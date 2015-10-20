# -*- coding: utf-8 -*-

#    Copyright 2015 Mirantis, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import mock
import six
import time

from packetary.library import connections
from packetary.tests import base


class TestConnectionsPool(base.TestCase):
    def test_get_connection(self):
        pool = connections.ConnectionsPool({"connection_count": 2})
        self.assertEqual(2, pool.free.qsize())
        with pool.get():
            self.assertEqual(1, pool.free.qsize())
        self.assertEqual(2, pool.free.qsize())

    def test_set_proxy(self):
        pool = connections.ConnectionsPool({
            "connection_count": 1,
            "connection_proxy": "http://10.250.1.1",
        })
        with pool.get() as c:
            for h in c.opener.handlers:
                if isinstance(h, connections.urllib_request.ProxyHandler):
                    self.assertEqual(
                        "http://10.250.1.1", h.proxies["http"]
                    )
                    break
            else:
                self.fail("ProxyHandler should be in list of handlers.")

    def test_reliability(self):
        pool = connections.ConnectionsPool({
            "connection_count": 0,
            "retries_count": 2
        })
        self.assertEqual(1, pool.free.qsize())
        with pool.get() as c:
            self.assertEqual(2, c.retries_num)
            for h in c.opener.handlers:
                if isinstance(h, connections.RetryHandler):
                    break
            else:
                self.fail("RetryHandler should be in list of handlers.")


class TestConnection(base.TestCase):
    def setUp(self):
        super(TestConnection, self).setUp()
        self.connection = connections.Connection(mock.MagicMock(), 2)

    def test_get_request(self):
        request = self.connection.get_request("/test/file", 0)
        self.assertIsInstance(request, connections.RetryableRequest)
        self.assertEqual("file:///test/file", request.get_full_url())
        self.assertEqual(0, request.offset)
        self.assertEqual(2, request.retries_left)
        request2 = self.connection.get_request("http://server/path", 100)
        self.assertEqual("http://server/path", request2.get_full_url())
        self.assertEqual(100, request2.offset)

    def test_open_stream(self):
        self.connection.open_stream("/test/file")
        self.assertEqual(1, self.connection.opener.open.call_count)
        args = self.connection.opener.open.call_args[0]
        self.assertIsInstance(args[0], connections.RetryableRequest)
        self.assertEqual(2, args[0].retries_left)

    @mock.patch("packetary.library.connections.logger")
    def test_retries_on_io_error(self, logger):
        self.connection.opener.open.side_effect = [
            IOError("I/O error"),
            mock.MagicMock()
        ]
        self.connection.open_stream("/test/file")
        self.assertEqual(2, self.connection.opener.open.call_count)
        logger.exception.assert_called_with(
            "Failed to open url: %s. retries left - %d.",
            "I/O error", 1
        )

        self.connection.opener.open.side_effect = IOError("I/O error")
        with self.assertRaises(IOError):
            self.connection.open_stream("/test/file")
        logger.exception.assert_called_with(
            "Failed to open url: %s. retries left - %d.",
            "I/O error", 0
        )

    def test_raise_other_errors(self):
        self.connection.opener.open.side_effect = \
            connections.urllib_error.HTTPError("", 500, "", {}, None)

        with self.assertRaises(connections.urllib_error.URLError):
            self.connection.open_stream("/test/file")

        self.assertEqual(1, self.connection.opener.open.call_count)

    @mock.patch("packetary.library.connections.os")
    def test_retrieve_from_offset(self, os):
        os.path.mkdirs.side_effect = OSError(17, "")
        os.open.return_value = 1
        response = mock.MagicMock()
        self.connection.opener.open.return_value = response
        response.read.side_effect = [b"test", b""]
        self.connection.retrieve("/file/src", "/file/dst", 10)
        os.lseek.assert_called_once_with(1, 10, os.SEEK_SET)
        os.ftruncate.assert_called_once_with(1, 10)
        self.assertEqual(1, os.write.call_count)
        os.fsync.assert_called_once_with(1)
        os.close.assert_called_once_with(1)

    @mock.patch.multiple(
        "packetary.library.connections",
        logger=mock.DEFAULT,
        os=mock.DEFAULT
    )
    def test_retrieve_from_offset_fail(self, os, logger):
        os.path.mkdirs.side_effect = OSError(17, "")
        os.open.return_value = 1
        response = mock.MagicMock()
        self.connection.opener.open.side_effect = [
            connections.RangeError("error"), response
        ]
        response.read.side_effect = [b"test", b""]
        self.connection.retrieve("/file/src", "/file/dst", 10)
        logger.warning.assert_called_once_with(
            "Failed to resume download, starts from begin: %s",
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
        self.assertIsInstance(r, connections.ResumeableStream)
        logger.debug.assert_called_with(
            "finish request: %s - %d (%s), duration - %d ms.",
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

    def test_error(self, logger):
        request = mock.MagicMock()
        request.get_full_url.return_value = "/test"
        request.retries_left = 1
        self.handler.http_error(
            request, mock.MagicMock(), 500, "error", mock.MagicMock()
        )
        logger.warning.assert_called_with(
            "fail request: %s - %d(%s), retries left - %d.",
            "/test", 500, "error", 0
        )
        self.handler.http_error(
            request, mock.MagicMock(), 500, "error", mock.MagicMock()
        )
        self.handler.parent.open.assert_called_once_with(request)


class TestResumeableResponse(base.TestCase):
    def setUp(self):
        super(TestResumeableResponse, self).setUp()
        self.request = mock.MagicMock()
        self.opener = mock.MagicMock()
        self.stream = mock.MagicMock()

    def test_resume_read(self):
        self.request.offset = 0
        response = connections.ResumeableStream(
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
        response = connections.ResumeableStream(
            self.request,
            six.BytesIO(b"line1\nline2\nline3\n"),
            self.opener
        )
        self.assertEqual(
            b"line1\nline2\nline3\n", response.read()
        )
