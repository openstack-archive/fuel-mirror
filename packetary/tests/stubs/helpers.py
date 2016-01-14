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

from contextlib import closing
import gzip
import mock
import six


class CallbacksAdapter(mock.MagicMock):
    """Helper to return data through callback."""

    def __call__(self, *args, **kwargs):
        if len(args) > 0:
            callback = args[-1]
        else:
            callback = None

        if not callable(callback):
            return super(CallbacksAdapter, self).__call__(*args, **kwargs)

        args = args[:-1]
        data = super(CallbacksAdapter, self).__call__(*args, **kwargs)

        if isinstance(data, list):
            for d in data:
                callback(d)
        else:
            callback(data)


class Buffer(object):
    """Helper to hide BytesIO methods."""

    def __init__(self, io):
        self.io = io
        self.reset()

    def reset(self):
        self.io.seek(0)

    def read(self, s=-1):
        return self.io.read(s)


def get_compressed(stream):
    """Gets compressed stream."""
    compressed = six.BytesIO()
    with closing(gzip.GzipFile(fileobj=compressed, mode="wb")) as gz:
        gz.write(stream.read())
    return Buffer(compressed)
