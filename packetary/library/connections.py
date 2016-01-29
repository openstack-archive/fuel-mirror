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
    max_delay = 5
    offset = 0
    retries_left = 1
    retries_delay = 0
    start_time = 0

    def can_retry(self):
        """Checks that retry can be retried.

        :return: True if retryable, otherwise False
        """
        if self.retries_left > 0:
            coef = max(self.max_delay - self.retries_left, 1)
            timeout = self.retries_delay * coef
            time.sleep(min(timeout, self.max_delay))
            self.retries_left -= 1
            return True
            # pass response to next handler as is.
        return False


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
        """Initialises http request.

        :param request: the instance of RetryableRequest
        :return: the request
        """
        logger.debug("start request: %s", request.get_full_url())
        if request.offset > 0:
            request.add_header('Range', 'bytes=%d-' % request.offset)
        request.start_time = time.time()
        return request

    def http_response(self, request, response):
        """Wraps response in a ResumableResponse.

        Checks that partial request completed successfully.
        :param request: the instance of RetryableRequest
        :param response: the response object
        :return: ResumableResponse if success otherwise same response
        """
        code, msg = response.getcode(), response.msg
        # the server should response partial content if range is specified
        if request.offset > 0 and code != 206:
            raise RangeError(msg)

        if code >= 400:
            logger.error(
                "request failed: %s - %d(%s), retries left - %d.",
                request.get_full_url(), code, msg, request.retries_left
            )
            if is_retryable_http_error(code) and request.can_retry():
                response = self.parent.open(request)
            # pass response to next handler as is.
            return response

        logger.debug(
            "request completed: %s - %d (%s), duration - %d ms.",
            request.get_full_url(), response.getcode(), response.msg,
            int((time.time() - request.start_time) * 1000)
        )

        return ResumableResponse(request, response, self.parent)

    https_request = http_request
    https_response = http_response


def is_retryable_http_error(code):
    """Checks that http error can be retried.

    :param code: the HTTP_CODE
    :return: True if request can be retried otherwise False
    """
    return code == http_client.NOT_FOUND or \
        code >= http_client.INTERNAL_SERVER_ERROR


class ConnectionsManager(object):
    """The connections manager."""

    def __init__(self, proxy=None, secure_proxy=None,
                 retries_num=0, retries_delay=0):
        """Initialises.

        :param proxy: the url of proxy for http-connections
        :param secure_proxy: the url of proxy for https-connections
        :param retries_num: the number of allowed retries
        :param retries_delay: the timeout between retries (in seconds)
        """
        if proxy:
            proxies = {
                "http": proxy,
                "https": secure_proxy or proxy,
            }
        else:
            proxies = None

        self.retries_num = retries_num
        self.retries_delay = retries_delay
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
        request.retries_delay = self.retries_delay
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
                if not request.can_retry():
                    raise
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
