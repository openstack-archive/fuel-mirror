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

import functools
import hashlib


class _HashComposite(object):
    """Combines several hash methods."""

    def __init__(self, methods):
        self.methods = methods

    def update(self, data):
        for m in self.methods:
            m.update(data)

    def hexdigest(self):
        return [m.hexdigest() for m in self.methods]


def _new_composite(methods):
    """Creates new composite method."""

    def wrapper():
        return _HashComposite([x() for x in methods])
    return wrapper


def _checksum(method):
    """Makes function to calculate checksum for stream."""
    @functools.wraps(method)
    def calculate(stream, chunksize=16 * 1024):
        """Calculates checksum for binary stream.

        :param stream: file-like object opened in binary mode.
        :return: the checksum of content in terms of method.
        """

        s = method()
        while True:
            chunk = stream.read(chunksize)
            if not chunk:
                break
            s.update(chunk)
        return s.hexdigest()
    return calculate


md5 = _checksum(hashlib.md5)

sha1 = _checksum(hashlib.sha1)

sha256 = _checksum(hashlib.sha256)


def composite(*methods):
    """Calculate several checksum at one time."""
    return _checksum(_new_composite(
        [getattr(hashlib, x) for x in methods]
    ))
