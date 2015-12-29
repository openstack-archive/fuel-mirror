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

import functools
import hashlib


class _HashComposite(object):
    """Combines several hash methods."""

    def __init__(self, hash_objects):
        self.hash_objects = hash_objects

    def update(self, data):
        """Updates the hash objects with the string arg.

        For more details see doc of hashlib.update.
        """
        for o in self.hash_objects:
            o.update(data)

    def hexdigest(self):
        """Returns the list of appropriate hexdigests of hash_objects.

        For more details see doc of hashlib.hexdigest.
        """
        return [o.hexdigest() for o in self.hash_objects]


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
