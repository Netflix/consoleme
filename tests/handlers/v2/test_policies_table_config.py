"""Docstring in public module."""
import os
import sys

import ujson as json
from tornado.testing import AsyncHTTPTestCase

from consoleme.config import config

APP_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(os.path.join(APP_ROOT, ".."))


class TestPoliciesTableConfig(AsyncHTTPTestCase):
    def get_app(self):
        from consoleme.routes import make_app

        return make_app(jwt_validator=lambda x: {})

    def test_policies_table_config(self):
        headers = {
            config.get("auth.user_header_name"): "user@example.com",
            config.get("auth.groups_header_name"): "groupa,groupb,groupc",
        }

        response = self.fetch("/api/v2/policies_table_config", headers=headers)
        self.assertEqual(response.code, 200)
        response_j = json.loads(response.body)
        self.assertEqual(
            response_j,
            {
                "expandableRows": True,
                "tableName": "Policies",
                "tableDescription": "View all of the AWS Resources we know about.",
                "dataEndpoint": "/api/v2/policies?markdown=true",
                "sortable": False,
                "totalRows": 1000,
                "rowsPerPage": 50,
                "serverSideFiltering": True,
                "columns": [
                    {
                        "placeholder": "Account ID",
                        "key": "account_id",
                        "type": "input",
                        "style": {"width": "110px"},
                    },
                    {
                        "placeholder": "Account",
                        "key": "account_name",
                        "type": "input",
                        "style": {"width": "90px"},
                    },
                    {
                        "placeholder": "Resource",
                        "key": "arn",
                        "type": "input",
                        "width": 6,
                        "style": {"whiteSpace": "normal", "wordBreak": "break-all"},
                    },
                    {
                        "placeholder": "Tech",
                        "key": "technology",
                        "type": "input",
                        "style": {"width": "70px"},
                    },
                    {
                        "placeholder": "Template",
                        "key": "templated",
                        "type": "input",
                        "style": {"width": "100px"},
                    },
                    {
                        "placeholder": "Errors",
                        "key": "errors",
                        "color": "red",
                        "width": 1,
                    },
                ],
            },
        )
