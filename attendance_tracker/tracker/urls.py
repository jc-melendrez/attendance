from django.urls import path

from . import accounts, views

urlpatterns = [
    # accounts
    path("login/", accounts.login_view, name="login"),
    path("signup/", accounts.signup_view, name="signup"),
    path("logout/", accounts.logout_view, name="logout"),
    # "/" sends each role to its own home
    path("", views.home, name="home"),
    # teacher
    path("class/<str:class_id>/", views.class_detail, name="class_detail"),
    path("class/<str:class_id>/students/add/", views.add_students, name="add_students"),
    path(
        "class/<str:class_id>/students/<str:student_id>/remove/",
        views.remove_student,
        name="remove_student",
    ),
    path("class/<str:class_id>/roll/", views.roll_call, name="roll_today"),
    path("class/<str:class_id>/roll/<str:day>/", views.roll_call, name="roll_call"),
    path("class/<str:class_id>/roll/<str:day>/done/", views.roll_done, name="roll_done"),
    path("class/<str:class_id>/report/", views.report, name="report"),
    # student
    path("my/", views.student_home, name="student_home"),
    path("my/class/<str:class_id>/", views.student_class, name="student_class"),
]
