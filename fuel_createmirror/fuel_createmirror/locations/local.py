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

from __future__ import print_function

import gzip
import os

from fuel_createmirror.options import options


class _FakeGzip(object):
    def __init__(self, path):
        if path.endswith(".gz"):
            self.path = path[:-3]
        else:
            self.path = path

    def write(self, p):
        print("echo ", p.join(("'", "'")), ">>", self.path)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            print("gzip", self.path)
        return False


join_path = os.path.join

exists = os.path.exists


def mkdir(base, *args, **kwargs):
    """Creates directory recursively."""
    path = os.path.join(base, *args)
    dry_run = kwargs.pop("dry_run", options.globals.dry_run)
    if dry_run:
        print("mkdir -p", path)
    elif not os.path.exists(path):
        os.makedirs(path)
    return path


def create_gzip(filename, **kwargs):
    """Creates gzipped file."""
    dry_run = kwargs.pop("dry_run", options.globals.dry_run)
    if dry_run:
        return _FakeGzip(filename)
    return gzip.open(filename, "wb")


def open_gzip(filename):
    """Opens gzipped file."""
    return gzip.open(filename, "rb")


def rename(path1, path2, **kwargs):
    """Renames file."""
    dry_run = kwargs.pop("dry_run", options.globals.dry_run)
    if dry_run:
        print("mv -f", path1, path2)
    else:
        os.rename(path1, path2)
