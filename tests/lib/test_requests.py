import asyncio

from mock import patch
from tornado.concurrent import Future
from tornado.testing import AsyncTestCase

from consoleme.lib.plugins import get_plugin_by_name
from tests.conftest import create_future


class TestRequestsLibrary(AsyncTestCase):
    def setUp(self) -> None:
        from consoleme.config import config
        from consoleme.exceptions.exceptions import NoMatchingRequest

        self.NoMatchingRequest = NoMatchingRequest
        auth = get_plugin_by_name(config.get("plugins.auth", "default_auth"))()
        self.Group = auth.Group

    def tearDown(self) -> None:
        pass

    @patch("consoleme.lib.requests.UserDynamoHandler")
    @patch("consoleme.lib.requests.auth")
    def test_get_user_requests(self, mock_auth, mock_user_dynamo_handler):
        from consoleme.lib.requests import get_user_requests

        """Chuck Norris has a request and is an secondary approver for group1"""
        mock_user = "cnorris"
        mock_requests = [
            {"username": mock_user},
            {"username": "edward", "group": "group1"},
            {"username": "clair"},
        ]
        mock_secondary_approver = [{"name": "group1"}]
        mock_user_dynamo_handler.return_value.get_all_requests.return_value = (
            create_future(mock_requests)
        )

        mock_sa = Future()
        mock_sa.set_result(mock_secondary_approver)
        mock_auth.query_cached_groups.return_value = mock_sa

        requests = asyncio.get_event_loop().run_until_complete(
            get_user_requests(mock_user, ["group1"])
        )
        self.assertEqual(
            requests,
            mock_requests[: len(mock_requests) - 1],
            "Only clair should be missing",
        )

    @patch("consoleme.lib.requests.UserDynamoHandler")
    @patch("consoleme.lib.requests.auth")
    def test_get_all_pending_requests_api(self, mock_auth, mock_user_dynamo_handler):
        """Chuck Norris has a request and is an secondary approver for group1"""
        from consoleme.lib.requests import get_all_pending_requests_api

        mock_user = "cnorris"
        mock_requests = [
            {"username": mock_user, "status": "pending"},
            {"username": "edward", "group": "group1", "status": "pending"},
            {"username": "clair", "status": "approved"},
        ]
        mock_secondary_approver = {"group1": ["group1"]}
        mock_user_dynamo_handler.return_value.get_all_requests.return_value = (
            create_future(mock_requests)
        )

        mock_auth.get_secondary_approvers.return_value = create_future(
            mock_secondary_approver
        )

        requests = asyncio.get_event_loop().run_until_complete(
            get_all_pending_requests_api(mock_user)
        )
        self.assertEqual(
            requests,
            mock_requests[: len(mock_requests) - 1],
            "Only clair should be missing",
        )

    @patch("consoleme.lib.requests.UserDynamoHandler")
    @patch("consoleme.lib.requests.auth")
    def test_get_request_by_id(self, mock_auth, mock_user_dynamo_handler):
        """Chuck Norris has a request and is an secondary approver for group1"""
        from consoleme.lib.requests import get_request_by_id

        mock_user = "cnorris"
        mock_requests = [
            {"username": mock_user, "status": "pending"},
            {"username": "edward", "group": "group1", "status": "pending"},
            {"username": "clair", "status": "approved"},
        ]
        mock_secondary_approver = ["group1"]
        mock_user_dynamo_handler.return_value.resolve_request_ids.return_value = (
            mock_requests
        )

        mock_sa = Future()
        mock_sa.set_result(mock_secondary_approver)
        mock_auth.get_secondary_approvers.return_value = mock_sa

        requests = asyncio.get_event_loop().run_until_complete(
            get_request_by_id(mock_user, "123456")
        )
        self.assertEqual(
            requests, mock_requests[0], "Only the first request should be returned"
        )

    @patch("consoleme.lib.requests.UserDynamoHandler")
    @patch("consoleme.lib.requests.auth")
    def test_get_request_by_id_no_match(self, mock_auth, mock_user_dynamo_handler):
        """Chuck Norris has a request and is an secondary approver for group1"""
        from consoleme.lib.requests import get_request_by_id

        mock_user = "cnorris"
        mock_requests = []
        mock_secondary_approver = ["group1"]
        mock_user_dynamo_handler.return_value.resolve_request_ids.return_value = (
            mock_requests
        )

        mock_sa = Future()
        mock_sa.set_result(mock_secondary_approver)
        mock_auth.get_secondary_approvers.return_value = mock_sa

        requests = asyncio.get_event_loop().run_until_complete(
            get_request_by_id(mock_user, "123456")
        )
        self.assertEqual(
            requests, None, "None should be returned when there is no match"
        )

    @patch("consoleme.lib.requests.UserDynamoHandler")
    @patch("consoleme.lib.requests.auth")
    def test_get_request_by_id_failure(self, mock_auth, mock_user_dynamo_handler):
        """Chuck Norris has a request and is an secondary approver for group1"""
        from consoleme.lib.requests import get_request_by_id

        mock_user = "cnorris"
        mock_requests = self.NoMatchingRequest("foo")
        mock_secondary_approver = ["group1"]
        mock_user_dynamo_handler.return_value.resolve_request_ids.side_effect = (
            mock_requests
        )

        mock_sa = Future()
        mock_sa.set_result(mock_secondary_approver)
        mock_auth.get_secondary_approvers.return_value = mock_sa

        requests = asyncio.get_event_loop().run_until_complete(
            get_request_by_id(mock_user, "123456")
        )
        self.assertEqual(
            requests, None, "None should be returned when there is no match"
        )

    @patch("consoleme.lib.requests.UserDynamoHandler")
    def test_get_existing_pending_request(self, mock_user_dynamo_handler):
        """Chuck Norris has a request and is an secondary approver for group1"""
        from consoleme.lib.requests import get_existing_pending_request

        mock_user = "cnorris"
        group_info = self.Group(**{"name": "group1"})
        mock_requests = [
            {"username": mock_user, "status": "pending"},
            {"username": "edward", "group": "group1", "status": "pending"},
            {"username": "clair", "group": "group2", "status": "pending"},
        ]

        mock_user_dynamo_handler.return_value.get_requests_by_user.return_value = (
            mock_requests
        )

        request = asyncio.get_event_loop().run_until_complete(
            get_existing_pending_request(mock_user, group_info)
        )
        self.assertEqual(request, mock_requests[1], "Second request should match")

    @patch("consoleme.lib.requests.UserDynamoHandler")
    def test_get_existing_pending_request_fail_status(self, mock_user_dynamo_handler):
        """Chuck Norris has a request and is an secondary approver for group1"""
        from consoleme.lib.requests import get_existing_pending_request

        mock_user = "cnorris"
        group_info = self.Group(**{"name": "group1"})
        mock_requests = [
            {"username": mock_user, "status": "pending"},
            {"username": "edward", "group": "group1", "status": "cancelled"},
            {"username": "clair", "group": "group2", "status": "approved"},
        ]

        mock_user_dynamo_handler.return_value.get_requests_by_user.return_value = (
            mock_requests
        )

        request = asyncio.get_event_loop().run_until_complete(
            get_existing_pending_request(mock_user, group_info)
        )
        self.assertEqual(request, None, "No matches - bad status")

    @patch("consoleme.lib.requests.UserDynamoHandler")
    def test_get_existing_pending_request_fail_group(self, mock_user_dynamo_handler):
        """Chuck Norris has a request and is an secondary approver for group1"""
        from consoleme.lib.requests import get_existing_pending_request

        mock_user = "cnorris"
        group_info = self.Group(**{"name": "group1"})
        mock_requests = [
            {"username": mock_user, "status": "pending"},
            {"username": "edward", "group": "group5", "status": "pending"},
            {"username": "clair", "group": "group2", "status": "approved"},
        ]

        mock_user_dynamo_handler.return_value.get_requests_by_user.return_value = (
            mock_requests
        )

        request = asyncio.get_event_loop().run_until_complete(
            get_existing_pending_request(mock_user, group_info)
        )
        self.assertEqual(request, None, "No matches - no group match")
