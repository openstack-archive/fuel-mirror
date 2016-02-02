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
import subprocess

# The cmd2 does not work with python3.5
# because it tries to get access to the property mswindows,
# that was removed in 3.5
subprocess.mswindows = False

from packetary.cli.commands import clone
from packetary.cli.commands import packages
from packetary.cli.commands import unresolved
from packetary.tests import base
from packetary.tests.stubs.generator import gen_package
from packetary.tests.stubs.generator import gen_relation
from packetary.tests.stubs.generator import gen_repository
from packetary.tests.stubs.helpers import CallbacksAdapter


@mock.patch.multiple(
    "packetary.api",
    RepositoryController=mock.DEFAULT,
    ConnectionsManager=mock.DEFAULT,
    AsynchronousSection=mock.MagicMock()
)
@mock.patch(
    "packetary.cli.commands.base.BaseRepoCommand.stdout"
)
class TestCliCommands(base.TestCase):
    common_argv = [
        "--ignore-errors-num=3",
        "--threads-num=8",
        "--retries-num=10",
        "--retry-interval=1",
        "--http-proxy=http://proxy",
        "--https-proxy=https://proxy"
    ]

    clone_argv = [
        "-o", "http://localhost/origin",
        "-d", ".",
        "-r", "http://localhost/requires",
        "-b", "test-package",
        "-t", "deb",
        "-a", "x86_64",
        "--clean",
    ]

    packages_argv = [
        "-o", "http://localhost/origin",
        "-t", "deb",
        "-a", "x86_64"
    ]

    unresolved_argv = [
        "-o", "http://localhost/origin",
        "-t", "deb",
        "-a", "x86_64"
    ]

    def start_cmd(self, cmd, argv):
        cmd.debug(argv + self.common_argv)

    def check_context(self, context, ConnectionsManager):
        self.assertEqual(3, context._ignore_errors_num)
        self.assertEqual(8, context._threads_num)
        self.assertIs(context._connection, ConnectionsManager.return_value)
        ConnectionsManager.assert_called_once_with(
            proxy="http://proxy",
            secure_proxy="https://proxy",
            retries_num=10,
            retry_interval=1
        )

    def test_clone_cmd(self, stdout, RepositoryController, **kwargs):
        ctrl = RepositoryController.load()
        ctrl.copy_packages = CallbacksAdapter()
        ctrl.load_repositories = CallbacksAdapter()
        ctrl.load_packages = CallbacksAdapter()
        ctrl.copy_packages.return_value = [1, 0]
        repo = gen_repository()
        ctrl.load_repositories.side_effect = [repo, gen_repository()]
        ctrl.load_packages.side_effect = [
            gen_package(repository=repo),
            gen_package()
        ]
        self.start_cmd(clone, self.clone_argv)
        RepositoryController.load.assert_called_with(
            mock.ANY, "deb", "x86_64"
        )
        self.check_context(
            RepositoryController.load.call_args[0][0], **kwargs
        )
        stdout.write.assert_called_once_with(
            "Packages copied: 1/2.\n"
        )

    def test_get_packages_cmd(self, stdout, RepositoryController, **kwargs):
        ctrl = RepositoryController.load()
        ctrl.load_packages = CallbacksAdapter()
        ctrl.load_packages.return_value = gen_package(
            name="test1",
            filesize=1,
            requires=None,
            obsoletes=None,
            provides=None
        )
        self.start_cmd(packages, self.packages_argv)
        RepositoryController.load.assert_called_with(
            mock.ANY, "deb", "x86_64"
        )
        self.check_context(
            RepositoryController.load.call_args[0][0], **kwargs
        )
        self.assertIn(
            "test1; test; 1; test1.pkg; 1;",
            stdout.write.call_args_list[3][0][0]
        )

    def test_get_unresolved_cmd(self, stdout, RepositoryController, **kwargs):
        ctrl = RepositoryController.load()
        ctrl.load_packages = CallbacksAdapter()
        ctrl.load_packages.return_value = gen_package(
            name="test1",
            requires=[gen_relation("test2")]
        )
        self.start_cmd(unresolved, self.unresolved_argv)
        RepositoryController.load.assert_called_with(
            mock.ANY, "deb", "x86_64"
        )
        self.check_context(
            RepositoryController.load.call_args[0][0], **kwargs
        )
        self.assertIn(
            "test2; any; -",
            stdout.write.call_args_list[3][0][0]
        )
