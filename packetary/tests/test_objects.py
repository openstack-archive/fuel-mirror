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

import copy
import six

from packetary.objects import PackageRelation

from packetary.tests import base
from packetary.tests.stubs import generator


class TestPlainObject(base.TestCase):
    def check_copy(self, origin):
        clone = copy.copy(origin)
        self.assertIsNot(origin, clone)
        self.assertEqual(origin, clone)
        origin_name = origin.name
        origin.name += "1"
        self.assertEqual(
            origin_name,
            clone.name
        )

    def check_ordering(self, *args):
        for i in six.moves.range(len(args) - 1, 1, -1):
            self.assertLess(args[i - 1], args[i])
            self.assertGreater(args[i], args[i - 1])

    def check_equal(self, o1, o11, o2):
        self.assertEqual(o1, o11)
        self.assertEqual(o11, o1)
        self.assertNotEqual(o1, o2)
        self.assertNotEqual(o2, o1)
        self.assertNotEqual(o1, None)


class TestPackageObject(TestPlainObject):
    def test_copy(self):
        self.check_copy(generator.gen_package(name="test1"))

    def test_ordering(self):
        self.check_ordering(
            generator.gen_package(name="test1", version=1),
            generator.gen_package(name="test1", version=2),
            generator.gen_package(name="test2", version=1),
            generator.gen_package(name="test2", version=2)
        )

    def test_equal(self):
        self.check_equal(
            generator.gen_package(name="test1", version=1),
            generator.gen_package(name="test1", version=1),
            generator.gen_package(name="test2", version=1)
        )


class TestRepositoryObject(TestPlainObject):
    def test_copy(self):
        self.check_copy(generator.gen_repository())

    def test_ordering(self):
        self.check_ordering(
            generator.gen_repository(name="test1", architecture="i386"),
            generator.gen_repository(name="test1", architecture="x86_64"),
            generator.gen_repository(name="test2", architecture="i386"),
            generator.gen_repository(name="test2", architecture="x86_64")
        )

    def test_equal(self):
        self.check_equal(
            generator.gen_repository(name="test1"),
            generator.gen_repository(name="test1"),
            generator.gen_repository(name="test2"),
        )


class TestRelationObject(TestPlainObject):
    def test_copy(self):
        self.check_copy(generator.gen_relation()[0])

    def test_ordering(self):
        self.check_ordering(
            generator.gen_relation("test1", ["eq", 1])[0],
            generator.gen_relation("test1", ["eq", 2])[0],
            generator.gen_relation("test2", ["le", 1])[0],
            generator.gen_relation("test2", ["le", 2])[0]
        )

    def test_equal(self):
        self.check_equal(
            generator.gen_relation(name="test1"),
            generator.gen_relation(name="test1"),
            generator.gen_relation(name="test2"),
        )

    def test_construct(self):
        r = PackageRelation(["test", "le", 2, "test2", "ge", 3])
        self.assertEqual("test", r.name)
        self.assertEqual("le", r.version.op)
        self.assertEqual(2, r.version.edge)
        self.assertEqual("test2", r.alternative.name)
        self.assertEqual("ge", r.alternative.version.op)
        self.assertEqual(3, r.alternative.version.edge)
        self.assertIsNone(r.alternative.alternative)

    def test_iter(self):
        it = iter(PackageRelation(["test", "le", 2, "test2", "ge", 3]))
        self.assertEqual("test", next(it).name)
        self.assertEqual("test2", next(it).name)
        with self.assertRaises(StopIteration):
            next(it)
