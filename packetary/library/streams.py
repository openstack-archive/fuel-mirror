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

import zlib


class BufferedStream(object):
    """Stream object."""
    CHUNK_SIZE = 1024

    def __init__(self, fileobj):
        self.fileobj = fileobj
        self.buffer = b""

    def __getattr__(self, item):
        return getattr(self.fileobj, item)

    def _read_buffer(self):
        tmp = self.buffer
        self.buffer = b""
        return tmp

    def _align_chunk(self, chunk, size):
        self.buffer = chunk[size:]
        return chunk[:size]

    def _read(self, chunksize):
        return self.fileobj.read(chunksize)

    def read(self, size=-1):
        result = self._read_buffer()
        if size < 0:
            while True:
                chunk = self._read(self.CHUNK_SIZE)
                if not chunk:
                    break
                result += chunk
        else:
            if len(result) > size:
                result = self._align_chunk(result, size)
            size -= len(result)
            while size > 0:
                chunk = self._read(self.CHUNK_SIZE)
                if not chunk:
                    break
                if len(chunk) > size:
                    chunk = self._align_chunk(chunk, size)
                size -= len(chunk)
                result += chunk
        return result

    def readline(self):
        pos = self.buffer.find(b"\n")
        if pos >= 0:
            line = self._align_chunk(self.buffer, pos + 1)
        else:
            line = self._read_buffer()
            while True:
                chunk = self._read(self.CHUNK_SIZE)
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


class GzipDecompress(BufferedStream):
    """The decompress stream."""

    def __init__(self, fileobj):
        super(GzipDecompress, self).__init__(fileobj)
        # Magic parameter makes zlib module understand gzip header
        # http://stackoverflow.com/questions/1838699/how-can-i-decompress-a-gzip-stream-with-zlib
        # This works on cpython and pypy, but not jython.
        self.decompress = zlib.decompressobj(16 + zlib.MAX_WBITS)

    def _read(self, chunksize):
        chunk = self.fileobj.read(chunksize)
        if not chunk:
            return self.decompress.flush()
        return self.decompress.decompress(chunk)
