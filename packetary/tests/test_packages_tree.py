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

import warnings

from packetary.objects import Index
from packetary.objects import PackagesTree
from packetary.tests import base
from packetary.tests.stubs import generator


class TestPackagesTree(base.TestCase):
    def setUp(self):
        super(TestPackagesTree, self).setUp()

    def test_get_unresolved_dependencies(self):
        ptree = PackagesTree()
        ptree.add(generator.gen_package(
            1, requires=[generator.gen_relation("unresolved")]))
        ptree.add(generator.gen_package(2, requires=None))
        ptree.add(generator.gen_package(
            3, requires=[generator.gen_relation("package1")]
        ))
        ptree.add(generator.gen_package(
            4,
            requires=[generator.gen_relation("loop")],
            obsoletes=[generator.gen_relation("loop", ["le", 1])]
        ))

        unresolved = ptree.get_unresolved_dependencies()
        self.assertItemsEqual(
            ["loop", "unresolved"],
            (x.name for x in unresolved)
        )

    def test_get_unresolved_dependencies_with_main(self):
        ptree = PackagesTree()
        ptree.add(generator.gen_package(
            1, requires=[generator.gen_relation("unresolved")]))
        ptree.add(generator.gen_package(2, requires=None))
        ptree.add(generator.gen_package(
            3, requires=[generator.gen_relation("package1")]
        ))
        ptree.add(generator.gen_package(
            4,
            requires=[generator.gen_relation("package5")]
        ))
        main = Index()
        main.add(generator.gen_package(5, requires=[
            generator.gen_relation("package6")
        ]))

        unresolved = ptree.get_unresolved_dependencies(main)
        self.assertItemsEqual(
            ["unresolved"],
            (x.name for x in unresolved)
        )

    def test_get_minimal_subset_with_master(self):
        ptree = PackagesTree()
        ptree.add(generator.gen_package(1, requires=None))
        ptree.add(generator.gen_package(2, requires=None))
        ptree.add(generator.gen_package(3, requires=None))
        ptree.add(generator.gen_package(
            4, requires=[generator.gen_relation("package1")]
        ))

        master = Index()
        master.add(generator.gen_package(1, requires=None))
        master.add(generator.gen_package(
            5,
            requires=[generator.gen_relation(
                "package10",
                alternative=generator.gen_relation("package4")
            )]
        ))

        unresolved = set([generator.gen_relation("package3")])
        resolved = ptree.get_minimal_subset(master, unresolved)
        self.assertItemsEqual(
            ["package3", "package4"],
            (x.name for x in resolved)
        )

    def test_get_minimal_subset_without_master(self):
        ptree = PackagesTree()
        ptree.add(generator.gen_package(1, requires=None))
        ptree.add(generator.gen_package(2, requires=None))
        ptree.add(generator.gen_package(
            3, requires=[generator.gen_relation("package1")]
        ))
        unresolved = set([generator.gen_relation("package3")])
        resolved = ptree.get_minimal_subset(None, unresolved)
        self.assertItemsEqual(
            ["package3", "package1"],
            (x.name for x in resolved)
        )

    def test_mandatory_packages_always_included(self):
        ptree = PackagesTree()
        ptree.add(generator.gen_package(1, requires=None, mandatory=True))
        ptree.add(generator.gen_package(2, requires=None))
        ptree.add(generator.gen_package(3, requires=None))
        unresolved = set([generator.gen_relation("package3")])
        resolved = ptree.get_minimal_subset(None, unresolved)
        self.assertItemsEqual(
            ["package3", "package1"],
            (x.name for x in resolved)
        )

    def test_warning_if_unresolved(self):
        ptree = PackagesTree()
        ptree.add(generator.gen_package(
            1, requires=None))

        with warnings.catch_warnings(record=True) as log:
            ptree.get_minimal_subset(
                None, [generator.gen_relation("package2")]
            )
        self.assertIn("package2", str(log[0]))
