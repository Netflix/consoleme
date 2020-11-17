"""Docstring in public module."""
import os
import sys

import ujson as json
from tornado.testing import AsyncHTTPTestCase

from consoleme.config import config

APP_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(os.path.join(APP_ROOT, ".."))


class TestSiteLogin(AsyncHTTPTestCase):
    def get_app(self):
        from consoleme.routes import make_app

        return make_app(jwt_validator=lambda x: {})

    def test_sitelogin(self):
        headers = {
            config.get("auth.user_header_name"): "user@example.com",
            config.get("auth.groups_header_name"): "groupa,groupb,groupc",
        }

        response = self.fetch("/api/v1/siteconfig", headers=headers)
        self.assertEqual(response.code, 200)
        response_j = json.loads(response.body)
        consoleme_logo = response_j.pop("consoleme_logo")
        self.assertIn("/static/logos", consoleme_logo)
        self.assertEqual(
            response_j,
            {
                "google_tracking_uri": None,
                "documentation_url": "https://github.com/Netflix/consoleme/",
                "support_contact": "consoleme-support@example.com",
                "support_chat_url": "https://www.example.com/slack/channel",
                "security_logo": None,
            },
        )
