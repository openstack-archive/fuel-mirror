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
import mock
import six

from packetary.controllers import RepositoryController
from packetary.tests import base
from packetary.tests.stubs.executor import Executor
from packetary.tests.stubs.generator import gen_package
from packetary.tests.stubs.generator import gen_repository
from packetary.tests.stubs.helpers import CallbacksAdapter


class TestRepositoryController(base.TestCase):
    def setUp(self):
        self.driver = mock.MagicMock()
        self.context = mock.MagicMock()
        self.context.async_section.return_value = Executor()
        self.ctrl = RepositoryController(self.context, self.driver, "x86_64")

    def test_load_fail_if_unknown_driver(self):
        with self.assertRaisesRegexp(NotImplementedError, "unknown_driver"):
            RepositoryController.load(
                self.context,
                "unknown_driver",
                "x86_64"
            )

    @mock.patch("packetary.controllers.repository.stevedore")
    def test_load_driver(self, stevedore):
        stevedore.ExtensionManager.return_value = {
            "test": mock.MagicMock(obj=self.driver)
        }
        RepositoryController._drivers = None
        controller = RepositoryController.load(self.context, "test", "x86_64")
        self.assertIs(self.driver, controller.driver)

    def test_load_repositories(self):
        self.driver.parse_urls.return_value = ["test1"]
        consumer = mock.MagicMock()
        self.ctrl.load_repositories("file:///test1", consumer)
        self.driver.parse_urls.assert_called_once_with(["file:///test1"])
        self.driver.get_repository.assert_called_once_with(
            self.context.connection, "test1", "x86_64", consumer
        )
        for url in [six.u("file:///test1"), ["file:///test1"]]:
            self.driver.reset_mock()
            self.ctrl.load_repositories(url, consumer)
            if not isinstance(url, list):
                url = [url]
            self.driver.parse_urls.assert_called_once_with(url)

    def test_load_packages(self):
        repo = mock.MagicMock()
        consumer = mock.MagicMock()
        self.ctrl.load_packages([repo], consumer)
        self.driver.get_packages.assert_called_once_with(
            self.context.connection, repo, consumer
        )

    @mock.patch("packetary.controllers.repository.os")
    def test_assign_packages(self, os):
        repo = gen_repository(url="/test/repo")
        packages = [
            gen_package(name="test1", repository=repo),
            gen_package(name="test2", repository=repo)
        ]
        existed_packages = [
            gen_package(name="test3", repository=repo),
            gen_package(name="test2", repository=repo)
        ]

        os.path.join = lambda *x: "/".join(x)
        self.driver.get_packages = CallbacksAdapter()
        self.driver.get_packages.return_value = existed_packages
        self.ctrl.assign_packages(repo, packages, True)
        os.remove.assert_not_called()
        all_packages = set(packages + existed_packages)
        self.driver.rebuild_repository.assert_called_once_with(
            repo, all_packages
        )
        self.driver.rebuild_repository.reset_mock()
        self.ctrl.assign_packages(repo, packages, False)
        self.driver.rebuild_repository.assert_called_once_with(
            repo, set(packages)
        )
        os.remove.assert_called_once_with("/test/repo/test3.pkg")

    def test_copy_packages(self):
        repo = gen_repository(url="file:///repo/")
        packages = [
            gen_package(name="test1", repository=repo, filesize=10),
            gen_package(name="test2", repository=repo, filesize=-1)
        ]
        target = gen_repository(url="/test/repo")
        self.context.connection.retrieve.side_effect = [0, 10]
        observer = mock.MagicMock()
        self.ctrl.copy_packages(target, packages, True, observer)
        observer.assert_has_calls([mock.call(0), mock.call(10)])
        self.context.connection.retrieve.assert_any_call(
            "file:///repo/test1.pkg",
            "/test/repo/test1.pkg",
            size=10
        )
        self.context.connection.retrieve.assert_any_call(
            "file:///repo/test2.pkg",
            "/test/repo/test2.pkg",
            size=-1
        )
        self.driver.rebuild_repository.assert_called_once_with(
            target, set(packages)
        )

    @mock.patch("packetary.controllers.repository.os")
    def test_clone_repository(self, os):
        os.path.abspath.return_value = "/root/repo"
        repos = [
            gen_repository(name="test1"),
            gen_repository(name="test2")
        ]
        clones = [copy.copy(x) for x in repos]
        self.driver.fork_repository.side_effect = clones
        mirrors = self.ctrl.clone_repositories(repos, "./repo")
        for r in repos:
            self.driver.fork_repository.assert_any_call(
                self.context.connection, r, "/root/repo", False, False
            )
        self.assertEqual(mirrors, dict(zip(repos, clones)))
