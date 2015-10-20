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
