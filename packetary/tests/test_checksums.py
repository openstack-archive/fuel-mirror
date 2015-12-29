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

import six

from packetary.library import checksum
from packetary.tests import base


class TestChecksum(base.TestCase):
    def test_checksum(self):
        stream = six.BytesIO(b"line1\nline2\nline3\n")
        checksums = {
            checksum.md5: "cc3d5ed5fda53dfa81ea6aa951d7e1fe",
            checksum.sha1: "8c84f6f36dd2230d3e9c954fa436e5fda90b1957",
            checksum.sha256: "66663af9c7aa341431a8ee2ff27b72"
                             "abd06c9218f517bb6fef948e4803c19e03"
        }
        for chunksize in (8, 256):
            for algo, expected in six.iteritems(checksums):
                stream.seek(0)
                self.assertEqual(
                    expected, algo(stream, chunksize)
                )

    def test_composite(self):
        stream = six.BytesIO(b"line1\nline2\nline3\n")
        result = checksum.composite('md5', 'sha1', 'sha256')(stream)
        self.assertEqual(
            [
                "cc3d5ed5fda53dfa81ea6aa951d7e1fe",
                "8c84f6f36dd2230d3e9c954fa436e5fda90b1957",
                "66663af9c7aa341431a8ee2ff27b72"
                "abd06c9218f517bb6fef948e4803c19e03"
            ],
            result
        )
