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

import gzip
import six

from packetary.library import streams
from packetary.tests import base


class TestBufferedStream(base.TestCase):
    def setUp(self):
        super(TestBufferedStream, self).setUp()
        self.stream = streams.BufferedStream(
            six.BytesIO(b"line1\nline2\nline3\n")
        )

    def test_read(self):
        self.stream.CHUNK_SIZE = 10
        chunk = self.stream.read(5)
        self.assertEqual(b"line1", chunk)
        self.assertEqual(b"\nline", self.stream.buffer)
        chunk = self.stream.read(1024)
        self.assertEqual(b"\nline2\nline3\n", chunk)
        self.assertEqual(b"", self.stream.buffer)

    def test_readline(self):
        self.stream.CHUNK_SIZE = 12
        chunk = self.stream.readline()
        self.assertEqual(b"line1\n", chunk)
        self.assertEqual(b"line2\n", self.stream.buffer)
        lines = list(self.stream.readlines())
        self.assertEqual([b"line2\n", b"line3\n"], lines)
        self.assertEqual(b"", self.stream.buffer)

    def test_readlines(self):
        self.stream.CHUNK_SIZE = 12
        lines = list(self.stream.readlines())
        self.assertEqual(
            [b"line1\n", b"line2\n", b"line3\n"],
            lines
        )


class TestGzipDecompress(base.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gzipped = six.BytesIO()
        gz = gzip.GzipFile(fileobj=cls.gzipped, mode="w")
        gz.write(b"line1\nline2\nline3\n")
        gz.flush()
        gz.close()

    def setUp(self):
        super(TestGzipDecompress, self).setUp()
        self.gzipped.seek(0)
        self.stream = streams.GzipDecompress(self.gzipped)

    def test_read(self):
        chunk = self.stream.read(5)
        self.assertEqual(b"line1", chunk)
        self.assertEqual(b"\nline2\nline3\n", self.stream.buffer)
        chunk = self.stream.read(1024)
        self.assertEqual(b"\nline2\nline3\n", chunk)
        self.assertEqual(b"", self.stream.buffer)

    def test_readline(self):
        self.stream.CHUNK_SIZE = 12
        chunk = self.stream.readline()
        self.assertEqual(b"line1\n", chunk)
        self.assertEqual(b"line2\nline3\n", self.stream.buffer)
        lines = list(self.stream.readlines())
        self.assertEqual([b"line2\n", b"line3\n"], lines)
        self.assertEqual(b"", self.stream.buffer)

    def test_readlines(self):
        self.stream.CHUNK_SIZE = 12
        lines = list(self.stream.readlines())
        self.assertEqual(
            [b"line1\n", b"line2\n", b"line3\n"],
            lines
        )
