"""Docstring in public module."""
import os
import sys

import ujson as json
from tornado.testing import AsyncHTTPTestCase

APP_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(os.path.join(APP_ROOT, ".."))


class TestUserProfile(AsyncHTTPTestCase):
    def get_app(self):
        from consoleme.routes import make_app

        return make_app(jwt_validator=lambda x: {})

    def test_profile(self):
        from consoleme.config import config

        self.maxDiff = None
        headers = {
            config.get("auth.user_header_name"): "user@example.com",
            config.get("auth.groups_header_name"): "groupa,groupb,groupc",
        }

        response = self.fetch("/api/v2/user_profile", headers=headers)
        self.assertEqual(response.code, 200)
        response_j = json.loads(response.body)
        consoleme_logo = response_j["site_config"].pop("consoleme_logo")
        self.assertIn("/images/logos/", consoleme_logo)
        self.assertEqual(
            response_j,
            {
                "site_config": {
                    "google_analytics": {"tracking_id": None, "options": {}},
                    "documentation_url": "https://github.com/Netflix/consoleme/",
                    "support_contact": "consoleme-support@example.com",
                    "support_chat_url": "https://www.example.com/slack/channel",
                    "security_logo": None,
                    "security_url": None,
                    "landing_url": None,
                    "temp_policy_support": True,
                    "notifications": {"enabled": None, "request_interval": 60},
                    "cloudtrail_denies_policy_generation": True,
                },
                "user": "user@example.com",
                "can_logout": False,
                "is_contractor": False,
                "employee_photo_url": "https://www.gravatar.com/avatar/b58996c504c5638798eb6b511e6f49af?d=mp",
                "employee_info_url": None,
                "authorization": {
                    "can_edit_policies": False,
                    "can_create_roles": False,
                    "can_delete_iam_principals": False,
                },
                "pages": {
                    "header": {
                        "custom_header_message_title": "Warning:",
                        "custom_header_message_text": "This configuration has no authentication configured. Do not use in a production environment. Do not publicly expose this endpoint or your AWS environment will be compromised! Click [here](/generate_config) to generate a configuration.",
                        "custom_header_message_route": ".*",
                    },
                    "groups": {"enabled": False},
                    "users": {"enabled": False},
                    "policies": {"enabled": True},
                    "self_service": {"enabled": True},
                    "api_health": {"enabled": False},
                    "audit": {"enabled": False},
                    "config": {"enabled": False},
                },
                "accounts": {"123456789012": "default_account"},
            },
        )
