import ujson as json
from deepdiff import DeepDiff
from tornado.testing import AsyncHTTPTestCase


class TestRequestsHandler(AsyncHTTPTestCase):
    def get_app(self):
        from consoleme.config import config

        self.config = config

        from consoleme.routes import make_app

        return make_app(jwt_validator=lambda x: {})

    def test_get(self):
        # Method not allowed
        headers = {
            self.config.get("auth.user_header_name"): "user@github.com",
            self.config.get("auth.groups_header_name"): "groupa,groupb,groupc",
        }
        response = self.fetch("/api/v2/requests", method="GET", headers=headers)
        self.assertEqual(response.code, 405)

    def test_post(self):
        mock_request_data = [
            {
                "request_id": 12345,
                "username": "user@example.com",
                "request_time": 22345,
            },
            {
                "request_id": 12346,
                "username": "userb@example.com",
                "request_time": 12345,
            },
        ]

        expected_response = {
            "totalCount": 2,
            "filteredCount": 2,
            "data": mock_request_data,
        }

        from consoleme.lib.redis import RedisHandler

        # Mocked by fakeredis
        red = RedisHandler().redis_sync()
        red.set(
            self.config.get("cache_policy_requests.redis_key", "ALL_POLICY_REQUESTS"),
            json.dumps(mock_request_data),
        )

        headers = {
            self.config.get("auth.user_header_name"): "user@github.com",
            self.config.get("auth.groups_header_name"): "groupa,groupb,groupc",
        }
        response = self.fetch(
            "/api/v2/requests", method="POST", headers=headers, body="{}"
        )
        self.assertEqual(response.code, 200)
        diff = DeepDiff(json.loads(response.body), expected_response)
        self.assertFalse(diff)

    def test_post_limit(self):
        mock_request_data = [
            {"request_id": 12345, "username": "user@example.com"},
            {"request_id": 12346, "username": "userb@example.com"},
        ]

        from consoleme.lib.redis import RedisHandler

        # Mocked by fakeredis
        red = RedisHandler().redis_sync()
        red.set(
            self.config.get("cache_policy_requests.redis_key", "ALL_POLICY_REQUESTS"),
            json.dumps(mock_request_data),
        )

        headers = {
            self.config.get("auth.user_header_name"): "user@github.com",
            self.config.get("auth.groups_header_name"): "groupa,groupb,groupc",
        }
        response = self.fetch(
            "/api/v2/requests",
            method="POST",
            headers=headers,
            body=json.dumps({"limit": 1}),
        )
        self.assertEqual(response.code, 200)
        self.assertEqual(len(json.loads(response.body)), 3)
        self.assertEqual(len(json.loads(response.body)["data"]), 1)

    def test_post_filter(self):
        mock_request_data = [
            {"request_id": 12345, "username": "user@example.com"},
            {"request_id": 12346, "username": "userb@example.com"},
        ]

        from consoleme.lib.redis import RedisHandler

        # Mocked by fakeredis
        red = RedisHandler().redis_sync()
        red.set(
            self.config.get("cache_policy_requests.redis_key", "ALL_POLICY_REQUESTS"),
            json.dumps(mock_request_data),
        )

        headers = {
            self.config.get("auth.user_header_name"): "user@github.com",
            self.config.get("auth.groups_header_name"): "groupa,groupb,groupc",
        }
        response = self.fetch(
            "/api/v2/requests",
            method="POST",
            headers=headers,
            body=json.dumps({"filters": {"request_id": "12346"}}),
        )
        self.assertEqual(response.code, 200)
        res = json.loads(response.body)
        self.assertEqual(len(json.loads(response.body)), 3)
        self.assertEqual(len(json.loads(response.body)["data"]), 1)
        self.assertEqual(res["data"][0], mock_request_data[1])


class TestRequestDetailHandler(AsyncHTTPTestCase):
    def get_app(self):
        from consoleme.routes import make_app

        return make_app(jwt_validator=lambda x: {})

    def test_get(self):
        # expected = {
        #     "status": 501,
        #     "title": "Not Implemented",
        #     "message": "Get request details",
        # }
        # headers = {
        #     config.get("auth.user_header_name"): "user@github.com",
        #     config.get("auth.groups_header_name"): "groupa,groupb,groupc",
        # }
        # response = self.fetch(
        #     "/api/v2/requests/16fd2706-8baf-433b-82eb-8c7fada847da",
        #     method="GET",
        #     headers=headers,
        # )
        # TODO: add unit tests
        pass
        # self.assertEqual(response.code, 501)
        # self.assertDictEqual(json.loads(response.body), expected)

    def test_put(self):
        # expected = {
        #     "status": 501,
        #     "title": "Not Implemented",
        #     "message": "Update request details",
        # }
        # headers = {
        #     config.get("auth.user_header_name"): "user@github.com",
        #     config.get("auth.groups_header_name"): "groupa,groupb,groupc",
        # }
        # response = self.fetch(
        #     "/api/v2/requests/16fd2706-8baf-433b-82eb-8c7fada847da",
        #     method="PUT",
        #     headers=headers,
        #     body="{}",
        # )
        # self.assertEqual(response.code, 501)
        # self.assertDictEqual(json.loads(response.body), expected)
        # TODO: add unit tests
        pass
