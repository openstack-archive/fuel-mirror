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

from packetary.library import streams
from packetary.tests import base
from packetary.tests.stubs.helpers import get_compressed


class TestBufferedStream(base.TestCase):
    def setUp(self):
        super(TestBufferedStream, self).setUp()
        self.stream = streams.StreamWrapper(
            six.BytesIO(b"line1\nline2\nline3\n")
        )

    def test_read(self):
        self.stream.CHUNK_SIZE = 10
        chunk = self.stream.read(5)
        self.assertEqual(b"line1", chunk)
        self.assertEqual(b"\nline", self.stream.unread_tail)
        chunk = self.stream.read(1024)
        self.assertEqual(b"\nline2\nline3\n", chunk)
        self.assertEqual(b"", self.stream.unread_tail)

    def test_readline(self):
        self.stream.CHUNK_SIZE = 12
        chunk = self.stream.readline()
        self.assertEqual(b"line1\n", chunk)
        self.assertEqual(b"line2\n", self.stream.unread_tail)
        lines = list(self.stream.readlines())
        self.assertEqual([b"line2\n", b"line3\n"], lines)
        self.assertEqual(b"", self.stream.unread_tail)

    def test_readlines(self):
        self.stream.CHUNK_SIZE = 12
        lines = list(self.stream.readlines())
        self.assertEqual(
            [b"line1\n", b"line2\n", b"line3\n"],
            lines)


class TestGzipDecompress(base.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.compressed = get_compressed(six.BytesIO(b"line1\nline2\nline3\n"))

    def setUp(self):
        super(TestGzipDecompress, self).setUp()
        self.compressed.reset()
        self.stream = streams.GzipDecompress(self.compressed)

    def test_read(self):
        chunk = self.stream.read(5)
        self.assertEqual(b"line1", chunk)
        self.assertEqual(b"\nline2\nline3\n", self.stream.unread_tail)
        chunk = self.stream.read(1024)
        self.assertEqual(b"\nline2\nline3\n", chunk)
        self.assertEqual(b"", self.stream.unread_tail)

    def test_readline(self):
        self.stream.CHUNK_SIZE = 12
        chunk = self.stream.readline()
        self.assertEqual(b"line1\n", chunk)
        self.assertEqual(b"line2\nl", self.stream.unread_tail)
        lines = list(self.stream.readlines())
        self.assertEqual([b"line2\n", b"line3\n"], lines)
        self.assertEqual(b"", self.stream.unread_tail)

    def test_readlines(self):
        self.stream.CHUNK_SIZE = 12
        lines = list(self.stream.readlines())
        self.assertEqual(
            [b"line1\n", b"line2\n", b"line3\n"],
            lines)

    def test_handle_case_if_not_enough_data_to_decompress(self):
        self.stream.CHUNK_SIZE = 1
        chunk = self.stream.read()
        self.assertEqual(
            b"line1\nline2\nline3\n",
            chunk
        )
