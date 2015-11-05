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

from packetary.objects.index import Index

from packetary import objects
from packetary.tests import base
from packetary.tests.stubs.generator import gen_package
from packetary.tests.stubs.generator import gen_relation


class TestIndex(base.TestCase):
    def test_add(self):
        index = Index()
        index.add(gen_package(version=1))
        self.assertIn("package1", index.packages)
        self.assertIn(1, index.packages["package1"])
        self.assertIn("obsoletes1", index.obsoletes)
        self.assertIn("provides1", index.provides)

        index.add(gen_package(version=2))
        self.assertEqual(1, len(index.packages))
        self.assertIn(1, index.packages["package1"])
        self.assertIn(2, index.packages["package1"])
        self.assertEqual(1, len(index.obsoletes))
        self.assertEqual(1, len(index.provides))

    def test_find(self):
        index = Index()
        p1 = gen_package(version=1)
        p2 = gen_package(version=2)
        index.add(p1)
        index.add(p2)

        self.assertIs(
            p1,
            index.find("package1", objects.VersionRange("eq", 1))
        )
        self.assertIs(
            p2,
            index.find("package1", objects.VersionRange())
        )
        self.assertIsNone(
            index.find("package1", objects.VersionRange("gt", 2))
        )

    def test_find_all(self):
        index = Index()
        p11 = gen_package(idx=1, version=1)
        p12 = gen_package(idx=1, version=2)
        p21 = gen_package(idx=2, version=1)
        p22 = gen_package(idx=2, version=2)
        index.add(p11)
        index.add(p12)
        index.add(p21)
        index.add(p22)

        self.assertItemsEqual(
            [p11, p12],
            index.find_all("package1", objects.VersionRange())
        )
        self.assertItemsEqual(
            [p21, p22],
            index.find_all("package2", objects.VersionRange("le", 2))
        )

    def test_find_newest_package(self):
        index = Index()
        p1 = gen_package(idx=1, version=2)
        p2 = gen_package(idx=2, version=2)
        p2.obsoletes.append(
            gen_relation(p1.name, ["lt", p1.version])
        )
        index.add(p1)
        index.add(p2)

        self.assertIs(
            p1, index.find(p1.name, objects.VersionRange("eq", p1.version))
        )
        self.assertIs(
            p2, index.find(p1.name, objects.VersionRange("eq", 1))
        )

    def test_find_top_down(self):
        index = Index()
        p1 = gen_package(version=1)
        p2 = gen_package(version=2)
        index.add(p1)
        index.add(p2)
        self.assertIs(
            p2,
            index.find("package1", objects.VersionRange("le", 2))
        )
        self.assertIs(
            p1,
            index.find("package1", objects.VersionRange("lt", 2))
        )
        self.assertIsNone(
            index.find("package1", objects.VersionRange("lt", 1))
        )

    def test_find_down_up(self):
        index = Index()
        p1 = gen_package(version=1)
        p2 = gen_package(version=2)
        index.add(p1)
        index.add(p2)
        self.assertIs(
            p2,
            index.find("package1", objects.VersionRange("ge", 2))
        )
        self.assertIs(
            p2,
            index.find("package1", objects.VersionRange("gt", 1))
        )
        self.assertIsNone(
            index.find("package1", objects.VersionRange("gt", 2))
        )

    def test_find_accurate(self):
        index = Index()
        p1 = gen_package(version=1)
        p2 = gen_package(version=2)
        index.add(p1)
        index.add(p2)
        self.assertIs(
            p1,
            index.find("package1", objects.VersionRange("eq", 1))
        )
        self.assertIsNone(
            index.find("package1", objects.VersionRange("eq", 3))
        )

    def test_find_obsolete(self):
        index = Index()
        p1 = gen_package(version=1)
        index.add(p1)

        self.assertIs(
            p1, index.find("obsoletes1", objects.VersionRange("le", 2))
        )
        self.assertIsNone(
            index.find("obsoletes1", objects.VersionRange("gt", 2))
        )

    def test_find_provides(self):
        index = Index()
        p1 = gen_package(version=1)
        p2 = gen_package(version=2)
        index.add(p1)
        index.add(p2)

        self.assertIs(
            p2, index.find("provides1", objects.VersionRange("ge", 2))
        )
        self.assertIsNone(
            index.find("provides1", objects.VersionRange("lt", 2))
        )

    def test_len(self):
        index = Index()
        for i in six.moves.range(3):
            index.add(gen_package(idx=i + 1))
        self.assertEqual(3, len(index))

        for i in six.moves.range(3):
            index.add(gen_package(idx=i + 1, version=2))
        self.assertEqual(6, len(index))
        self.assertEqual(3, len(index.packages))

        for i in six.moves.range(3):
            index.add(gen_package(idx=i + 1, version=2))
        self.assertEqual(6, len(index))
        self.assertEqual(3, len(index.packages))
