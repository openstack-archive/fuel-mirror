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
import tempfile

from fuel_createmirror.services import curl
from fuel_createmirror.services import rsync

from .location import Location


__all__ = ("probe",)


logger = logging.getLogger(__package__)


def probe(url_components):
    """Tries to open location."""
    if not url_components.scheme.startswith('http'):
        return None

    baseurl = _get_rsync_url(url_components.netloc, url_components.path)
    if not baseurl.endswith('/'):
        baseurl += '/'
    if rsync.exists(baseurl):
        return HTTPLocation(rsync, baseurl=baseurl)

    baseurl = _get_http_url(
        url_components.scheme, url_components.netloc, url_components.path
    )
    if curl.exists(baseurl):
        return HTTPLocation(curl, baseurl=baseurl)


def _get_rsync_url(netloc, path):
    """Gets the url in rsync format."""
    if path.startswith('/'):
        path = path[1:]
    if not path.endswith('/'):
        path += '/'
    return '::'.join((netloc, path))


def _get_http_url(scheme, netloc, path):
    """Gets the http url."""
    if path.endswith("/"):
        path = path[:-1]

    return "{0}://{1}{2}/".format(
        scheme, netloc, path
    )


class HTTPLocation(Location):
    def __init__(self, service, baseurl):
        self.service = service
        self.baseurl = baseurl

    def exists(self, path):
        return self.service.exists(self._get_url(path))

    def fetch(self, src, dst, sha1=None, size=None, **kwargs):
        return self.service.copy(
            self._get_url(src), dst, sha1=sha1, size=size, **kwargs
        )

    def open(self, path, mode):
        fd, name = tempfile.mkstemp()
        os.close(fd)
        try:
            logger.debug("open: %s", name)
            self.fetch(path, name, dry_run=False)
            return open(name, mode)
        finally:
            os.unlink(name)

    def _get_url(self, path):
        if path.startswith("/"):
            path = path[1:]
        return self.baseurl + path
