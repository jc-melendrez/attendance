"""Session helpers and role checks. Roles: "teacher" and "student"."""
from functools import wraps
from urllib.parse import quote

from django.shortcuts import redirect
from django.urls import reverse


def current_user(request):
    session = getattr(request, "session", None)
    uid = session.get("uid") if session is not None else None
    if not uid:
        return None
    return {
        "uid": uid,
        "role": session.get("role"),
        "name": session.get("name", uid),
    }


def sign_in(request, user):
    request.session.flush()  # fresh session on every login
    request.session["uid"] = user["username"]
    request.session["role"] = user["role"]
    request.session["name"] = user["name"]


def sign_out(request):
    request.session.flush()


def _require(role):
    def decorator(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            user = current_user(request)
            if not user:
                return redirect(f"{reverse('login')}?next={quote(request.get_full_path())}")
            if user["role"] != role:
                return redirect("home")  # home sends each role to its own page
            request.account = user
            return view(request, *args, **kwargs)

        return wrapper

    return decorator


teacher_required = _require("teacher")
student_required = _require("student")
