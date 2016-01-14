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

import zlib


class StreamWrapper(object):
    """Helper class to implement stream wrappers.

    It is base-class for Streamers,
    that provides functionality to transform stream on the fly.
    The wrapped stream may return data more that required,
    the extra read data will be kept in the internal buffer till
    next read.
    """

    CHUNK_SIZE = 1024

    def __init__(self, stream):
        """Initializes.

        :param stream: file-like object opened in binary mode.
        """
        self.stream = stream
        self.unread_tail = b""

    def __getattr__(self, item):
        return getattr(self.stream, item)

    def _read_tail(self):
        tmp = self.unread_tail
        self.unread_tail = b""
        return tmp

    def _align_chunk(self, chunk, size):
        self.unread_tail = chunk[size:]
        return chunk[:size]

    def read_chunk(self, chunksize):
        """Overrides this method to change default behaviour."""
        return self.stream.read(chunksize)

    def read(self, size=-1):
        result = self._read_tail()
        if size < 0:
            while True:
                chunk = self.read_chunk(self.CHUNK_SIZE)
                if not chunk:
                    break
                result += chunk
        else:
            if len(result) > size:
                result = self._align_chunk(result, size)
            size -= len(result)
            while size > 0:
                chunk = self.read_chunk(self.CHUNK_SIZE)
                if not chunk:
                    break
                if len(chunk) > size:
                    chunk = self._align_chunk(chunk, size)
                size -= len(chunk)
                result += chunk
        return result

    def readline(self):
        pos = self.unread_tail.find(b"\n")
        if pos >= 0:
            line = self._align_chunk(self.unread_tail, pos + 1)
        else:
            line = self._read_tail()
            while True:
                chunk = self.read_chunk(self.CHUNK_SIZE)
                if not chunk:
                    break
                pos = chunk.find(b"\n")
                if pos >= 0:
                    line += self._align_chunk(chunk, pos + 1)
                    break
                line += chunk
        return line

    def readlines(self):
        while True:
            line = self.readline()
            if not line:
                break
            yield line

    def __iter__(self):
        return self.readlines()


class GzipDecompress(StreamWrapper):
    """The decompress stream."""

    def __init__(self, stream):
        super(GzipDecompress, self).__init__(stream)
        # Magic parameter makes zlib module understand gzip header
        # http://stackoverflow.com/questions/1838699/how-can-i-decompress-a-gzip-stream-with-zlib
        # This works on cpython and pypy, but not jython.
        self.decompress = zlib.decompressobj(16 + zlib.MAX_WBITS)

    def read_chunk(self, chunksize):
        if self.decompress.unconsumed_tail:
            uncompressed = self.decompress.decompress(
                self.decompress.unconsumed_tail, chunksize
            )
            if uncompressed:
                return uncompressed

        while True:
            chunk = self.stream.read(chunksize)
            if not chunk:
                break
            uncompressed = self.decompress.decompress(chunk, chunksize)
            if uncompressed:
                return uncompressed
        return self.decompress.flush()
