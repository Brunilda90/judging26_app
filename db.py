import hashlib
import os
import secrets
from typing import Any, Dict, Optional
from datetime import datetime, timedelta

import streamlit as st
from bson import ObjectId
from pymongo import ASCENDING, MongoClient
from pymongo.errors import DuplicateKeyError
from bson.binary import Binary

def _get_mongo_uri() -> str:
    # Streamlit Cloud exposes secrets via st.
    print("calling _get_mongo_uri")
    try:
        secret_uri = st.secrets.database.uri
    except Exception:
        secret_uri = None
    if secret_uri:
        print("Using MongoDB URI from Streamlit secrets.")
        return secret_uri
    # No valid URI present
    return None


def _get_db_name() -> str:
    print("calling _get_db_name")
    try:
        secret_db = st.secrets.database.name  # type: ignore[attr-defined]
    except Exception:
        secret_db = None
    if secret_db:
        print("Using MongoDB DB name from Streamlit secrets.")
        return secret_db
    return None


@st.cache_resource
def get_db():
    # Cached Mongo client/db for Streamlit reruns
    uri = _get_mongo_uri()
    db_name = _get_db_name()
    if not uri or not db_name:
        raise RuntimeError("Database configuration missing. See .streamlit/secrets.toml")
    client = MongoClient(uri)
    return client[db_name]


# Module-level helper to let the app check configuration before calling DB functions
def is_db_configured() -> bool:
    try:
        return bool(_get_mongo_uri() and _get_db_name())
    except Exception:
        return False


def _oid(value: Any) -> ObjectId:
    if isinstance(value, ObjectId):
        return value
    return ObjectId(str(value))


def _doc_with_id(doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not doc:
        return None
    clean = dict(doc)
    clean["id"] = str(clean.pop("_id"))
    # Normalize nested ids if present
    for key in ("judge_id", "competitor_id", "question_id"):
        if key in clean and isinstance(clean[key], ObjectId):
            clean[key] = str(clean[key])
    return clean


def init_db():
    """
    Create indexes and seed default admin.
    """
    if not is_db_configured():
        st.error(
            "Database configuration missing. Create a .streamlit/secrets.toml with [database] uri and name. Login is disabled until configured."
        )
        return
    db = get_db()
    # Make email index sparse so judges without emails don't conflict
    try:
        db.judges.drop_index("email_1")
    except Exception:
        pass
    db.judges.create_index("email", unique=True, sparse=True)
    db.users.create_index("username", unique=True)
    db.users.create_index("judge_id", unique=True, sparse=True)
    db.scores.create_index(
        [("judge_id", ASCENDING), ("competitor_id", ASCENDING)], unique=True
    )
    db.answers.create_index(
        [("judge_id", ASCENDING), ("competitor_id", ASCENDING), ("question_id", ASCENDING)],
        unique=True,
    )
    db.team_registrations.create_index("team_name")
    db.team_registrations.create_index("contact_email")
    db.team_registrations.create_index("status")
    _init_booking_indexes(db)
    _init_booking_history_indexes(db)
    _init_scheduling_indexes(db)
    _init_finals_indexes(db)
    create_default_admin_if_missing(db)


# --- CRUD operations ---

def get_judges():
    db = get_db()
    rows = db.judges.find().sort("_id", ASCENDING)
    return [_doc_with_id(r) for r in rows]


def get_judges_with_user():
    db = get_db()
    results = []
    for judge in db.judges.find().sort("_id", ASCENDING):
        linked_user = db.users.find_one({"judge_id": judge["_id"], "role": "judge"})
        merged = _doc_with_id(judge)
        merged["username"] = linked_user["username"] if linked_user else None
        merged["judge_round"] = linked_user.get("judge_round", "prelims") if linked_user else "prelims"
        merged["prelim_room"] = judge.get("prelim_room")
        results.append(merged)
    return results


def insert_judge(name: str, email: str):
    db = get_db()
    db.judges.insert_one({"name": name, "email": email})


def create_judge_account(name: str, username: str, password: str, judge_round: str = "prelims", prelim_room: Optional[str] = None):
    """
    Create judge record and associated user account.
    judge_round: 'prelims' (default) or 'finals'
    """
    db = get_db()
    result = db.judges.insert_one({"name": name, "prelim_room": prelim_room})
    judge_id = result.inserted_id
    try:
        db.users.insert_one(
            {
                "username": username,
                "password_hash": hash_password(password),
                "role": "judge",
                "judge_id": judge_id,
                "judge_round": judge_round,
            }
        )
    except DuplicateKeyError:
        # Roll back the judge if username or email collides
        db.judges.delete_one({"_id": judge_id})
        raise
    return judge_id


def get_judge_by_id(judge_id: Any):
    db = get_db()
    row = db.judges.find_one({"_id": _oid(judge_id)})
    return _doc_with_id(row)


def update_judge_account(
    judge_id: Any,
    name: str,
    username: str,
    password: Optional[str] = None,
    judge_round: Optional[str] = None,
    update_room: bool = False,
    prelim_room: Optional[str] = None,
):
    db = get_db()
    judge_oid = _oid(judge_id)
    judge_patch: Dict[str, Any] = {"name": name}
    if update_room:
        judge_patch["prelim_room"] = prelim_room
    db.judges.update_one({"_id": judge_oid}, {"$set": judge_patch})
    update_fields: Dict[str, Any] = {"username": username}
    if password:
        update_fields["password_hash"] = hash_password(password)
    if judge_round is not None:
        update_fields["judge_round"] = judge_round
    db.users.update_one(
        {"judge_id": judge_oid, "role": "judge"},
        {"$set": update_fields},
        upsert=True,
    )


def delete_judge_account(judge_id: Any):
    db = get_db()
    judge_oid = _oid(judge_id)
    db.scores.delete_many({"judge_id": judge_oid})
    db.answers.delete_many({"judge_id": judge_oid})
    db.users.delete_many({"judge_id": judge_oid})
    db.judges.delete_one({"_id": judge_oid})


def get_competitors():
    db = get_db()
    rows = db.competitors.find().sort("_id", ASCENDING)
    return [_doc_with_id(r) for r in rows]


def insert_competitor(name: str, notes: str = ""):
    db = get_db()
    db.competitors.insert_one({"name": name, "notes": notes})


def update_competitor(competitor_id: Any, name: str, notes: Optional[str] = None):
    db = get_db()
    update_fields: Dict[str, Any] = {"name": name}
    if notes is not None:
        update_fields["notes"] = notes
    db.competitors.update_one({"_id": _oid(competitor_id)}, {"$set": update_fields})

def delete_competitor(competitor_id: Any):
    db = get_db()
    comp_oid = _oid(competitor_id)
    db.scores.delete_many({"competitor_id": comp_oid})
    db.answers.delete_many({"competitor_id": comp_oid})
    db.competitors.delete_one({"_id": comp_oid})


def replace_scores_for_judge(judge_id, scores_dict):
    # Replace all scores for a judge
    db = get_db()
    judge_oid = _oid(judge_id)
    db.scores.delete_many({"judge_id": judge_oid})
    for competitor_id, value in scores_dict.items():
        db.scores.insert_one(
            {"judge_id": judge_oid, "competitor_id": _oid(competitor_id), "value": value}
        )


def save_answers_for_judge(judge_id: Any, competitor_id: Any, answers_dict: Dict[Any, float], comments: str = ""):
    # Save per-question answers and aggregate into scores collection
    db = get_db()
    judge_oid = _oid(judge_id)
    comp_oid = _oid(competitor_id)

    db.answers.delete_many({"judge_id": judge_oid, "competitor_id": comp_oid})
    db.scores.delete_many({"judge_id": judge_oid, "competitor_id": comp_oid})

    if answers_dict:
        payload = []
        for question_id, value in answers_dict.items():
            payload.append(
                {
                    "judge_id": judge_oid,
                    "competitor_id": comp_oid,
                    "question_id": _oid(question_id),
                    "value": value,
                }
            )
        if payload:
            db.answers.insert_many(payload)

        avg_value = sum(answers_dict.values()) / len(answers_dict)
        db.scores.insert_one(
            {"judge_id": judge_oid, "competitor_id": comp_oid, "value": avg_value, "comments": comments}
        )
    else:
        # No answers, ensure scores entry is removed
        db.scores.delete_many({"judge_id": judge_oid, "competitor_id": comp_oid})
    get_leaderboard.clear()


def get_scores_for_judge(judge_id: Any):
    db = get_db()
    judge_oid = _oid(judge_id)
    rows = db.scores.find({"judge_id": judge_oid})
    return {str(row["competitor_id"]): row["value"] for row in rows}


@st.cache_data(ttl=30)
def get_leaderboard():
    db = get_db()
    pipeline = [
        {
            "$lookup": {
                "from": "scores",
                "localField": "_id",
                "foreignField": "competitor_id",
                "as": "score_docs",
            }
        },
        {
            "$addFields": {
                "num_scores": {"$size": "$score_docs"},
                "total_score": {"$sum": "$score_docs.value"},
                "avg_score": {
                    "$cond": [
                        {"$gt": [{"$size": "$score_docs"}, 0]},
                        {"$avg": "$score_docs.value"},
                        0,
                    ]
                },
            }
        },
        {
            "$project": {
                "name": 1,
                "num_scores": 1,
                "total_score": 1,
                "avg_score": 1,
            }
        },
        {"$sort": {"avg_score": -1}},
    ]
    rows = db.competitors.aggregate(pipeline)
    results = []
    for row in rows:
        base = _doc_with_id(row)
        base["competitor_id"] = base.pop("id")
        base["competitor_name"] = row["name"]
        results.append(base)
    return results


# --- Assets / customization helpers ---
def save_banner_image(file_bytes: bytes, filename: str, content_type: str):
    """Save or replace the banner image in the `assets` collection."""
    db = get_db()
    doc = {
        "key": "banner",
        "filename": filename,
        "content_type": content_type,
        "data": Binary(file_bytes),
        "updated_at": datetime.utcnow(),
    }
    db.assets.update_one({"key": "banner"}, {"$set": doc}, upsert=True)
    get_banner_image.clear()


@st.cache_data(ttl=300)
def get_banner_image():
    """Return banner image as dict or None: {filename, content_type, data(bytes)}"""
    db = get_db()
    row = db.assets.find_one({"key": "banner"})
    if not row:
        return None
    return {
        "filename": row.get("filename"),
        "content_type": row.get("content_type"),
        "data": bytes(row.get("data")) if row.get("data") is not None else None,
        "updated_at": row.get("updated_at"),
    }


def delete_banner_image():
    """Remove the banner image document from the assets collection."""
    db = get_db()
    db.assets.delete_many({"key": "banner"})
    get_banner_image.clear()

def set_background_color(color_hex: str):
    """Persist a background color setting (hex string)."""
    db = get_db()
    doc = {
        "key": "background_color",
        "color": color_hex,
        "updated_at": datetime.utcnow(),
    }
    db.assets.update_one({"key": "background_color"}, {"$set": doc}, upsert=True)
    get_background_color.clear()

@st.cache_data(ttl=300)
def get_background_color() -> Optional[str]:
    """Return stored background color hex string or None."""
    db = get_db()
    row = db.assets.find_one({"key": "background_color"})
    if not row:
        return None
    return row.get("color")

def clear_background_color():
    """Remove background color setting."""
    db = get_db()
    db.assets.delete_many({"key": "background_color"})
    get_background_color.clear()

def set_intro_message(text: str):
    """Persist intro message shown to judges on the scoring page."""
    db = get_db()
    doc = {
        "key": "intro_message",
        "text": text,
        "updated_at": datetime.utcnow(),
    }
    db.assets.update_one({"key": "intro_message"}, {"$set": doc}, upsert=True)
    get_intro_message.clear()

@st.cache_data(ttl=60)
def get_intro_message() -> Optional[str]:
    db = get_db()
    row = db.assets.find_one({"key": "intro_message"})
    if not row:
        return None
    return row.get("text")

def clear_intro_message():
    db = get_db()
    db.assets.delete_many({"key": "intro_message"})
    get_intro_message.clear()


# --- Questions/answers ---

def _recompute_scores_from_answers(db):
    """
    Rebuild scores collection by averaging existing answers per judge+competitor.
    """
    db.scores.delete_many({})
    pipeline = [
        {
            "$group": {
                "_id": {"judge_id": "$judge_id", "competitor_id": "$competitor_id"},
                "avg_value": {"$avg": "$value"},
            }
        }
    ]
    docs = []
    for row in db.answers.aggregate(pipeline):
        docs.append(
            {
                "judge_id": row["_id"]["judge_id"],
                "competitor_id": row["_id"]["competitor_id"],
                "value": row["avg_value"],
            }
        )
    if docs:
        db.scores.insert_many(docs)

@st.cache_data(ttl=600)
def get_questions():
    db = get_db()
    rows = db.questions.find().sort("_id", ASCENDING)
    return [_doc_with_id(r) for r in rows]

def insert_question(prompt):
    db = get_db()
    db.questions.insert_one({"prompt": prompt})
    get_questions.clear()

def update_question(question_id, prompt):
    db = get_db()
    db.questions.update_one({"_id": _oid(question_id)}, {"$set": {"prompt": prompt}})
    get_questions.clear()

def delete_question(question_id):
    db = get_db()
    question_oid = _oid(question_id)
    db.answers.delete_many({"question_id": question_oid})
    db.questions.delete_one({"_id": question_oid})
    _recompute_scores_from_answers(db)
    get_questions.clear()
    get_leaderboard.clear()

def get_answers_for_judge_competitor(judge_id, competitor_id):
    db = get_db()
    rows = db.answers.find(
        {"judge_id": _oid(judge_id), "competitor_id": _oid(competitor_id)}
    )
    return {str(row["question_id"]): row["value"] for row in rows}


# --- Team Registration ---

def register_team(team_name: str, project_name: str, description: str, members: list, contact_email: str) -> str:
    """Submit a new team registration (public, no auth required)."""
    db = get_db()
    doc = {
        "team_name": team_name.strip(),
        "project_name": project_name.strip(),
        "description": description.strip(),
        "members": members,  # list of {name, email}
        "contact_email": contact_email.strip().lower(),
        "status": "pending",
        "created_at": datetime.utcnow(),
        "admin_notes": "",
        "competitor_id": None,
    }
    result = db.team_registrations.insert_one(doc)
    get_team_registrations.clear()
    get_bookable_team_names.clear()
    return str(result.inserted_id)


@st.cache_data(ttl=30)
def get_team_registrations(status: Optional[str] = None):
    """Return all team registrations, optionally filtered by status."""
    db = get_db()
    query: Dict[str, Any] = {}
    if status:
        query["status"] = status
    rows = db.team_registrations.find(query).sort("created_at", ASCENDING)
    return [_doc_with_id(r) for r in rows]


def approve_registration_as_competitor(reg_id: Any) -> str:
    """Approve a registration and create a competitor entry. Returns competitor_id."""
    db = get_db()
    reg = db.team_registrations.find_one({"_id": _oid(reg_id)})
    if not reg:
        raise ValueError("Registration not found")
    notes_text = f"Project: {reg['project_name']}"
    if reg.get("description"):
        notes_text += f"\n{reg['description']}"
    result = db.competitors.insert_one({"name": reg["team_name"], "notes": notes_text})
    competitor_id = result.inserted_id
    db.team_registrations.update_one(
        {"_id": _oid(reg_id)},
        {"$set": {
            "status": "approved",
            "competitor_id": competitor_id,
            "reviewed_at": datetime.utcnow(),
        }},
    )
    get_team_registrations.clear()
    get_approved_team_names.clear()
    get_bookable_team_names.clear()
    get_leaderboard.clear()
    return str(competitor_id)


def reject_registration(reg_id: Any, admin_notes: str = ""):
    """Mark a registration as rejected with optional admin notes."""
    db = get_db()
    db.team_registrations.update_one(
        {"_id": _oid(reg_id)},
        {"$set": {"status": "rejected", "admin_notes": admin_notes, "reviewed_at": datetime.utcnow()}},
    )
    get_team_registrations.clear()
    get_bookable_team_names.clear()


def update_registration(reg_id: Any, team_name: str = None, contact_email: str = None,
                        admin_notes: str = None, status: str = None, members: list = None):
    """Update editable fields on a team registration."""
    db = get_db()
    patch: Dict[str, Any] = {}
    if team_name     is not None: patch["team_name"]    = team_name.strip()
    if contact_email is not None: patch["contact_email"] = contact_email.strip().lower()
    if admin_notes   is not None: patch["admin_notes"]  = admin_notes.strip()
    if status        is not None: patch["status"]       = status
    if members       is not None: patch["members"]      = members
    if patch:
        db.team_registrations.update_one({"_id": _oid(reg_id)}, {"$set": patch})
        get_team_registrations.clear()
        get_bookable_team_names.clear()
        get_approved_team_names.clear()


def team_name_exists(team_name: str) -> bool:
    """Check if a team name is already in a pending or approved registration."""
    db = get_db()
    return bool(db.team_registrations.find_one({
        "team_name": team_name.strip(),
        "status": {"$in": ["pending", "approved"]},
    }))


def contact_email_registered(email: str) -> bool:
    """Check if a contact email is already in a pending or approved registration."""
    db = get_db()
    return bool(db.team_registrations.find_one({
        "contact_email": email.strip().lower(),
        "status": {"$in": ["pending", "approved"]},
    }))


def get_team_by_member_email(email: str):
    """Return the registration doc where any member's email matches (pending/approved), or None.
    Comparison is case-insensitive."""
    import re
    db = get_db()
    pattern = re.compile(r"^" + re.escape(email.strip()) + r"$", re.IGNORECASE)
    row = db.team_registrations.find_one({
        "members.email": pattern,
        "status": {"$in": ["pending", "approved"]},
    })
    return _doc_with_id(row) if row else None


# ── Prelim Booking constants ────────────────────────────────────────────────────

PRELIM_ROOMS: list = ["N200", "N217", "N300A"]

PRELIM_SLOTS: list = [
    "2:00 PM – 2:10 PM",
    "2:10 PM – 2:20 PM",
    "2:20 PM – 2:30 PM",
    "2:30 PM – 2:40 PM",
    "2:40 PM – 2:50 PM",
    "2:50 PM – 3:00 PM",
    "3:00 PM – 3:10 PM",
    "3:10 PM – 3:20 PM",
    "3:20 PM – 3:30 PM",
]


# ── Prelim Booking DB helpers ───────────────────────────────────────────────────

def _init_booking_indexes(db):
    """Create unique indexes for the prelim_bookings collection."""
    # Each (slot, room) pair can only be assigned once
    db.prelim_bookings.create_index(
        [("slot_label", ASCENDING), ("room", ASCENDING)], unique=True
    )
    # Each approved team can only have one booking at a time
    db.prelim_bookings.create_index("team_name", unique=True)


def _init_booking_history_indexes(db):
    """Create indexes for the prelim_booking_history audit collection."""
    db.prelim_booking_history.create_index([("timestamp", ASCENDING)])
    db.prelim_booking_history.create_index([("team_name", ASCENDING)])


def log_booking_event(
    team_name: str,
    slot_label: str,
    room: str,
    action: str,
    previous_slot: Optional[str] = None,
    previous_room: Optional[str] = None,
):
    """Append an entry to the prelim booking audit log.

    action values: 'booked', 'switched', 'admin_updated', 'admin_deleted'
    """
    db = get_db()
    doc: Dict[str, Any] = {
        "team_name": team_name,
        "slot_label": slot_label,
        "room": room,
        "action": action,
        "timestamp": datetime.utcnow(),
    }
    if previous_slot is not None:
        doc["previous_slot"] = previous_slot
    if previous_room is not None:
        doc["previous_room"] = previous_room
    db.prelim_booking_history.insert_one(doc)


@st.cache_data(ttl=30)
def get_booking_history() -> list:
    """Return all prelim booking audit-log entries, newest first."""
    db = get_db()
    rows = db.prelim_booking_history.find().sort("timestamp", -1)
    return [_doc_with_id(r) for r in rows]


@st.cache_data(ttl=30)
def get_approved_team_names() -> list:
    """Return sorted list of team names from approved registrations."""
    db = get_db()
    rows = db.team_registrations.find({"status": "approved"}).sort("team_name", ASCENDING)
    return [r["team_name"] for r in rows]


@st.cache_data(ttl=30)
def get_bookable_team_names() -> list:
    """Return sorted list of team names eligible to book (pending or approved, not rejected)."""
    db = get_db()
    rows = db.team_registrations.find(
        {"status": {"$in": ["pending", "approved"]}}
    ).sort("team_name", ASCENDING)
    return [r["team_name"] for r in rows]


@st.cache_data(ttl=15)
def get_all_bookings() -> list:
    """Return all prelim bookings sorted by slot then room."""
    db = get_db()
    rows = db.prelim_bookings.find().sort(
        [("slot_label", ASCENDING), ("room", ASCENDING)]
    )
    return [_doc_with_id(r) for r in rows]


def get_booking_by_team_name(team_name: str) -> Optional[Dict[str, Any]]:
    """Return the booking for a given team name, or None."""
    db = get_db()
    row = db.prelim_bookings.find_one({"team_name": team_name})
    return _doc_with_id(row) if row else None


@st.cache_data(ttl=15)
def get_booked_slot_map() -> Dict[str, str]:
    """Return dict keyed by 'slot_label||room' → team_name for all booked slots."""
    db = get_db()
    result: Dict[str, str] = {}
    for row in db.prelim_bookings.find():
        key = f"{row['slot_label']}||{row['room']}"
        result[key] = row["team_name"]
    return result


def create_booking(team_name: str, slot_label: str, room: str) -> str:
    """Create a new booking. Raises ValueError on conflict."""
    db = get_db()
    # Check if team already has a booking
    existing = db.prelim_bookings.find_one({"team_name": team_name})
    if existing:
        raise ValueError(f"Team '{team_name}' already has a booking. Use switch_booking to change it.")
    doc = {
        "team_name": team_name,
        "slot_label": slot_label,
        "room": room,
        "booked_at": datetime.utcnow(),
    }
    try:
        result = db.prelim_bookings.insert_one(doc)
        log_booking_event(team_name, slot_label, room, "booked")
        get_booked_slot_map.clear()
        get_all_bookings.clear()
        get_prelim_slot_map.clear()
        get_teams_booked_in_room.clear()
        get_bookable_team_names.clear()
        return str(result.inserted_id)
    except DuplicateKeyError:
        raise ValueError(f"Slot '{slot_label}' in room {room} is already taken.")


def switch_booking(team_name: str, new_slot_label: str, new_room: str) -> str:
    """Delete existing booking for team and create a new one atomically."""
    db = get_db()
    # Capture old booking details for the audit log before deleting
    old = db.prelim_bookings.find_one({"team_name": team_name})
    old_slot = old["slot_label"] if old else None
    old_room = old["room"] if old else None
    # Remove old booking first
    db.prelim_bookings.delete_many({"team_name": team_name})
    doc = {
        "team_name": team_name,
        "slot_label": new_slot_label,
        "room": new_room,
        "booked_at": datetime.utcnow(),
    }
    try:
        result = db.prelim_bookings.insert_one(doc)
        log_booking_event(team_name, new_slot_label, new_room, "switched", old_slot, old_room)
        get_booked_slot_map.clear()
        get_all_bookings.clear()
        get_prelim_slot_map.clear()
        get_teams_booked_in_room.clear()
        return str(result.inserted_id)
    except DuplicateKeyError:
        raise ValueError(f"Slot '{new_slot_label}' in room {new_room} is already taken.")


def admin_update_booking(booking_id: Any, slot_label: str, room: str):
    """Admin: update any booking's slot/room. Raises ValueError on slot conflict."""
    db = get_db()
    # Capture current booking details for the audit log
    current = db.prelim_bookings.find_one({"_id": _oid(booking_id)})
    # Check the target slot isn't taken by a different booking
    conflict = db.prelim_bookings.find_one({
        "slot_label": slot_label,
        "room": room,
        "_id": {"$ne": _oid(booking_id)},
    })
    if conflict:
        raise ValueError(f"Slot '{slot_label}' in room {room} is already booked by '{conflict['team_name']}'.")
    db.prelim_bookings.update_one(
        {"_id": _oid(booking_id)},
        {"$set": {"slot_label": slot_label, "room": room}},
    )
    if current:
        log_booking_event(
            current["team_name"], slot_label, room, "admin_updated",
            current.get("slot_label"), current.get("room"),
        )
    get_booked_slot_map.clear()
    get_all_bookings.clear()
    get_prelim_slot_map.clear()
    get_teams_booked_in_room.clear()
    get_booking_history.clear()


def admin_delete_booking(booking_id: Any):
    """Admin: remove a booking entirely."""
    db = get_db()
    current = db.prelim_bookings.find_one({"_id": _oid(booking_id)})
    db.prelim_bookings.delete_one({"_id": _oid(booking_id)})
    if current:
        log_booking_event(
            current["team_name"], current.get("slot_label", ""), current.get("room", ""),
            "admin_deleted",
        )
    get_booked_slot_map.clear()
    get_all_bookings.clear()
    get_prelim_slot_map.clear()
    get_teams_booked_in_room.clear()
    get_booking_history.clear()


# ── Mentor & Robot Scheduling constants ─────────────────────────────────────────

MENTOR_NAMES: list = [
    "Mentor 1",
    "Mentor 2",
    "Mentor 3",
    "Mentor 4",
    "Mentor 5",
    "Mentor 6",
    "Mentor 7",
]

# Maps each mentor to the room they are stationed in.
# UPDATE with real mentor names and room assignments before the event.
MENTOR_ROOM_MAP: dict = {
    "Mentor 1": "N200",
    "Mentor 2": "N200",
    "Mentor 3": "N217",
    "Mentor 4": "N217",
    "Mentor 5": "N300A",
    "Mentor 6": "N300A",
    "Mentor 7": "N300A",
}

# One robot per room — the room name IS the robot identifier
SCHED_ROBOT_ROOMS: list = ["N200", "N217", "N300A"]

SCHED_FRIDAY_SLOTS: list = [
    "Fri Mar 6 \u00b7 6:20 \u2013 6:40 PM",
    "Fri Mar 6 \u00b7 6:40 \u2013 7:00 PM",
    "Fri Mar 6 \u00b7 7:00 \u2013 7:20 PM",
    "Fri Mar 6 \u00b7 7:20 \u2013 7:40 PM",
    "Fri Mar 6 \u00b7 7:40 \u2013 8:00 PM",
]

SCHED_SATURDAY_SLOTS: list = [
    "Sat Mar 7 \u00b7 10:00 \u2013 10:20 AM",
    "Sat Mar 7 \u00b7 10:20 \u2013 10:40 AM",
    "Sat Mar 7 \u00b7 10:40 \u2013 11:00 AM",
    "Sat Mar 7 \u00b7 11:00 \u2013 11:20 AM",
    "Sat Mar 7 \u00b7 11:20 \u2013 11:40 AM",
    "Sat Mar 7 \u00b7 11:40 AM \u2013 12:00 PM",
    "Sat Mar 7 \u00b7 12:00 \u2013 12:20 PM",
    "Sat Mar 7 \u00b7 12:20 \u2013 12:40 PM",
    "Sat Mar 7 \u00b7 12:40 \u2013  1:00 PM",
    "Sat Mar 7 \u00b7  1:00 \u2013  1:20 PM",
]

SCHED_ALL_SLOTS: list = SCHED_FRIDAY_SLOTS + SCHED_SATURDAY_SLOTS

MAX_MENTOR_BOOKINGS: int = 2
MAX_ROBOT_BOOKINGS: int = 2


# ── Scheduling DB helpers ────────────────────────────────────────────────────────

def _init_scheduling_indexes(db):
    """Create unique indexes for mentor_bookings and robot_bookings collections."""
    # One team per mentor per slot
    db.mentor_bookings.create_index(
        [("mentor_name", ASCENDING), ("slot_label", ASCENDING)], unique=True
    )
    # A team can only have one mentor booking per slot (no double-booking same time)
    db.mentor_bookings.create_index(
        [("team_name", ASCENDING), ("slot_label", ASCENDING)], unique=True
    )
    # One team per robot room per slot
    db.robot_bookings.create_index(
        [("room", ASCENDING), ("slot_label", ASCENDING)], unique=True
    )
    # A team can only have one robot booking per slot
    db.robot_bookings.create_index(
        [("team_name", ASCENDING), ("slot_label", ASCENDING)], unique=True
    )


def get_mentor_bookings_for_team(team_name: str) -> list:
    """Return all mentor bookings for a team."""
    db = get_db()
    rows = db.mentor_bookings.find({"team_name": team_name}).sort(
        "slot_label", ASCENDING
    )
    return [_doc_with_id(r) for r in rows]


def get_robot_bookings_for_team(team_name: str) -> list:
    """Return all robot bookings for a team."""
    db = get_db()
    rows = db.robot_bookings.find({"team_name": team_name}).sort(
        "slot_label", ASCENDING
    )
    return [_doc_with_id(r) for r in rows]


@st.cache_data(ttl=15)
def get_all_mentor_bookings() -> list:
    """Return all mentor bookings sorted by slot then mentor."""
    db = get_db()
    rows = db.mentor_bookings.find().sort(
        [("slot_label", ASCENDING), ("mentor_name", ASCENDING)]
    )
    return [_doc_with_id(r) for r in rows]


@st.cache_data(ttl=15)
def get_all_robot_bookings() -> list:
    """Return all robot bookings sorted by slot then room."""
    db = get_db()
    rows = db.robot_bookings.find().sort(
        [("slot_label", ASCENDING), ("room", ASCENDING)]
    )
    return [_doc_with_id(r) for r in rows]


@st.cache_data(ttl=15)
def get_mentor_booked_map() -> Dict[str, str]:
    """Return dict keyed by 'slot_label||mentor_name' → team_name."""
    db = get_db()
    result: Dict[str, str] = {}
    for row in db.mentor_bookings.find():
        key = f"{row['slot_label']}||{row['mentor_name']}"
        result[key] = row["team_name"]
    return result


@st.cache_data(ttl=15)
def get_robot_booked_map() -> Dict[str, str]:
    """Return dict keyed by 'slot_label||room' → team_name."""
    db = get_db()
    result: Dict[str, str] = {}
    for row in db.robot_bookings.find():
        key = f"{row['slot_label']}||{row['room']}"
        result[key] = row["team_name"]
    return result


def create_mentor_booking(team_name: str, mentor_name: str, slot_label: str) -> str:
    """Create a mentor booking. Raises ValueError on limit or slot conflict."""
    db = get_db()
    current = db.mentor_bookings.count_documents({"team_name": team_name})
    if current >= MAX_MENTOR_BOOKINGS:
        raise ValueError(
            f"Your team has already booked {MAX_MENTOR_BOOKINGS} mentor sessions (the maximum)."
        )
    doc = {
        "team_name": team_name,
        "mentor_name": mentor_name,
        "slot_label": slot_label,
        "booked_at": datetime.utcnow(),
    }
    try:
        result = db.mentor_bookings.insert_one(doc)
        get_mentor_booked_map.clear()
        get_all_mentor_bookings.clear()
        return str(result.inserted_id)
    except DuplicateKeyError:
        raise ValueError(
            f"That slot is no longer available for {mentor_name}. Please choose another."
        )


def create_mentor_booking_room(team_name: str, room: str, slot_label: str) -> str:
    """Book a mentor session in a specific room at a specific slot.
    Auto-assigns to any available mentor stationed in that room.
    Raises ValueError if at limit, already booked at this slot, or no mentors free in that room."""
    db = get_db()
    current = db.mentor_bookings.count_documents({"team_name": team_name})
    if current >= MAX_MENTOR_BOOKINGS:
        raise ValueError(
            f"Your team has already booked {MAX_MENTOR_BOOKINGS} mentor sessions (the maximum)."
        )
    slot_conflict = db.mentor_bookings.find_one(
        {"team_name": team_name, "slot_label": slot_label}
    )
    if slot_conflict:
        raise ValueError("Your team already has a mentor session booked at this time slot.")
    mentors_in_room = [m for m, r in MENTOR_ROOM_MAP.items() if r == room]
    if not mentors_in_room:
        raise ValueError(f"No mentors are assigned to Room {room}.")
    booked_here = {
        r["mentor_name"]
        for r in db.mentor_bookings.find(
            {"slot_label": slot_label, "mentor_name": {"$in": mentors_in_room}}
        )
    }
    available_mentor = next((m for m in mentors_in_room if m not in booked_here), None)
    if not available_mentor:
        raise ValueError(
            f"Room {room} is fully booked at that time. Please choose a different slot or room."
        )
    doc = {
        "team_name": team_name,
        "mentor_name": available_mentor,
        "slot_label": slot_label,
        "booked_at": datetime.utcnow(),
    }
    try:
        result = db.mentor_bookings.insert_one(doc)
        get_mentor_booked_map.clear()
        get_all_mentor_bookings.clear()
        return str(result.inserted_id)
    except DuplicateKeyError:
        raise ValueError("That slot was just taken. Please refresh and try a different time.")


def create_robot_booking(team_name: str, room: str, slot_label: str) -> str:
    """Create a robot booking. Raises ValueError on limit or slot conflict."""
    db = get_db()
    current = db.robot_bookings.count_documents({"team_name": team_name})
    if current >= MAX_ROBOT_BOOKINGS:
        raise ValueError(
            f"Your team has already booked {MAX_ROBOT_BOOKINGS} robot sessions (the maximum)."
        )
    doc = {
        "team_name": team_name,
        "room": room,
        "slot_label": slot_label,
        "booked_at": datetime.utcnow(),
    }
    try:
        result = db.robot_bookings.insert_one(doc)
        get_robot_booked_map.clear()
        get_all_robot_bookings.clear()
        return str(result.inserted_id)
    except DuplicateKeyError:
        raise ValueError(
            f"That slot is no longer available for Robot in {room}. Please choose another."
        )


def cancel_mentor_booking(booking_id: Any):
    """Cancel (delete) a mentor booking by ID."""
    db = get_db()
    db.mentor_bookings.delete_one({"_id": _oid(booking_id)})
    get_mentor_booked_map.clear()
    get_all_mentor_bookings.clear()


def cancel_robot_booking(booking_id: Any):
    """Cancel (delete) a robot booking by ID."""
    db = get_db()
    db.robot_bookings.delete_one({"_id": _oid(booking_id)})
    get_robot_booked_map.clear()
    get_all_robot_bookings.clear()


def admin_update_mentor_booking(booking_id: Any, mentor_name: str, slot_label: str):
    """Admin: update a mentor booking's mentor and slot. Raises ValueError on conflict."""
    db = get_db()
    conflict = db.mentor_bookings.find_one({
        "mentor_name": mentor_name,
        "slot_label": slot_label,
        "_id": {"$ne": _oid(booking_id)},
    })
    if conflict:
        raise ValueError(
            f"Slot '{slot_label}' is already booked with {mentor_name} by '{conflict['team_name']}'."
        )
    db.mentor_bookings.update_one(
        {"_id": _oid(booking_id)},
        {"$set": {"mentor_name": mentor_name, "slot_label": slot_label}},
    )
    get_mentor_booked_map.clear()
    get_all_mentor_bookings.clear()


def admin_update_robot_booking(booking_id: Any, room: str, slot_label: str):
    """Admin: update a robot booking's room and slot. Raises ValueError on conflict."""
    db = get_db()
    conflict = db.robot_bookings.find_one({
        "room": room,
        "slot_label": slot_label,
        "_id": {"$ne": _oid(booking_id)},
    })
    if conflict:
        raise ValueError(
            f"Slot '{slot_label}' for Robot in {room} is already booked by '{conflict['team_name']}'."
        )
    db.robot_bookings.update_one(
        {"_id": _oid(booking_id)},
        {"$set": {"room": room, "slot_label": slot_label}},
    )
    get_robot_booked_map.clear()
    get_all_robot_bookings.clear()


def admin_delete_mentor_booking(booking_id: Any):
    """Admin: remove a mentor booking entirely."""
    db = get_db()
    db.mentor_bookings.delete_one({"_id": _oid(booking_id)})
    get_mentor_booked_map.clear()
    get_all_mentor_bookings.clear()


def admin_delete_robot_booking(booking_id: Any):
    """Admin: remove a robot booking entirely."""
    db = get_db()
    db.robot_bookings.delete_one({"_id": _oid(booking_id)})
    get_robot_booked_map.clear()
    get_all_robot_bookings.clear()


# --- Competitor auto-create ---

def get_or_create_competitor_for_team(team_name: str) -> dict:
    """Return the competitor entry for a team (by name match), creating one if absent.
    This lets judges score any team that booked a prelim slot, even if admin has
    not yet manually approved the registration as a competitor."""
    db = get_db()
    existing = db.competitors.find_one({"name": team_name})
    if existing:
        return _doc_with_id(existing)
    # Auto-create from registration data (or minimal fallback)
    reg = db.team_registrations.find_one(
        {"team_name": team_name, "status": {"$in": ["pending", "approved"]}}
    )
    notes = ""
    if reg:
        notes = f"Project: {reg.get('project_name', '')}"
        if reg.get("description"):
            notes += f"\n{reg['description']}"
    result = db.competitors.insert_one({"name": team_name, "notes": notes})
    return {"id": str(result.inserted_id), "name": team_name, "notes": notes}


# --- Scoring overview helpers ---

def get_prelim_scoring_matrix():
    """Return (questions, competitors_with_scores, matrix, judge_counts) for prelims.
    matrix[comp_id][question_id] = avg_value (0–100 scale, divide by 10 to display).
    judge_counts[comp_id] = number of judges who scored that competitor."""
    db = get_db()
    questions = [_doc_with_id(q) for q in db.questions.find().sort("_id", ASCENDING)]
    competitors = [_doc_with_id(c) for c in db.competitors.find().sort("name", ASCENDING)]

    agg = list(db.answers.aggregate([
        {"$group": {
            "_id": {"competitor_id": "$competitor_id", "question_id": "$question_id"},
            "avg_value": {"$avg": "$value"},
            "judge_count": {"$sum": 1},
        }}
    ]))

    judge_count_agg = list(db.scores.aggregate([
        {"$group": {"_id": "$competitor_id", "count": {"$sum": 1}}}
    ]))
    judge_counts = {str(row["_id"]): row["count"] for row in judge_count_agg}

    matrix: Dict[str, Dict[str, float]] = {}
    for row in agg:
        cid = str(row["_id"]["competitor_id"])
        qid = str(row["_id"]["question_id"])
        matrix.setdefault(cid, {})[qid] = row["avg_value"]

    scored = [c for c in competitors if c["id"] in matrix]
    return questions, scored, matrix, judge_counts


def get_finals_scoring_matrix():
    """Same as get_prelim_scoring_matrix but for the finals_answers / finals_scores collections."""
    db = get_db()
    questions = [_doc_with_id(q) for q in db.questions.find().sort("_id", ASCENDING)]
    competitors = [_doc_with_id(c) for c in db.competitors.find().sort("name", ASCENDING)]

    agg = list(db.finals_answers.aggregate([
        {"$group": {
            "_id": {"competitor_id": "$competitor_id", "question_id": "$question_id"},
            "avg_value": {"$avg": "$value"},
        }}
    ]))

    judge_count_agg = list(db.finals_scores.aggregate([
        {"$group": {"_id": "$competitor_id", "count": {"$sum": 1}}}
    ]))
    judge_counts = {str(row["_id"]): row["count"] for row in judge_count_agg}

    matrix: Dict[str, Dict[str, float]] = {}
    for row in agg:
        cid = str(row["_id"]["competitor_id"])
        qid = str(row["_id"]["question_id"])
        matrix.setdefault(cid, {})[qid] = row["avg_value"]

    scored = [c for c in competitors if c["id"] in matrix]
    return questions, scored, matrix, judge_counts


# --- Judge Round / Room helpers ---

@st.cache_data(ttl=30)
def get_teams_booked_in_room(room: str) -> list:
    """Return list of {team_name, slot_label, members, project_name} for every team
    that has a prelim booking in the given room."""
    db = get_db()
    bookings = list(db.prelim_bookings.find({"room": room}).sort("slot_label", ASCENDING))
    result = []
    for b in bookings:
        tn = b["team_name"]
        reg = db.team_registrations.find_one(
            {"team_name": tn, "status": {"$in": ["pending", "approved"]}}
        )
        result.append({
            "team_name": tn,
            "slot_label": b.get("slot_label", ""),
            "members": reg.get("members", []) if reg else [],
            "project_name": reg.get("project_name", "") if reg else "",
        })
    return result


@st.cache_data(ttl=15)
def get_prelim_slot_map() -> Dict[str, str]:
    """Return {team_name: slot_label} for all prelim bookings."""
    db = get_db()
    result: Dict[str, str] = {}
    for row in db.prelim_bookings.find():
        result[row["team_name"]] = row.get("slot_label", "")
    return result


def get_prelim_top5() -> list:
    """Return up to 5 competitors with the highest average prelim score
    (only competitors that have received at least one score)."""
    leaderboard = get_leaderboard()
    scored = [c for c in leaderboard if c.get("num_scores", 0) > 0]
    return scored[:5]


def get_prelim_top6() -> list:
    """Return up to 6 competitors with the highest average prelim score
    (only competitors that have received at least one score)."""
    leaderboard = get_leaderboard()
    scored = [c for c in leaderboard if c.get("num_scores", 0) > 0]
    return scored[:6]


def get_prelim_comments_for_judge_competitor(judge_id: Any, competitor_id: Any) -> str:
    """Return the comments stored by a specific judge for a specific competitor (prelims)."""
    db = get_db()
    row = db.scores.find_one({"judge_id": _oid(judge_id), "competitor_id": _oid(competitor_id)})
    return row.get("comments", "") if row else ""


def get_all_prelim_comments_for_competitor(competitor_id: Any) -> list:
    """Return list of {judge_name, comments} for all prelim judges who left notes for this competitor."""
    db = get_db()
    rows = list(db.scores.find({
        "competitor_id": _oid(competitor_id),
        "comments": {"$exists": True, "$nin": ["", None]},
    }))
    result = []
    for row in rows:
        judge = db.judges.find_one({"_id": row["judge_id"]})
        result.append({
            "judge_name": judge.get("name", "Judge") if judge else "Judge",
            "comments": row.get("comments", ""),
        })
    return result


def get_finals_comments_for_judge_competitor(judge_id: Any, competitor_id: Any) -> str:
    """Return the comments stored by a specific judge for a specific competitor (finals)."""
    db = get_db()
    row = db.finals_scores.find_one({"judge_id": _oid(judge_id), "competitor_id": _oid(competitor_id)})
    return row.get("comments", "") if row else ""


def get_all_finals_comments_for_competitor(competitor_id: Any) -> list:
    """Return list of {judge_name, comments} for all finals judges who left notes for this competitor."""
    db = get_db()
    rows = list(db.finals_scores.find({
        "competitor_id": _oid(competitor_id),
        "comments": {"$exists": True, "$nin": ["", None]},
    }))
    result = []
    for row in rows:
        judge = db.judges.find_one({"_id": row["judge_id"]})
        result.append({
            "judge_name": judge.get("name", "Judge") if judge else "Judge",
            "comments": row.get("comments", ""),
        })
    return result


def get_scores_for_judge_all(judge_id: Any) -> Dict[str, float]:
    """Return {competitor_id_str: avg_score} for all prelim scores by a judge."""
    db = get_db()
    judge_oid = _oid(judge_id)
    rows = db.scores.find({"judge_id": judge_oid})
    return {str(row["competitor_id"]): row["value"] for row in rows}


# --- Finals Scoring ---

def _init_finals_indexes(db):
    """Create unique indexes for finals_scores and finals_answers collections."""
    db.finals_scores.create_index(
        [("judge_id", ASCENDING), ("competitor_id", ASCENDING)], unique=True
    )
    db.finals_answers.create_index(
        [
            ("judge_id", ASCENDING),
            ("competitor_id", ASCENDING),
            ("question_id", ASCENDING),
        ],
        unique=True,
    )


def get_answers_for_judge_competitor_finals(judge_id: Any, competitor_id: Any) -> dict:
    """Return {question_id_str: value} for a finals judge+competitor pair."""
    db = get_db()
    rows = db.finals_answers.find(
        {"judge_id": _oid(judge_id), "competitor_id": _oid(competitor_id)}
    )
    return {str(row["question_id"]): row["value"] for row in rows}


def save_answers_for_judge_finals(
    judge_id: Any, competitor_id: Any, answers_dict: Dict[Any, float], comments: str = ""
):
    """Save per-question answers and the aggregated score into the finals collections."""
    db = get_db()
    judge_oid = _oid(judge_id)
    comp_oid = _oid(competitor_id)
    db.finals_answers.delete_many({"judge_id": judge_oid, "competitor_id": comp_oid})
    db.finals_scores.delete_many({"judge_id": judge_oid, "competitor_id": comp_oid})
    if answers_dict:
        payload = [
            {
                "judge_id": judge_oid,
                "competitor_id": comp_oid,
                "question_id": _oid(qid),
                "value": val,
            }
            for qid, val in answers_dict.items()
        ]
        if payload:
            db.finals_answers.insert_many(payload)
        avg_value = sum(answers_dict.values()) / len(answers_dict)
        db.finals_scores.insert_one(
            {"judge_id": judge_oid, "competitor_id": comp_oid, "value": avg_value, "comments": comments}
        )
    get_leaderboard.clear()


def get_finals_scores_for_judge(judge_id: Any) -> Dict[str, float]:
    """Return {competitor_id_str: avg_score} for all finals scores by a judge."""
    db = get_db()
    judge_oid = _oid(judge_id)
    rows = db.finals_scores.find({"judge_id": judge_oid})
    return {str(row["competitor_id"]): row["value"] for row in rows}


def get_finals_leaderboard() -> list:
    """Return all competitors sorted by average finals score descending."""
    db = get_db()
    pipeline = [
        {
            "$lookup": {
                "from": "finals_scores",
                "localField": "_id",
                "foreignField": "competitor_id",
                "as": "score_docs",
            }
        },
        {
            "$addFields": {
                "num_scores": {"$size": "$score_docs"},
                "total_score": {"$sum": "$score_docs.value"},
                "avg_score": {
                    "$cond": [
                        {"$gt": [{"$size": "$score_docs"}, 0]},
                        {"$avg": "$score_docs.value"},
                        0,
                    ]
                },
            }
        },
        {
            "$project": {
                "name": 1,
                "num_scores": 1,
                "total_score": 1,
                "avg_score": 1,
            }
        },
        {"$sort": {"avg_score": -1}},
    ]
    results = []
    for row in db.competitors.aggregate(pipeline):
        base = _doc_with_id(row)
        base["competitor_id"] = base.pop("id")
        base["competitor_name"] = row["name"]
        results.append(base)
    return results


# --- Auth helpers ---

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def create_default_admin_if_missing(db):
    existing = db.users.count_documents({"role": "admin"})
    if existing == 0:
        db.users.insert_one(
            {"username": "admin", "password_hash": hash_password("admin"), "role": "admin"}
        )

def authenticate_user(username, password):
    db = get_db()
    row = db.users.find_one({"username": username})
    if row and row["password_hash"] == hash_password(password):
        result = _doc_with_id(row)
        return result
    return None


# --- Server-side session store ---

def create_session(user: dict, ttl_hours: int = 12) -> str:
    """Create a server-side session for the given user. Returns a URL-safe token."""
    db = get_db()
    token = secrets.token_urlsafe(32)
    db.sessions.insert_one({
        "token": token,
        "user":  user,
        "expires_at": datetime.utcnow() + timedelta(hours=ttl_hours),
    })
    # Ensure MongoDB auto-expires old sessions via TTL index
    try:
        db.sessions.create_index("expires_at", expireAfterSeconds=0)
    except Exception:
        pass
    return token


def get_session(token: str) -> Optional[dict]:
    """Return the stored user dict for a valid, unexpired token, or None."""
    if not token:
        return None
    db = get_db()
    row = db.sessions.find_one({
        "token": token,
        "expires_at": {"$gt": datetime.utcnow()},
    })
    return row.get("user") if row else None


def delete_session(token: str) -> None:
    """Delete a session by token (logout)."""
    if not token:
        return
    db = get_db()
    db.sessions.delete_one({"token": token})
