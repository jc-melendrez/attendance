from .auth import current_user


def account(request):
    return {"account": current_user(request)}
