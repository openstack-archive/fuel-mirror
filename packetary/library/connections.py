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

import logging
import os
import six
import six.moves.http_client as http_client
import six.moves.urllib.request as urllib_request
import six.moves.urllib_error as urllib_error
import time

from packetary.library.streams import StreamWrapper


logger = logging.getLogger(__package__)


RETRYABLE_ERRORS = (http_client.HTTPException, IOError)


class RangeError(urllib_error.URLError):
    pass


class RetryableRequest(urllib_request.Request):
    offset = 0
    retries_left = 1
    start_time = 0


class ResumableResponse(StreamWrapper):
    """The http-response wrapper to add resume ability.

    Allows to resume read from same position if connection is lost.
    """

    def __init__(self, request, response, opener):
        """Initialises.

        :param request: the original http request
        :param response: the original http response
        :param opener: the instance of urllib.OpenerDirector
        """
        super(ResumableResponse, self).__init__(response)
        self.request = request
        self.opener = opener

    def read_chunk(self, chunksize):
        """Overrides super class method."""
        while 1:
            try:
                chunk = self.stream.read(chunksize)
                self.request.offset += len(chunk)
                return chunk
            except RETRYABLE_ERRORS as e:
                response = self.opener.error(
                    self.request.get_type(), self.request,
                    self.stream, 502, six.text_type(e), self.stream.info()
                )
                self.stream = response.stream


class RetryHandler(urllib_request.BaseHandler):
    """urllib Handler to add ability for retrying on server errors."""

    @staticmethod
    def http_request(request):
        """Initialises http request."""
        logger.debug("start request: %s", request.get_full_url())
        if request.offset > 0:
            request.add_header('Range', 'bytes=%d-' % request.offset)
        request.start_time = time.time()
        return request

    def http_response(self, request, response):
        """Wraps response in a ResumableResponse.

        Checks that partial request completed successfully.
        """
        # the server should response partial content if range is specified
        logger.debug(
            "finish request: %s - %d (%s), duration - %d ms.",
            request.get_full_url(), response.getcode(), response.msg,
            int((time.time() - request.start_time) * 1000)
        )
        if request.offset > 0 and response.getcode() != 206:
            raise RangeError("Server does not support ranges.")
        return ResumableResponse(request, response, self.parent)

    def http_error(self, req, fp, code, msg, hdrs):
        """Checks error code and retries request if it is allowed."""
        if code >= 500 and req.retries_left > 0:
            req.retries_left -= 1
            logger.warning(
                "fail request: %s - %d(%s), retries left - %d.",
                req.get_full_url(), code, msg, req.retries_left
            )
            return self.parent.open(req)

    https_request = http_request
    https_response = http_response


class Connection(object):
    """Helper class to deal with streams."""

    def __init__(self, opener, retries_num):
        """Initializes.

        :param opener: the instance of urllib.OpenerDirector
        :param retries_num: the number of allowed retries
        """
        self.opener = opener
        self.retries_num = retries_num

    def make_request(self, url, offset=0):
        """Makes new http request.

        :param url: the remote file`s url
        :param offset: the number of bytes from begin, that will be skipped
        :return: The new http request
        """

        if url.startswith("/"):
            url = "file://" + url

        request = RetryableRequest(url)
        request.retries_left = self.retries_num
        request.offset = offset
        return request

    def open_stream(self, url, offset=0):
        """Opens remote file for streaming.

        :param url: the remote file`s url
        :param offset: the number of bytes from begin, that will be skipped
        """

        request = self.make_request(url, offset)
        while 1:
            try:
                return self.opener.open(request)
            except (RangeError, urllib_error.HTTPError):
                raise
            except RETRYABLE_ERRORS as e:
                if request.retries_left <= 0:
                    raise
                request.retries_left -= 1
                logger.exception(
                    "Failed to open url - %s: %s. retries left - %d.",
                    url, six.text_type(e), request.retries_left
                )

    def retrieve(self, url, filename, offset=0):
        """Downloads remote file.

        :param url: the remote file`s url
        :param filename: the file`s name, that includes path on local fs
        :param offset: the number of bytes from begin, that will be skipped
        """

        self._ensure_dir_exists(filename)
        fd = os.open(filename, os.O_CREAT | os.O_WRONLY)
        try:
            self._copy_stream(fd, url, offset)
        except RangeError:
            if offset == 0:
                raise
            logger.warning(
                "Failed to resume download, starts from begin: %s", url
            )
            self._copy_stream(fd, url, 0)
        finally:
            os.fsync(fd)
            os.close(fd)

    @staticmethod
    def _ensure_dir_exists(dst):
        """Checks that directory exists and creates otherwise."""
        target_dir = os.path.dirname(dst)
        try:
            os.makedirs(target_dir)
        except OSError as e:
            if e.errno != 17:
                raise

    def _copy_stream(self, fd, url, offset):
        """Copies remote file to local.

        :param fd: the file`s descriptor
        :param url: the remote file`s url
        :param offset: the number of bytes from begin, that will be skipped
        """

        source = self.open_stream(url, offset)
        os.ftruncate(fd, offset)
        os.lseek(fd, offset, os.SEEK_SET)
        chunk_size = 16 * 1024
        while 1:
            chunk = source.read(chunk_size)
            if not chunk:
                break
            os.write(fd, chunk)


class ConnectionContext(object):
    """Helper class acquire and release connection within context."""
    def __init__(self, connection, on_exit):
        self.connection = connection
        self.on_exit = on_exit

    def __enter__(self):
        return self.connection

    def __exit__(self, *_):
        self.on_exit(self.connection)


class ConnectionsPool(object):
    """Controls the number of simultaneously opened connections."""

    MIN_CONNECTIONS_COUNT = 1

    def __init__(self, count=0, proxy=None, secure_proxy=None, retries_num=0):
        """Initialises.

        :param count: the number of allowed simultaneously connections
        :param proxy: the url of proxy for http-connections
        :param secure_proxy: the url of proxy for https-connections
        :param retries_num: the number of allowed retries
        """
        if proxy:
            proxies = {
                "http": proxy,
                "https": secure_proxy or proxy,
            }
        else:
            proxies = None

        opener = urllib_request.build_opener(
            RetryHandler(),
            urllib_request.ProxyHandler(proxies)
        )

        limit = max(count, self.MIN_CONNECTIONS_COUNT)
        connections = six.moves.queue.Queue()
        while limit > 0:
            connections.put(Connection(opener, retries_num))
            limit -= 1

        self.free = connections

    def get(self, timeout=None):
        """Gets the free connection.

        Blocks in case if there is no free connections.

        :param timeout: the timeout in seconds to wait.
            by default infinity waiting.
        """
        return ConnectionContext(
            self.free.get(timeout=timeout), self._release
        )

    def _release(self, connection):
        """Puts back connection to free connections."""
        self.free.put(connection)
