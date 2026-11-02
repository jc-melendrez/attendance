"""All Firestore reads and writes live here.

Data layout:

  users/{username}
      name, role ("teacher" | "student"), password_hash,
      joins: {classId: studentId}          (students only)
  classes/{classId}
      name, owner (teacher's username), join_code, student_count,
      last_session ("YYYY-MM-DD"), created_at
      students/{studentId}
          name, user_id (set when the student joined with an account), created_at
      sessions/{YYYY-MM-DD}
          date, marks: {studentId: "present" | "late" | "absent"}, updated_at

A session's document id is its date, so there is one roll call per class per day
and saving the same day again simply updates it. The username is the user
document id, which keeps usernames unique without needing an index.
"""
import secrets

from firebase_admin import firestore
from google.api_core.exceptions import AlreadyExists
from google.cloud.firestore_v1.base_query import FieldFilter

from .firebase import db

STATUSES = ("present", "late", "absent")
CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O or 1/I


class UsernameTaken(Exception):
    pass


def _classes():
    return db().collection("classes")


def _users():
    return db().collection("users")


def _with_id(doc):
    data = doc.to_dict() or {}
    data["id"] = doc.id
    return data


# ---- users -----------------------------------------------------------------

def get_user(username):
    doc = _users().document(username).get()
    if not doc.exists:
        return None
    data = doc.to_dict() or {}
    data["username"] = doc.id
    return data


def create_user(username, name, role, password_hash):
    try:
        _users().document(username).create(
            {
                "name": name,
                "role": role,
                "password_hash": password_hash,
                "joins": {},
                "created_at": firestore.SERVER_TIMESTAMP,
            }
        )
    except AlreadyExists:
        raise UsernameTaken(username)


def get_joins(username):
    user = _users().document(username).get().to_dict() or {}
    return user.get("joins", {})


# ---- classes ---------------------------------------------------------------

def list_classes(owner):
    docs = _classes().where(filter=FieldFilter("owner", "==", owner)).stream()
    return sorted((_with_id(d) for d in docs), key=lambda c: c.get("name", "").lower())


def get_class(class_id):
    doc = _classes().document(class_id).get()
    return _with_id(doc) if doc.exists else None


def find_class_by_code(code):
    query = _classes().where(filter=FieldFilter("join_code", "==", code)).limit(1)
    for doc in query.stream():
        return _with_id(doc)
    return None


def _new_code():
    for _ in range(10):
        code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(6))
        if find_class_by_code(code) is None:
            return code
    raise RuntimeError("Could not make a unique class code")


def create_class(name, owner):
    ref = _classes().document()
    ref.set(
        {
            "name": name,
            "owner": owner,
            "join_code": _new_code(),
            "student_count": 0,
            "last_session": "",
            "created_at": firestore.SERVER_TIMESTAMP,
        }
    )
    return ref.id


# ---- students --------------------------------------------------------------

def list_students(class_id):
    query = _classes().document(class_id).collection("students").order_by("name")
    return [_with_id(d) for d in query.stream()]


def add_students(class_id, names):
    class_ref = _classes().document(class_id)
    batch = db().batch()
    for name in names:
        ref = class_ref.collection("students").document()
        batch.set(ref, {"name": name, "created_at": firestore.SERVER_TIMESTAMP})
    batch.update(class_ref, {"student_count": firestore.Increment(len(names))})
    batch.commit()


def join_class(username, name, class_id):
    """Link a student account to a class. Returns the student document id."""
    user_ref = _users().document(username)
    joins = (user_ref.get().to_dict() or {}).get("joins", {})
    if class_id in joins:
        return joins[class_id]  # already joined

    class_ref = _classes().document(class_id)
    student_ref = class_ref.collection("students").document()
    batch = db().batch()
    batch.set(
        student_ref,
        {"name": name, "user_id": username, "created_at": firestore.SERVER_TIMESTAMP},
    )
    batch.update(class_ref, {"student_count": firestore.Increment(1)})
    batch.update(user_ref, {f"joins.{class_id}": student_ref.id})
    batch.commit()
    return student_ref.id


def delete_student(class_id, student_id):
    class_ref = _classes().document(class_id)
    student_ref = class_ref.collection("students").document(student_id)
    linked_user = (student_ref.get().to_dict() or {}).get("user_id")

    batch = db().batch()
    batch.delete(student_ref)
    batch.update(class_ref, {"student_count": firestore.Increment(-1)})
    if linked_user:  # unlink the student's account too
        batch.update(
            _users().document(linked_user),
            {f"joins.{class_id}": firestore.DELETE_FIELD},
        )
    batch.commit()


# ---- sessions (roll calls) -------------------------------------------------

def get_session(class_id, day):
    doc = _classes().document(class_id).collection("sessions").document(day).get()
    return doc.to_dict() if doc.exists else None


def save_session(class_id, day, marks):
    class_ref = _classes().document(class_id)
    current = (class_ref.get().to_dict() or {}).get("last_session", "")
    batch = db().batch()
    batch.set(
        class_ref.collection("sessions").document(day),
        {"date": day, "marks": marks, "updated_at": firestore.SERVER_TIMESTAMP},
    )
    if day >= current:
        batch.update(class_ref, {"last_session": day})
    batch.commit()


def list_sessions(class_id, limit=60):
    query = (
        _classes()
        .document(class_id)
        .collection("sessions")
        .order_by("date", direction=firestore.Query.DESCENDING)
        .limit(limit)
    )
    return [d.to_dict() for d in query.stream()]
