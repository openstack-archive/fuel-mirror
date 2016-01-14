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

import errno
import logging
import os
import six
import six.moves.http_client as http_client
import six.moves.urllib.request as urllib
import six.moves.urllib_error as urlerror
import time

from packetary.library.streams import StreamWrapper
from packetary.library.utils import ensure_dir_exist


logger = logging.getLogger(__package__)


RETRYABLE_ERRORS = (http_client.HTTPException, IOError)


class RangeError(urlerror.URLError):
    pass


class RetryableRequest(urllib.Request):
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
                # TODO(check hashsums)
                response = self.opener.error(
                    self.request.get_type(), self.request,
                    self.stream, 502, six.text_type(e), self.stream.info()
                )
                self.stream = response.stream


class RetryHandler(urllib.BaseHandler):
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
        logger.error(
            "fail request: %s - %d(%s), retries left - %d.",
            req.get_full_url(), code, msg, req.retries_left
        )
        if req.retries_left > 0 and is_retryable_http_error(code):
            req.retries_left -= 1
            return self.parent.open(req)

    https_request = http_request
    https_response = http_response


def is_retryable_http_error(code):
    """Checks that http error can be retried."""
    return code == http_client.NOT_FOUND or \
        code >= http_client.INTERNAL_SERVER_ERROR


class ConnectionsManager(object):
    """The connections manager."""

    def __init__(self, proxy=None, secure_proxy=None, retries_num=0):
        """Initialises.

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

        self.retries_num = retries_num
        self.opener = urllib.build_opener(
            RetryHandler(),
            urllib.ProxyHandler(proxies)
        )

    def make_request(self, url, offset=0):
        """Makes new http request.

        :param url: the remote file`s url
        :param offset: the number of bytes from the beginning,
                       that will be skipped
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
        :param offset: the number of bytes from the beginning,
                       that will be skipped
        """

        request = self.make_request(url, offset)
        while 1:
            try:
                return self.opener.open(request)
            except (RangeError, urlerror.HTTPError):
                raise
            except RETRYABLE_ERRORS as e:
                if request.retries_left <= 0:
                    raise
                request.retries_left -= 1
                logger.exception(
                    "Failed to open url - %s: %s. retries left - %d.",
                    url, six.text_type(e), request.retries_left
                )

    def retrieve(self, url, filename, **attributes):
        """Downloads remote file.

        :param url: the remote file`s url
        :param filename: the target filename on local filesystem
        :param attributes: the file attributes, like size, hashsum, etc.
        :return: the count of actually copied bytes
        """
        offset = 0
        try:
            stats = os.stat(filename)
            expected_size = attributes.get('size', -1)
            if expected_size == stats.st_size:
                # TODO(check hashsum)
                return 0

            if stats.st_size < expected_size:
                offset = stats.st_size
        except OSError as e:
            if e.errno != errno.ENOENT:
                raise
            ensure_dir_exist(os.path.dirname(filename))

        logger.info("download: %s from the offset: %d", url, offset)

        fd = os.open(filename, os.O_CREAT | os.O_WRONLY)
        try:
            return self._copy_stream(fd, url, offset)
        except RangeError:
            if offset == 0:
                raise
            logger.warning(
                "Failed to resume download, starts from the beginning: %s",
                url
            )
            return self._copy_stream(fd, url, 0)
        finally:
            os.fsync(fd)
            os.close(fd)

    def _copy_stream(self, fd, url, offset):
        """Copies remote file to local.

        :param fd: the file`s descriptor
        :param url: the remote file`s url
        :param offset: the number of bytes from the beginning,
                       that will be skipped
        :return: the count of actually copied bytes
        """

        source = self.open_stream(url, offset)
        os.ftruncate(fd, offset)
        os.lseek(fd, offset, os.SEEK_SET)
        chunk_size = 16 * 1024
        size = 0
        while 1:
            chunk = source.read(chunk_size)
            if not chunk:
                break
            os.write(fd, chunk)
            size += len(chunk)
        return size
