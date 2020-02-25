"""Docstring in public module."""

# import unittest
import os
import sys

import mock
from mock import Mock, patch
from tornado.httpclient import AsyncHTTPClient

# from tornado.options import options
from tornado.testing import AsyncHTTPTestCase

APP_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(os.path.join(APP_ROOT, ".."))


class TestMain(AsyncHTTPTestCase):
    """Docstring in public class."""

    def setUp(self):
        super(TestMain, self).setUp()
        self.client = AsyncHTTPClient(force_instance=True)

    def get_app(self):
        from consoleme import __main__

        self.__main__ = __main__
        app = self.__main__.main()
        return app

    @patch("consoleme.__main__.asyncio.get_event_loop")
    def test_main(self, mock_ioloop):
        """Docstring in public method."""
        self.__main__.app = Mock()
        self.__main__.app.listen = Mock()
        with patch.object(self.__main__, "main", return_value=42):
            with patch.object(self.__main__, "__name__", "__main__"):
                self.__main__.config = {}
                mock_ioloop.run_forever = mock.Mock()
                mock_ioloop.add_handler = mock.Mock()
                mock_ioloop.start = mock.Mock()
                self.__main__.init()


class TestHealth(AsyncHTTPTestCase):
    def get_app(self):
        from consoleme.routes import make_app

        return make_app(jwt_validator=lambda x: {})

    def test_health(self):
        """Docstring in public method."""
        response = self.fetch("/healthcheck", method="GET", follow_redirects=False)
        self.assertEqual(b"OK", response.body)
