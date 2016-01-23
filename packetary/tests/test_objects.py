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

import copy
import six

from packetary.objects import PackageRelation
from packetary.objects import PackageVersion
from packetary.objects import VersionRange


from packetary.tests import base
from packetary.tests.stubs import generator


class TestObjectBase(base.TestCase):
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

    def check_hashable(self, o1, o2):
        d = dict()
        d[o1] = o2
        d[o2] = o1

        self.assertIs(o2, d[o1])
        self.assertIs(o1, d[o2])


class TestPackageObject(TestObjectBase):
    def test_copy(self):
        self.check_copy(generator.gen_package(name="test1"))

    def test_ordering(self):
        self.check_ordering([
            generator.gen_package(name="test1", version=1),
            generator.gen_package(name="test1", version=2),
            generator.gen_package(name="test2", version=1),
            generator.gen_package(name="test2", version=2)
        ])

    def test_equal(self):
        self.check_equal(
            generator.gen_package(name="test1", version=1),
            generator.gen_package(name="test1", version=1),
            generator.gen_package(name="test2", version=1)
        )

    def test_hashable(self):
        self.check_hashable(
            generator.gen_package(name="test1", version=1),
            generator.gen_package(name="test2", version=1),
        )
        self.check_hashable(
            generator.gen_package(name="test1", version=1),
            generator.gen_package(name="test1", version=2),
        )


class TestRepositoryObject(base.TestCase):
    def test_copy(self):
        origin = generator.gen_repository()
        clone = copy.copy(origin)
        self.assertEqual(clone.name, origin.name)
        self.assertEqual(clone.architecture, origin.architecture)

    def test_str(self):
        self.assertEqual(
            "a.b",
            str(generator.gen_repository(name=("a", "b")))
        )
        self.assertEqual(
            "/a/b/",
            str(generator.gen_repository(name="", url="/a/b/"))
        )
        self.assertEqual(
            "a",
            str(generator.gen_repository(name="a", url="/a/b/"))
        )


class TestRelationObject(TestObjectBase):
    def test_equal(self):
        self.check_equal(
            generator.gen_relation(name="test1"),
            generator.gen_relation(name="test1"),
            generator.gen_relation(name="test2")
        )

    def test_hashable(self):
        self.check_hashable(
            generator.gen_relation(name="test1"),
            generator.gen_relation(name="test1", version=["le", 1])
        )

    def test_from_args(self):
        r = PackageRelation.from_args(
            ("test", "le", 2), ("test2",), ("test3",)
        )
        self.assertEqual("test", r.name)
        self.assertEqual("le", r.version.op)
        self.assertEqual(2, r.version.edge)
        self.assertEqual("test2", r.alternative.name)
        self.assertEqual(VersionRange(), r.alternative.version)
        self.assertEqual("test3", r.alternative.alternative.name)
        self.assertEqual(VersionRange(), r.alternative.alternative.version)
        self.assertIsNone(r.alternative.alternative.alternative)

    def test_iter(self):
        it = iter(PackageRelation.from_args(
            ("test", "le", 2), ("test2", "ge", 3))
        )
        self.assertEqual("test", next(it).name)
        self.assertEqual("test2", next(it).name)
        with self.assertRaises(StopIteration):
            next(it)


class TestVersionRange(TestObjectBase):
    def test_equal(self):
        self.check_equal(
            VersionRange("eq", 1),
            VersionRange("eq", 1),
            VersionRange("le", 1)
        )

    def test_hashable(self):
        self.check_hashable(
            VersionRange(op="le"),
            VersionRange(op="le", edge=3)
        )

    def __check_intersection(self, assertion, cases):
        for data in cases:
            v1 = VersionRange(*data[0])
            v2 = VersionRange(*data[1])
            assertion(
                v1.has_intersection(v2), msg="%s and %s" % (v1, v2)
            )
            assertion(
                v2.has_intersection(v1), msg="%s and %s" % (v2, v1)
            )

    def test_have_intersection(self):
        cases = [
            (("eq", 2), ("eq", 2)),
            (("eq", 2), ("lt", 3)),
            (("eq", 2), ("gt", 1)),
            (("lt", 2), ("gt", 1)),
            (("lt", 2), ("lt", 3)),
            (("lt", 2), ("lt", 2)),
            (("lt", 2), ("le", 2)),
            (("gt", 2), ("gt", 1)),
            (("gt", 2), ("lt", 3)),
            (("gt", 2), ("ge", 2)),
            (("gt", 2), ("gt", 2)),
            (("ge", 2), ("le", 2)),
            ((None, None), ("eq", 2)),
        ]
        self.__check_intersection(self.assertTrue, cases)

    def test_does_not_have_intersection(self):
        cases = [
            (("eq", 2), ("eq", 1)),
            (("eq", 2), ("lt", 2)),
            (("eq", 2), ("gt", 2)),
            (("eq", 2), ("gt", 3)),
            (("eq", 2), ("lt", 1)),
            (("lt", 2), ("ge", 2)),
            (("lt", 2), ("gt", 3)),
            (("gt", 2), ("le", 2)),
            (("gt", 2), ("lt", 1)),
        ]
        self.__check_intersection(self.assertFalse, cases)

    def test_intersection_is_typesafe(self):
        with self.assertRaises(TypeError):
            VersionRange("eq", 1).has_intersection(("eq", 1))


class TestPackageVersion(base.TestCase):
    def test_get_from_string(self):
        ver = PackageVersion.from_string("1.0-22")
        self.assertEqual(0, ver.epoch)
        self.assertEqual(('1', '0'), ver.version)
        self.assertEqual(('22',), ver.release)

        ver2 = PackageVersion.from_string("1-11.0-2")
        self.assertEqual(1, ver2.epoch)
        self.assertEqual(('11', '0'), ver2.version)
        self.assertEqual(('2',), ver2.release)

    def test_compare(self):
        ver1 = PackageVersion.from_string("6.3-31.5")
        ver2 = PackageVersion.from_string("13.9-16.12")
        self.assertLess(ver1, ver2)
        self.assertGreater(ver2, ver1)
        self.assertEqual(ver1, ver1)
        self.assertLess(ver1, "6.3-40")
        self.assertGreater(ver1, "6.3-31.4a")
