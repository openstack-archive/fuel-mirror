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

import mock
import six

from packetary.library.repository import Repository
from packetary.tests import base
from packetary.tests.stubs.context import Context
from packetary.tests.stubs.driver import RepoDriver


class TestRepository(base.TestCase):
    @classmethod
    def setUpClass(cls):
        super(TestRepository, cls).setUpClass()
        cls.repo = Repository(
            Context(),
            "stub",
            "x86_64",
            drivers=mock.MagicMock(stub=RepoDriver)
        )

    def test_load_packages(self):
        url = "url1"
        packages = list()
        self.repo.load_packages(url, packages.append)
        self.assertEqual(packages, self.repo.driver.packages)

    @mock.patch("packetary.library.repository.os")
    def test_copy_packages(self, os):
        self.repo.driver.generate_packages(4, size=10)
        packages = self.repo.driver.packages
        os.stat.side_effect = [
            mock.MagicMock(st_size=packages[0].size),
            mock.MagicMock(st_size=packages[1].size + 1),
            mock.MagicMock(st_size=packages[2].size - 1),
            OSError(2, "error")
        ]

        self.repo.copy_packages(packages, "target", True)
        index_writer = self.repo.driver.create_index(".")
        self.assertEqual(
            len(packages), index_writer.add.call_count
        )
        index_writer.flush.assert_called_once_with(True)

        retrieve = self.repo.context.connections.get().__enter__().retrieve
        call_args = retrieve.call_args_list
        self.assertEqual(3, retrieve.call_count)
        packages[1].props['size'] = 0
        packages[2].props['size'] -= 1
        packages[3].props['size'] = 0

        for i in six.moves.range(3):
            self.assertItemsEqual(
                [
                    self.repo.driver.get_path(".", packages[i + 1]),
                    self.repo.driver.get_path("target", packages[i + 1]),
                    packages[i + 1].size,
                ],
                call_args[i][0]
            )
