from collections import Counter
from datetime import date

from django.http import Http404
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from . import services
from .auth import current_user, student_required, teacher_required

WORD = {"present": "Present", "late": "Late", "absent": "Absent", "": "Not marked"}


# ---- small helpers ---------------------------------------------------------

def _long(day):
    return f"{day.strftime('%A')} {day.day} {day.strftime('%B')}"


def _short(day):
    return f"{day.strftime('%a')} {day.day} {day.strftime('%b')}"


def _tally(marks):
    counts = Counter((marks or {}).values())
    return {k: counts.get(k, 0) for k in services.STATUSES}


def _class_or_404(request, class_id):
    """A teacher can only open classes they own. Anyone else gets a 404."""
    klass = services.get_class(class_id)
    if not klass or klass.get("owner") != request.account["uid"]:
        raise Http404("Class not found")
    klass.setdefault("student_count", 0)
    return klass


def _parse_day(value):
    if not value:
        return timezone.localdate()
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise Http404("Invalid date")


# ---- home: each role goes to its own page ----------------------------------

def home(request):
    user = current_user(request)
    if not user:
        return redirect("login")
    if user["role"] == "student":
        return redirect("student_home")
    return teacher_home(request)


# ---- teacher ---------------------------------------------------------------

@teacher_required
def teacher_home(request):
    error = ""
    if request.method == "POST":
        name = request.POST.get("name", "").strip()[:80]
        if name:
            class_id = services.create_class(name, request.account["uid"])
            return redirect("class_detail", class_id=class_id)
        error = "Enter a class name to add it."

    classes = services.list_classes(request.account["uid"])
    for c in classes:
        c.setdefault("student_count", 0)
        last = c.get("last_session")
        c["last_label"] = _short(date.fromisoformat(last)) if last else ""
    return render(request, "tracker/home.html", {"classes": classes, "error": error})


@teacher_required
def class_detail(request, class_id):
    klass = _class_or_404(request, class_id)
    students = services.list_students(class_id)
    today = timezone.localdate()

    today_session = services.get_session(class_id, today.isoformat())
    today_tally = _tally(today_session.get("marks")) if today_session else None

    sessions = []
    for s in services.list_sessions(class_id, limit=30):
        tally = _tally(s.get("marks"))
        sessions.append(
            {
                "date": s["date"],
                "label": _short(date.fromisoformat(s["date"])),
                "t": tally,
                "here": tally["present"] + tally["late"],
            }
        )

    return render(
        request,
        "tracker/class_detail.html",
        {
            "klass": klass,
            "students": students,
            "today_label": _long(today),
            "today_tally": today_tally,
            "sessions": sessions,
        },
    )


@teacher_required
@require_POST
def add_students(request, class_id):
    _class_or_404(request, class_id)
    names = []
    for line in request.POST.get("names", "").splitlines():
        name = line.strip()[:80]
        if name:
            names.append(name)
    names = names[:100]  # one Firestore batch, keep it small
    if names:
        services.add_students(class_id, names)
    return redirect("class_detail", class_id=class_id)


@teacher_required
@require_POST
def remove_student(request, class_id, student_id):
    _class_or_404(request, class_id)
    services.delete_student(class_id, student_id)
    return redirect("class_detail", class_id=class_id)


@teacher_required
def roll_call(request, class_id, day=None):
    klass = _class_or_404(request, class_id)
    day = _parse_day(day)
    students = services.list_students(class_id)

    if request.method == "POST":
        marks = {}
        for s in students:
            value = request.POST.get(f"mark_{s['id']}", "")
            if value in services.STATUSES:
                marks[s["id"]] = value
        services.save_session(class_id, day.isoformat(), marks)
        return redirect("roll_done", class_id=class_id, day=day.isoformat())

    session = services.get_session(class_id, day.isoformat())
    existing = (session or {}).get("marks", {})
    for s in students:
        s["mark"] = existing.get(s["id"], "")
        s["word"] = WORD[s["mark"]]

    return render(
        request,
        "tracker/roll_call.html",
        {"klass": klass, "students": students, "day_label": _long(day)},
    )


@teacher_required
def roll_done(request, class_id, day):
    klass = _class_or_404(request, class_id)
    day = _parse_day(day)
    session = services.get_session(class_id, day.isoformat())
    if not session:
        return redirect("roll_call", class_id=class_id, day=day.isoformat())

    students = services.list_students(class_id)
    marks = session.get("marks", {})
    tally = _tally(marks)
    total = len(students)
    marked = sum(1 for s in students if s["id"] in marks)
    absent_names = [s["name"] for s in students if marks.get(s["id"]) == "absent"]

    return render(
        request,
        "tracker/roll_done.html",
        {
            "klass": klass,
            "day_label": _long(day),
            "day_iso": day.isoformat(),
            "t": tally,
            "total": total,
            "here": tally["present"] + tally["late"],
            "unmarked": max(total - marked, 0),
            "absent_names": absent_names,
        },
    )


@teacher_required
def report(request, class_id):
    klass = _class_or_404(request, class_id)
    students = services.list_students(class_id)
    sessions = services.list_sessions(class_id, limit=60)  # newest first
    recent = list(reversed(sessions[:12]))  # oldest to newest

    rows = []
    for s in students:
        counts = Counter()
        for session in sessions:
            mark = session.get("marks", {}).get(s["id"])
            if mark:
                counts[mark] += 1
        recorded = sum(counts.values())
        rate = (
            round((counts["present"] + counts["late"]) * 100 / recorded)
            if recorded
            else None
        )
        strip = []
        for session in recent:
            mark = session.get("marks", {}).get(s["id"], "")
            label = _short(date.fromisoformat(session["date"]))
            strip.append({"state": mark, "title": f"{label}: {WORD[mark]}"})
        rows.append(
            {
                "name": s["name"],
                "rate": rate,
                "present": counts["present"],
                "late": counts["late"],
                "absent": counts["absent"],
                "strip": strip,
            }
        )

    # Lowest attendance first, so the students who need attention come first.
    rows.sort(key=lambda r: (r["rate"] is None, r["rate"] if r["rate"] is not None else 0))

    return render(
        request,
        "tracker/report.html",
        {"klass": klass, "rows": rows, "session_count": len(sessions)},
    )


# ---- student ---------------------------------------------------------------

def _summary(class_id, student_id):
    """One student's own attendance in one class."""
    counts = Counter()
    history = []
    for s in services.list_sessions(class_id, limit=60):  # newest first
        mark = s.get("marks", {}).get(student_id, "")
        if mark:
            counts[mark] += 1
        day = date.fromisoformat(s["date"])
        history.append(
            {"label": _long(day), "short": _short(day), "state": mark, "word": WORD[mark]}
        )
    recorded = sum(counts.values())
    rate = (
        round((counts["present"] + counts["late"]) * 100 / recorded) if recorded else None
    )
    return {
        "counts": {k: counts[k] for k in services.STATUSES},
        "rate": rate,
        "recorded": recorded,
        "history": history,
    }


@student_required
def student_home(request):
    user = request.account
    error = ""

    if request.method == "POST":
        code = request.POST.get("code", "").strip().upper().replace(" ", "")
        klass = services.find_class_by_code(code) if code else None
        if klass:
            services.join_class(user["uid"], user["name"], klass["id"])
            return redirect("student_class", class_id=klass["id"])
        error = "No class has that code. Check it with your teacher."

    rows = []
    for class_id, student_id in services.get_joins(user["uid"]).items():
        klass = services.get_class(class_id)
        if not klass:
            continue
        summary = _summary(class_id, student_id)
        latest = summary["history"][0] if summary["history"] else None
        rows.append({"id": class_id, "name": klass["name"], "s": summary, "latest": latest})
    rows.sort(key=lambda r: r["name"].lower())

    return render(request, "tracker/student_home.html", {"rows": rows, "error": error})


@student_required
def student_class(request, class_id):
    student_id = services.get_joins(request.account["uid"]).get(class_id)
    klass = services.get_class(class_id) if student_id else None
    if not klass:
        raise Http404("Class not found")  # students only see classes they joined
    summary = _summary(class_id, student_id)
    return render(
        request,
        "tracker/student_class.html",
        {"klass": klass, "s": summary},
    )
