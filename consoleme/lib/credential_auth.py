from consoleme.config import config


async def authenticate_user_by_credentials(request):
    # If request is a POST and it has username, password, etc, then validate and return
    # If request doesn't have these parameters, render login page
    email = None
    groups = None

    if request.request.path == "/auth":
        # If request is post and has credentials, validate or return error
        pass

    if email and groups and config.get("auth.set_auth_cookie"):
        pass
        # encoded_cookie = await generate_jwt_token(email, groups)
        # request.set_cookie(config.get("auth_cookie_name", "consoleme_auth"), encoded_cookie)

    if request.request.path != "/auth":
        request.redirect("/auth")
