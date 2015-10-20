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

from packetary.library.index import Index

from packetary.tests import base
from packetary.tests.stubs.package import Package
from packetary.tests.stubs.package import Relation
from packetary.tests.stubs.package import VersionRange


class TestIndex(base.TestCase):
    def _get_packages(self, count=1, **kwargs):
        packages = []
        for i in six.moves.range(count):
            requires = [
                Relation("package%d_r" % i, VersionRange())
            ]
            obsoletes = [
                Relation("package%d_o" % i, VersionRange("le", 2))
            ]
            provides = [
                Relation("package%d_p" % i, VersionRange("gt", 1))
            ]
            packages.append(Package(
                name="package%d" % i,
                requires=requires,
                obsoletes=obsoletes,
                provides=provides,
                **kwargs
            ))

        return packages

    def test_add(self):
        index = Index()
        index.add(self._get_packages(version=1)[0])
        self.assertIn("package0", index.packages)
        self.assertIn(1, index.packages["package0"])
        self.assertIn("package0_o", index.obsoletes)
        self.assertIn("package0_p", index.provides)

        index.add(self._get_packages(version=2)[0])
        self.assertEqual(1, len(index.packages))
        self.assertIn(1, index.packages["package0"])
        self.assertIn(2, index.packages["package0"])
        self.assertEqual(1, len(index.obsoletes))
        self.assertEqual(1, len(index.provides))

    def test_find_package(self):
        index = Index()
        p1 = self._get_packages(version=1)[0]
        p2 = self._get_packages(version=2)[0]
        index.add(p1)
        index.add(p2)

        self.assertIs(
            p1, index.find(Relation("package0", VersionRange("eq", 1)))
        )
        self.assertIs(
            p2, index.find(Relation("package0", VersionRange()))
        )
        self.assertIsNone(
            index.find(Relation("package0", VersionRange("gt", 2)))
        )

    def test_find_newest_package(self):
        index = Index()
        p1, p2 = self._get_packages(2, version=2)
        p2.obsoletes.append(Relation(p1.name, VersionRange("lt", p1.version)))
        index.add(p1)
        index.add(p2)

        self.assertIs(
            p1, index.find(Relation(p1.name, VersionRange("eq", p1.version)))
        )
        self.assertIs(
            p2, index.find(Relation(p1.name, VersionRange("eq", 1)))
        )

    def test_find_obsolete(self):
        index = Index()
        p1 = self._get_packages(version=1)[0]
        p2 = self._get_packages(version=2)[0]
        index.add(p1)
        index.add(p2)

        self.assertIs(
            p2, index.find(Relation("package0_o", VersionRange("eq", 1)))
        )
        self.assertIsNone(
            index.find(Relation("package0_o", VersionRange("gt", 2)))
        )

    def test_find_provides(self):
        index = Index()
        p1 = self._get_packages(version=1)[0]
        p2 = self._get_packages(version=2)[0]
        index.add(p1)
        index.add(p2)

        self.assertIs(
            p2, index.find(Relation("package0_p", VersionRange("eq", 2)))
        )
        self.assertIsNone(
            index.find(Relation("package0_p", VersionRange("lt", 1)))
        )

    def test_len(self):
        index = Index()
        for p in self._get_packages(3, version=1):
            index.add(p)
        self.assertEqual(3, len(index))
        for p in self._get_packages(3, version=2):
            index.add(p)
        self.assertEqual(6, len(index))
        for p in self._get_packages(3, version=2):
            index.add(p)
        self.assertEqual(6, len(index))
