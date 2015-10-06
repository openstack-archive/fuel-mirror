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

import os

from fuel_createmirror.repositories import deb


DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


class LocationStub(object):
    @staticmethod
    def open(path, mode):
        return open(os.path.join(DATA_DIR, os.path.basename(path)), mode)


def test_repositories_deb():
    repo = deb.Repository(LocationStub, "main", "amd64")
    packages = list(repo.get_packages())
    assert ["package1", "package2"] == sorted((x.name for x in packages))
    resolved = set()
    unresolved = set()
    for p in packages:
        repo.resolve_depends(p.depends, resolved, unresolved)

    assert 1 == len(resolved)
    assert "package2" == next(iter(resolved)).name
    assert 1 == len(unresolved)
    assert "package3" == next(iter(unresolved)).name
