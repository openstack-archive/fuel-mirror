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

import mock

from packetary.api import Configuration
from packetary.api import Context
from packetary.api import RepositoryApi
from packetary.tests import base
from packetary.tests.stubs import generator
from packetary.tests.stubs.helpers import CallbacksAdapter


class TestRepositoryApi(base.TestCase):
    def test_get_packages_as_is(self):
        controller = CallbacksAdapter()
        pkg = generator.gen_package(name="test")
        controller.load_packages.side_effect = [
            pkg
        ]
        api = RepositoryApi(controller)
        packages = api.get_packages("file:///repo1")
        self.assertEqual(1, len(packages))
        package = packages.pop()
        self.assertIs(pkg, package)

    def test_get_packages_with_depends_resolving(self):
        controller = CallbacksAdapter()
        controller.load_packages.side_effect = [
            [
                generator.gen_package(idx=1, requires=None),
                generator.gen_package(
                    idx=2, requires=[generator.gen_relation("package1")]
                ),
                generator.gen_package(
                    idx=3, requires=[generator.gen_relation("package1")]
                ),
                generator.gen_package(idx=4, requires=None),
                generator.gen_package(idx=5, requires=None),
            ],
            generator.gen_package(
                idx=6, requires=[generator.gen_relation("package2")]
            ),
        ]

        api = RepositoryApi(controller)
        packages = api.get_packages([
            "file:///repo1", "file:///repo2"
        ],
            "file:///repo3", ["package4"]
        )

        self.assertEqual(3, len(packages))
        self.assertItemsEqual(
            ["package1", "package4", "package2"],
            (x.name for x in packages)
        )
        controller.load_repositories.assert_any_call(
            ["file:///repo1", "file:///repo2"]
        )
        controller.load_repositories.assert_any_call(
            "file:///repo3"
        )

    def test_clone_repositories_as_is(self):
        controller = CallbacksAdapter()
        repo = generator.gen_repository(name="repo1")
        packages = [
            generator.gen_package(name="test1", repository=repo),
            generator.gen_package(name="test2", repository=repo)
        ]
        mirror = generator.gen_repository(name="mirror")
        controller.load_repositories.return_value = repo
        controller.load_packages.return_value = packages
        controller.clone_repositories.return_value = {repo: mirror}
        controller.copy_packages.return_value = [0, 1]
        api = RepositoryApi(controller)
        stats = api.clone_repositories(
            ["file:///repo1"], "/mirror", keep_existing=True
        )
        self.assertEqual(2, stats.total)
        self.assertEqual(1, stats.copied)
        controller.copy_packages.assert_called_once_with(
            mirror, set(packages), True
        )

    def test_copy_minimal_subset_of_repository(self):
        controller = CallbacksAdapter()
        repo1 = generator.gen_repository(name="repo1")
        repo2 = generator.gen_repository(name="repo2")
        repo3 = generator.gen_repository(name="repo3")
        mirror1 = generator.gen_repository(name="mirror1")
        mirror2 = generator.gen_repository(name="mirror2")
        pkg_group1 = [
            generator.gen_package(
                idx=1, requires=None, repository=repo1
            ),
            generator.gen_package(
                idx=1, version=2, requires=None, repository=repo1
            ),
            generator.gen_package(
                idx=2, requires=None, repository=repo1
            )
        ]
        pkg_group2 = [
            generator.gen_package(
                idx=4,
                requires=[generator.gen_relation("package1")],
                repository=repo2,
                mandatory=True,
            )
        ]
        pkg_group3 = [
            generator.gen_package(
                idx=3, requires=None, repository=repo1
            )
        ]
        controller.load_repositories.side_effect = [[repo1, repo2], repo3]
        controller.load_packages.side_effect = [
            pkg_group1 + pkg_group2 + pkg_group3,
            generator.gen_package(
                idx=6,
                repository=repo3,
                requires=[generator.gen_relation("package2")]
            )
        ]
        controller.clone_repositories.return_value = {
            repo1: mirror1, repo2: mirror2
        }
        controller.copy_packages.return_value = 1
        api = RepositoryApi(controller)
        api.clone_repositories(
            ["file:///repo1", "file:///repo2"], "/mirror",
            ["file:///repo3"],
            keep_existing=True
        )
        controller.copy_packages.assert_any_call(
            mirror1, set(pkg_group1), True
        )
        controller.copy_packages.assert_any_call(
            mirror2, set(pkg_group2), True
        )
        self.assertEqual(2, controller.copy_packages.call_count)

    def test_get_unresolved(self):
        controller = CallbacksAdapter()
        pkg = generator.gen_package(
            name="test", requires=[generator.gen_relation("test2")]
        )
        controller.load_packages.side_effect = [
            pkg
        ]
        api = RepositoryApi(controller)
        r = api.get_unresolved_dependencies("file:///repo1")
        controller.load_repositories.assert_called_once_with("file:///repo1")
        self.assertItemsEqual(
            ["test2"],
            (x.name for x in r)
        )

    def test_get_unresolved_with_main(self):
        controller = CallbacksAdapter()
        pkg1 = generator.gen_package(
            name="test1", requires=[
                generator.gen_relation("test2"),
                generator.gen_relation("test3")
            ]
        )
        pkg2 = generator.gen_package(
            name="test2", requires=[generator.gen_relation("test4")]
        )
        controller.load_packages.side_effect = [
            pkg1, pkg2
        ]
        api = RepositoryApi(controller)
        r = api.get_unresolved_dependencies("file:///repo1", "file:///repo2")
        controller.load_repositories.assert_any_call("file:///repo1")
        controller.load_repositories.assert_any_call("file:///repo2")
        self.assertItemsEqual(
            ["test3"],
            (x.name for x in r)
        )

    def test_parse_requirements(self):
        requirements = RepositoryApi._parse_requirements(
            ["p1 le 2 | p2 | p3 ge 2"]
        )

        expected = generator.gen_relation(
            "p1",
            ["le", '2'],
            generator.gen_relation(
                "p2",
                None,
                generator.gen_relation(
                    "p3",
                    ["ge", '2']
                )
            )
        )
        self.assertEqual(1, len(requirements))
        self.assertEqual(
            list(expected),
            list(requirements.pop())
        )


class TestContext(base.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = Configuration(
            threads_num=2,
            ignore_errors_num=3,
            retries_num=5,
            retry_interval=5,
            http_proxy="http://localhost",
            https_proxy="https://localhost"
        )

    @mock.patch("packetary.api.ConnectionsManager")
    def test_initialise_connection_manager(self, conn_manager):
        context = Context(self.config)
        conn_manager.assert_called_once_with(
            proxy="http://localhost",
            secure_proxy="https://localhost",
            retries_num=5,
            retry_interval=5
        )

        self.assertIs(
            conn_manager(),
            context.connection
        )

    @mock.patch("packetary.api.AsynchronousSection")
    def test_asynchronous_section(self, async_section):
        context = Context(self.config)
        s = context.async_section()
        async_section.assert_called_with(2, 3)
        self.assertIs(s, async_section())
        context.async_section(0)
        async_section.assert_called_with(2, 0)
