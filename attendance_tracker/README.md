# Rollcall: a basic attendance tracker (Django + Firestore)

Two roles, teacher and student.
- Teachers make classes, add students, take roll by tapping names, and see reports.
- Students join a class with a class code and see only their own attendance.

Text only: no images, no Firebase Storage.

## 1. Firebase setup
1. Create a project at https://console.firebase.google.com
2. Build > Firestore Database > Create database (Native mode, pick a nearby region).
3. Project settings > Service accounts > Generate new private key. Save the JSON
   file somewhere safe, outside this folder or at least never committed to Git.
4. Rules: leave them locked (deny all). Django uses the Admin SDK on the server,
   which does not go through client rules.

## 2. Run it
```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

export FIREBASE_KEY_PATH=/path/to/your-service-account.json   # Windows: set FIREBASE_KEY_PATH=...
export TEACHER_SIGNUP_CODE=pick-something-private
python manage.py runserver
```
Open http://127.0.0.1:8000

On EC2 or another server, also set `ALLOWED_HOSTS` (comma separated) and run
`python manage.py runserver 0.0.0.0:8000`.

## 3. Accounts and roles
- **Teacher code:** teachers must enter `TEACHER_SIGNUP_CODE` when they sign up, so a
  student cannot make themselves a teacher. With `DJANGO_DEBUG=1` (the default) the code
  is `rollcall-teacher` if you don't set one. In production (`DJANGO_DEBUG=0`), if the
  variable is empty, teacher sign-up is switched off.
- **Students:** sign up, then enter the class code shown on the teacher's class page.
  That links their account to a student record in the class.
- **Walk-ins:** teachers can still add names with no account. Roll call treats both the same.
- **Access rules:** a teacher only sees classes they created. A student only sees classes
  they joined, and only their own marks. Removing a student also unlinks their account.
- **Passwords** are hashed (PBKDF2). After 5 wrong tries on a username, login is
  locked for 15 minutes.
- The login session is a signed cookie, so no SQL database is needed. Set
  `SECURE_COOKIES=1` once you serve the site over HTTPS.
- Classes created before login existed have no owner and will not show up.

## 4. Firestore layout
```
users/{username}             name, role, password_hash, joins {classId: studentId}
classes/{classId}            name, owner, join_code, student_count, last_session, created_at
  students/{studentId}       name, user_id (if they joined with an account), created_at
  sessions/{YYYY-MM-DD}      date, marks {studentId: present|late|absent}, updated_at
```
One document per roll call (the date is its id), so saving a day again edits it.
The username is the user document id, which keeps usernames unique.

## 5. UI principles used (not Jakob's Law)
- Fitts's Law: tiles are at least 120px tall, and Save sits in a bottom bar within thumb reach.
- Hick's Law: each screen has one primary action.
- Von Restorff effect: the main action is the only solid blue block; the save bar is the only dark one.
- Goal-gradient and Zeigarnik: a progress rail shows how much roll is left.
- Doherty threshold: tiles respond instantly (no page reload while marking).
- Peak-end rule: saving ends on a stamped summary showing who is absent.
- Common Region and Proximity: lists use rules, and each roll call's counts sit with its date.
- Status is never color alone: each state has its own icon and word.
- Signup role choice uses the same tile style as roll call, with a checkmark on the selected role.

## Not included (on purpose, to stay basic)
- Password reset and email verification.
- Students leaving a class on their own (the teacher removes them).
- Deleting a whole class.
