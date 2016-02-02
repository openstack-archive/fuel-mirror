# -*- coding: utf-8 -*-

#    Copyright 2015 Mirantis, Inc.
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License along
#    with this program; if not, write to the Free Software Foundation, Inc.,
#    51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import mock
import six
import time

from packetary.library import connections
from packetary.tests import base


@mock.patch("packetary.library.connections.logger")
class TestConnectionManager(base.TestCase):
    def _check_proxies(self, manager, http_proxy, https_proxy):
        for h in manager.opener.handlers:
            if isinstance(h, connections.urllib.ProxyHandler):
                self.assertEqual(
                    (http_proxy, https_proxy),
                    (h.proxies["http"], h.proxies["https"])
                )
                break
        else:
            self.fail("ProxyHandler should be in list of handlers.")

    def test_set_proxy(self, _):
        manager = connections.ConnectionsManager(proxy="http://localhost")
        self._check_proxies(
            manager, "http://localhost", "http://localhost"
        )
        manager = connections.ConnectionsManager(
            proxy="http://localhost", secure_proxy="https://localhost")
        self._check_proxies(
            manager, "http://localhost", "https://localhost"
        )
        manager = connections.ConnectionsManager(retries_num=2)
        self.assertEqual(2, manager.retries_num)
        for h in manager.opener.handlers:
            if isinstance(h, connections.RetryHandler):
                break
        else:
            self.fail("RetryHandler should be in list of handlers.")

    @mock.patch("packetary.library.connections.urllib.build_opener")
    def test_make_request(self, *_):
        manager = connections.ConnectionsManager(retries_num=2)
        request = manager.make_request("/test/file", 0)
        self.assertIsInstance(request, connections.RetryableRequest)
        self.assertEqual("file:///test/file", request.get_full_url())
        self.assertEqual(0, request.offset)
        self.assertEqual(2, request.retries_left)
        request2 = manager.make_request("http://server/path", 100)
        self.assertEqual("http://server/path", request2.get_full_url())
        self.assertEqual(100, request2.offset)

    @mock.patch("packetary.library.connections.urllib.build_opener")
    def test_open_stream(self, *_):
        manager = connections.ConnectionsManager(retries_num=2)
        manager.open_stream("/test/file")
        self.assertEqual(1, manager.opener.open.call_count)
        args = manager.opener.open.call_args[0]
        self.assertIsInstance(args[0], connections.RetryableRequest)
        self.assertEqual(2, args[0].retries_left)

    @mock.patch("packetary.library.connections.urllib.build_opener")
    def test_retries_on_io_error(self, _, logger):
        manager = connections.ConnectionsManager(retries_num=2)
        manager.opener.open.side_effect = [
            IOError("I/O error"),
            mock.MagicMock()
        ]
        manager.open_stream("/test/file")
        self.assertEqual(2, manager.opener.open.call_count)
        logger.exception.assert_called_with(
            "Failed to open url - %s: %s. retries left - %d.",
            "/test/file", "I/O error", 1
        )

        manager.opener.open.side_effect = IOError("I/O error")
        with self.assertRaises(IOError):
            manager.open_stream("/test/file")
        logger.exception.assert_called_with(
            "Failed to open url - %s: %s. retries left - %d.",
            "/test/file", "I/O error", 0
        )

    @mock.patch.multiple(
        "packetary.library.connections.urllib.HTTPHandler",
        http_request=mock.DEFAULT,
        http_open=mock.DEFAULT
    )
    def test_retries_on_50x(self, logger, http_open, http_request):
        request = connections.RetryableRequest("http:///localhost/file1.txt")
        request.retries_left = 1
        http_request.return_value = request
        response_mock = mock.MagicMock(code=501, msg="not found")
        response_mock.getcode.return_value = response_mock.code
        http_open.return_value = response_mock
        manager = connections.ConnectionsManager(retries_num=2)
        with self.assertRaises(connections.urlerror.HTTPError) as trapper:
            manager.open_stream("http:///localhost/file1.txt")
        self.assertEqual(501, trapper.exception.code)
        self.assertEqual(2, http_request.call_count)
        for retry_num in six.moves.range(1):
            logger.error.assert_any_call(
                "request failed: %s - %d(%s), retries left - %d.",
                mock.ANY, 501, mock.ANY, retry_num
            )

    @mock.patch("packetary.library.connections.urllib.build_opener")
    def test_raise_other_errors(self, *_):
        manager = connections.ConnectionsManager()
        manager.opener.open.side_effect = \
            connections.urlerror.HTTPError("", 500, "", {}, None)

        with self.assertRaises(connections.urlerror.URLError):
            manager.open_stream("/test/file")

        self.assertEqual(1, manager.opener.open.call_count)

    @mock.patch("packetary.library.connections.urllib.build_opener")
    @mock.patch("packetary.library.connections.time")
    def test_progressive_delay_between_request(self, time_mock, *_):
        manager = connections.ConnectionsManager(
            retries_num=6, retry_interval=1
        )
        manager.opener.open.side_effect = IOError("I/O Error")

        with self.assertRaises(IOError):
            manager.open_stream("/test/file")

        self.assertEqual(7, manager.opener.open.call_count)
        self.assertEqual(
            [1, 1, 2, 3, 4, 5],
            [x[0][0] for x in time_mock.sleep.call_args_list]
        )

    @mock.patch("packetary.library.connections.urllib.build_opener")
    @mock.patch("packetary.library.connections.ensure_dir_exist")
    @mock.patch("packetary.library.connections.os")
    def test_retrieve_from_offset(self, os, *_):
        manager = connections.ConnectionsManager()
        os.stat.return_value = mock.MagicMock(st_size=10)
        os.open.return_value = 1
        response = mock.MagicMock()
        manager.opener.open.return_value = response
        response.read.side_effect = [b"test", b""]
        manager.retrieve("/file/src", "/file/dst", size=20)
        os.lseek.assert_called_once_with(1, 10, os.SEEK_SET)
        os.ftruncate.assert_called_once_with(1, 10)
        self.assertEqual(1, os.write.call_count)
        os.fsync.assert_called_once_with(1)
        os.close.assert_called_once_with(1)

    @mock.patch("packetary.library.connections.urllib.build_opener")
    @mock.patch("packetary.library.connections.ensure_dir_exist")
    @mock.patch("packetary.library.connections.os")
    def test_retrieve_non_existence(self, os, *_):
        manager = connections.ConnectionsManager()
        os.stat.side_effect = OSError(2, "")
        os.open.return_value = 1
        response = mock.MagicMock()
        manager.opener.open.return_value = response
        response.read.side_effect = [b"test", b""]
        manager.retrieve("/file/src", "/file/dst", size=20)
        os.lseek.assert_called_once_with(1, 0, os.SEEK_SET)
        os.ftruncate.assert_called_once_with(1, 0)
        self.assertEqual(1, os.write.call_count)
        os.fsync.assert_called_once_with(1)
        os.close.assert_called_once_with(1)

    @mock.patch("packetary.library.connections.urllib.build_opener",
                new=mock.MagicMock())
    @mock.patch("packetary.library.connections.ensure_dir_exist",
                new=mock.MagicMock())
    @mock.patch("packetary.library.connections.os")
    def test_retrieve_from_offset_fail(self, os, logger):
        manager = connections.ConnectionsManager(retries_num=2)
        os.stat.return_value = mock.MagicMock(st_size=10)
        os.open.return_value = 1
        response = mock.MagicMock()
        manager.opener.open.side_effect = [
            connections.RangeError("error"), response
        ]
        response.read.side_effect = [b"test", b""]
        manager.retrieve("/file/src", "/file/dst", size=20)
        logger.warning.assert_called_once_with(
            "Failed to resume download, starts from the beginning: %s",
            "/file/src"
        )
        os.lseek.assert_called_once_with(1, 0, os.SEEK_SET)
        os.ftruncate.assert_called_once_with(1, 0)
        self.assertEqual(1, os.write.call_count)
        os.fsync.assert_called_once_with(1)
        os.close.assert_called_once_with(1)


@mock.patch("packetary.library.connections.logger")
class TestRetryHandler(base.TestCase):
    def setUp(self):
        super(TestRetryHandler, self).setUp()
        self.handler = connections.RetryHandler()
        self.handler.add_parent(mock.MagicMock())

    def test_start_request(self, logger):
        request = mock.MagicMock()
        request.offset = 0
        request.get_full_url.return_value = "/file/test"
        request = self.handler.http_request(request)
        request.start_time <= time.time()
        logger.debug.assert_called_with("start request: %s", "/file/test")
        request.offset = 1
        request = self.handler.http_request(request)
        request.add_header.assert_called_once_with('Range', 'bytes=1-')

    def test_handle_response(self, logger):
        request = mock.MagicMock()
        request.offset = 0
        request.start_time.__rsub__.return_value = 0.01
        request.get_full_url.return_value = "/file/test"
        response = mock.MagicMock()
        response.getcode.return_value = 200
        response.msg = "test"
        r = self.handler.http_response(request, response)
        self.assertIsInstance(r, connections.ResumableResponse)
        logger.debug.assert_called_with(
            "request completed: %s - %d (%s), duration - %d ms.",
            "/file/test", 200, "test", 10
        )

    def test_handle_partial_response(self, _):
        request = mock.MagicMock()
        request.offset = 1
        request.get_full_url.return_value = "/file/test"
        response = mock.MagicMock()
        response.getcode.return_value = 200
        response.msg = "test"
        with self.assertRaises(connections.RangeError):
            self.handler.http_response(request, response)
        response.getcode.return_value = 206
        self.handler.http_response(request, response)

    def test_handle_error(self, logger):
        request = mock.MagicMock(retries_left=1, retry_interval=0, offset=0)
        request.get_retry_interval.return_value = 0
        request.get_full_url.return_value = "/test"
        response_mock = mock.MagicMock(code=500, msg="error")
        response_mock.getcode.return_value = response_mock.code
        self.handler.http_response(request, response_mock)
        logger.error.assert_called_with(
            "request failed: %s - %d(%s), retries left - %d.",
            "/test", 500, "error", 0
        )
        self.handler.http_response(request, response_mock)
        self.handler.parent.open.assert_called_once_with(request)


class TestResumeableResponse(base.TestCase):
    def setUp(self):
        super(TestResumeableResponse, self).setUp()
        self.request = mock.MagicMock()
        self.opener = mock.MagicMock()
        self.stream = mock.MagicMock()

    def test_resume_read(self):
        self.request.offset = 0
        response = connections.ResumableResponse(
            self.request,
            self.stream,
            self.opener
        )
        self.stream.read.side_effect = [
            b"chunk1", IOError(), b"chunk2", b""
        ]
        self.opener.error.return_value = response
        data = response.read()
        self.assertEqual(b"chunk1chunk2", data)
        self.assertEqual(12, self.request.offset)
        self.assertEqual(1, self.opener.error.call_count)

    def test_read(self):
        self.request.offset = 0
        response = connections.ResumableResponse(
            self.request,
            six.BytesIO(b"line1\nline2\nline3\n"),
            self.opener
        )
        self.assertEqual(
            b"line1\nline2\nline3\n", response.read()
        )
