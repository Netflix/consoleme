import json

from asgiref.sync import async_to_sync
from tornado.testing import AsyncHTTPTestCase


class TestUserRegistrationApi(AsyncHTTPTestCase):
    def get_app(self):
        from consoleme.config import config

        config.CONFIG.config["auth"]["get_user_by_password"] = True
        config.CONFIG.config["auth"]["allow_user_registration"] = True
        from consoleme.routes import make_app

        return make_app(jwt_validator=lambda x: {})

    def tearDown(self) -> None:
        from consoleme.config import config

        config.CONFIG.config["auth"]["get_user_by_password"] = False
        config.CONFIG.config["auth"]["allow_user_registration"] = False

    def test_register_user(self):
        body = json.dumps(
            {
                "username": "testuser5",
                "password": "testuser5password",
            }
        )
        response = self.fetch("/api/v2/user_registration", method="POST", body=body)
        self.assertEqual(response.code, 403)
        self.assertEqual(
            json.loads(response.body),
            {
                "status": "error",
                "reason": "invalid_request",
                "redirect_url": None,
                "status_code": 403,
                "message": None,
                "errors": [
                    "The email address is not valid. It must have exactly one @-sign."
                ],
                "data": None,
            },
        )

        body = json.dumps(
            {
                "username": "testuser5@example.com",
                "password": "testuser5password",
            }
        )
        response = self.fetch("/api/v2/user_registration", method="POST", body=body)
        self.assertEqual(response.code, 200)
        self.assertEqual(
            json.loads(response.body),
            {
                "status": "success",
                "reason": None,
                "redirect_url": None,
                "status_code": 200,
                "message": "Successfully created user testuser5@example.com.",
                "errors": None,
                "data": None,
            },
        )


class TestLoginApi(AsyncHTTPTestCase):
    def get_app(self):
        from consoleme.config import config

        config.CONFIG.config["auth"]["get_user_by_password"] = True
        config.CONFIG.config["auth"]["set_auth_cookie"] = True
        from consoleme.routes import make_app

        return make_app(jwt_validator=lambda x: {})

    def tearDown(self) -> None:
        from consoleme.config import config

        config.CONFIG.config["auth"]["get_user_by_password"] = False
        config.CONFIG.config["auth"]["set_auth_cookie"] = False

    def test_login_post_no_user(self):
        body = json.dumps(
            {"username": "fakeuser", "password": "pass", "after_redirect_uri": "/"}
        )
        response = self.fetch("/api/v2/login", method="POST", body=body)
        self.assertEqual(response.code, 403)
        self.assertEqual(
            json.loads(response.body),
            {
                "status": "error",
                "reason": "authentication_failure",
                "redirect_url": None,
                "status_code": 403,
                "message": None,
                "errors": ["User doesn't exist, or password is incorrect."],
                "data": None,
            },
        )

    def test_login_post_invalid_password(self):
        from consoleme.lib.dynamo import UserDynamoHandler

        ddb = UserDynamoHandler()
        ddb.create_user("testuser", "correctpassword", ["group1", "group2@example.com"])
        body = json.dumps(
            {"username": "testuser", "password": "wrongpass", "after_redirect_uri": "/"}
        )
        response = self.fetch("/api/v2/login", method="POST", body=body)
        self.assertEqual(response.code, 403)
        self.assertEqual(
            json.loads(response.body),
            {
                "data": None,
                "errors": ["User doesn't exist, or password is incorrect."],
                "message": None,
                "reason": "authentication_failure",
                "redirect_url": None,
                "status": "error",
                "status_code": 403,
            },
        )

    def test_login_post_success(self):
        from consoleme.lib.dynamo import UserDynamoHandler

        ddb = UserDynamoHandler()
        ddb.create_user(
            "testuser2", "correctpassword", ["group1", "group2@example.com"]
        )
        body = json.dumps(
            {
                "username": "testuser2",
                "password": "correctpassword",
                "after_redirect_uri": "/",
            }
        )
        response = self.fetch("/api/v2/login", method="POST", body=body)
        self.assertEqual(response.code, 200)
        self.assertEqual(
            json.loads(response.body),
            {
                "status": "redirect",
                "reason": "authenticated_redirect",
                "redirect_url": "/",
                "status_code": 200,
                "message": "User has successfully authenticated. Redirecting to their intended destination.",
                "errors": None,
                "data": None,
            },
        )


class TestUserApi(AsyncHTTPTestCase):
    def get_app(self):
        from consoleme.routes import make_app

        return make_app(jwt_validator=lambda x: {})

    def test_create_user(self):
        from consoleme.config import config

        headers = {
            config.get("auth.user_header_name"): "consoleme_admins@example.com",
            config.get("auth.groups_header_name"): "groupa,groupb,groupc",
        }

        body = json.dumps(
            {
                "action": "create",
                "username": "testuser3",
                "password": "testuser3password",
                "groups": ["group1", "group2", "group3"],
            }
        )
        response = self.fetch("/api/v2/user", headers=headers, method="POST", body=body)
        self.assertEqual(response.code, 200)
        self.assertEqual(
            json.loads(response.body),
            {
                "status": "success",
                "reason": None,
                "redirect_url": None,
                "status_code": 200,
                "message": "Successfully created user testuser3.",
                "errors": None,
                "data": None,
            },
        )

        # Verify new user works
        from consoleme.lib.dynamo import UserDynamoHandler
        from consoleme.models import LoginAttemptModel

        ddb = UserDynamoHandler()
        login_attempt_success = LoginAttemptModel(
            username="testuser3", password="testuser3password"
        )

        should_pass = async_to_sync(ddb.authenticate_user)(login_attempt_success)
        self.assertEqual(
            should_pass.dict(),
            {
                "authenticated": True,
                "errors": None,
                "username": "testuser3",
                "groups": ["group1", "group2", "group3"],
            },
        )
        login_attempt_fail = LoginAttemptModel(
            username="testuser3", password="wrongpassword"
        )

        should_fail = async_to_sync(ddb.authenticate_user)(login_attempt_fail)

        self.assertEqual(
            should_fail.dict(),
            {
                "authenticated": False,
                "errors": ["User doesn't exist, or password is incorrect."],
                "username": None,
                "groups": None,
            },
        )

        # Update password
        body = json.dumps(
            {
                "action": "update",
                "username": "testuser3",
                "password": "testuser3newpassword",
            }
        )
        response = self.fetch("/api/v2/user", headers=headers, method="POST", body=body)
        self.assertEqual(response.code, 200)
        self.assertEqual(
            json.loads(response.body),
            {
                "status": "success",
                "reason": None,
                "redirect_url": None,
                "status_code": 200,
                "message": "Successfully updated user testuser3.",
                "errors": None,
                "data": None,
            },
        )

        # Update groups
        body = json.dumps(
            {
                "action": "update",
                "username": "testuser3",
                "groups": ["group1", "group2", "group3", "newgroup"],
            }
        )
        response = self.fetch("/api/v2/user", headers=headers, method="POST", body=body)
        self.assertEqual(response.code, 200)
        self.assertEqual(
            json.loads(response.body),
            {
                "status": "success",
                "reason": None,
                "redirect_url": None,
                "status_code": 200,
                "message": "Successfully updated user testuser3.",
                "errors": None,
                "data": None,
            },
        )
        # Update groups and password AT THE SAME TIME!!1
        body = json.dumps(
            {
                "action": "update",
                "username": "testuser3",
                "password": "testuser3newpassword2",
                "groups": ["group1", "group2", "group3", "newgroup", "newgroup2"],
            }
        )
        response = self.fetch("/api/v2/user", headers=headers, method="POST", body=body)
        self.assertEqual(response.code, 200)
        self.assertEqual(
            json.loads(response.body),
            {
                "status": "success",
                "reason": None,
                "redirect_url": None,
                "status_code": 200,
                "message": "Successfully updated user testuser3.",
                "errors": None,
                "data": None,
            },
        )

        # Delete the user

        body = json.dumps(
            {
                "action": "delete",
                "username": "testuser3",
            }
        )

        response = self.fetch("/api/v2/user", headers=headers, method="POST", body=body)
        self.assertEqual(response.code, 200)
        self.assertEqual(
            json.loads(response.body),
            {
                "status": "success",
                "reason": None,
                "redirect_url": None,
                "status_code": 200,
                "message": "Successfully deleted user testuser3.",
                "errors": None,
                "data": None,
            },
        )
