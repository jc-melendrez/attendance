import hmac
import re

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.core.cache import cache
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from . import services
from .auth import current_user, sign_in, sign_out

USERNAME_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{2,29}$")
MAX_FAILS = 5
LOCK_SECONDS = 15 * 60

_dummy = None


def _dummy_hash():
    # Checked when the username does not exist, so timing doesn't reveal which names exist.
    global _dummy
    if _dummy is None:
        _dummy = make_password("not-a-real-password")
    return _dummy


def _safe_next(request, value):
    if value and url_has_allowed_host_and_scheme(
        value, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return value
    return ""


def login_view(request):
    if current_user(request):
        return redirect("home")

    nxt = request.POST.get("next", request.GET.get("next", ""))
    error = ""
    username = ""

    if request.method == "POST":
        username = request.POST.get("username", "").strip().lower()
        password = request.POST.get("password", "")
        key = f"login-fails:{username}"

        if cache.get(key, 0) >= MAX_FAILS:
            error = "Too many tries. Wait 15 minutes, then try again."
        else:
            user = services.get_user(username) if USERNAME_RE.match(username) else None
            valid = check_password(
                password, user["password_hash"] if user else _dummy_hash()
            )
            if user and valid:
                cache.delete(key)
                sign_in(request, user)
                return redirect(_safe_next(request, nxt) or "home")
            cache.set(key, cache.get(key, 0) + 1, LOCK_SECONDS)
            error = "That username and password don't match."

    return render(
        request, "tracker/login.html", {"error": error, "next": nxt, "username": username}
    )


def signup_view(request):
    if current_user(request):
        return redirect("home")

    form = {"role": "student", "name": "", "username": ""}
    errors = {}

    if request.method == "POST":
        role = request.POST.get("role", "student")
        if role not in ("teacher", "student"):
            role = "student"
        name = request.POST.get("name", "").strip()[:60]
        username = request.POST.get("username", "").strip().lower()
        password = request.POST.get("password", "")
        form = {"role": role, "name": name, "username": username}

        if not name:
            errors["name"] = "Enter your name."
        if not USERNAME_RE.match(username):
            errors["username"] = "Use 3 to 30 letters, numbers, dots, dashes or underscores."
        if len(password) < 8:
            errors["password"] = "Use at least 8 characters."
        elif len(password) > 128:
            errors["password"] = "Use 128 characters or fewer."

        if role == "teacher":
            expected = settings.TEACHER_SIGNUP_CODE
            given = request.POST.get("teacher_code", "").strip()
            if not expected:
                errors["teacher_code"] = (
                    "Teacher sign-up is switched off. The site owner needs to set a teacher code."
                )
            elif not hmac.compare_digest(given.encode(), expected.encode()):
                errors["teacher_code"] = "That teacher code isn't right."

        if not errors:
            try:
                services.create_user(username, name, role, make_password(password))
            except services.UsernameTaken:
                errors["username"] = "That username is taken. Try another."
            else:
                sign_in(request, {"username": username, "name": name, "role": role})
                return redirect("home")

    return render(request, "tracker/signup.html", {"form": form, "errors": errors})


@require_POST
def logout_view(request):
    sign_out(request)
    return redirect("login")
