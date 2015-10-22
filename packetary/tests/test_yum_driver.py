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

from __future__ import with_statement

import mock
import os.path as path


from packetary.library.drivers import yum_driver
from packetary.library.drivers import yum_package
from packetary.library.package import Relation
from packetary.tests import base
from packetary.tests.stubs.context import Context


REPOMD = path.join(path.dirname(__file__), "data", "repomd.xml")
PRIMARY_DB = path.join(path.dirname(__file__), "data", "primary.xml.gz")


class TestYumDriver(base.TestCase):
    @classmethod
    def setUpClass(cls):
        super(TestYumDriver, cls).setUpClass()
        cls.driver = yum_driver.Driver(
            Context(),
            "x86_64"
        )

    def test_get_path(self):
        package = mock.MagicMock(
            baseurl=".", reponame="os", filename="test.rpm"
        )
        self.assertEqual(
            "dir/os/x86_64/test.rpm",
            self.driver.get_path("dir", package)
        )
        self.assertEqual(
            "./os/x86_64/test.rpm",
            self.driver.get_path(None, package)
        )

    def test_load(self):
        packages = []
        connection = self.driver.connections.connection
        with open(REPOMD, "rb") as repomd:
            with open(PRIMARY_DB, "rb") as primary:
                connection.open_stream.side_effect = [repomd, primary]
                self.driver.load(
                    "http://host/centos", "os", packages.append
                )

        connection.open_stream.assert_any_call(
            "http://host/centos/os/x86_64/repodata/repomd.xml"
        )
        connection.open_stream.assert_any_call(
            "http://host/centos/os/x86_64/repodata/primary.xml.gz"
        )
        self.assertEqual(1, len(packages))
        package = packages[0]
        self.assertEqual("test", package.name)
        self.assertEqual("0-1.1.1.1-1.el7", str(package.version))
        self.assertEqual(100, package.size)
        self.assertEqual(
            (
                "sha256",
                "e8ed9e0612e813491ed5e7c10502a39e"
                "43ec665afd1321541dea211202707a65"
            ),
            packages[0].checksum
        )
        self.assertEqual(
            "Packages/test.rpm", package.filename
        )
        self.assertItemsEqual(
            [Relation(
                ['test2', 'eq',
                 yum_package.Version({
                     "epoch": "0",
                     "ver": "1.1.1.1",
                     "rel": "1.el7"
                 })]
            )],
            package.requires
        )
        self.assertItemsEqual(
            [Relation("file")], package.provides
        )
        self.assertItemsEqual(
            [Relation("test-old")], package.obsoletes
        )

    def test_parse_urls(self):
        self.assertItemsEqual(
            [
                ["http://host/centos", "os"],
                ["http://host/centos", "updates"],
            ],
            self.driver.parse_urls([
                "http://host/centos/os",
                "http://host/centos/updates/",
            ])
        )


@mock.patch.multiple(
    "packetary.library.drivers.yum_driver",
    os=mock.DEFAULT,
    subprocess=mock.DEFAULT,
    createrepo="createrepo"
)
class TestYumIndexWriter(base.TestCase):
    def setUp(self):
        super(TestYumIndexWriter, self).setUp()
        driver = mock.MagicMock()
        driver.arch = "x86_64"
        self.writer = yum_driver.YumIndexWriter(
            driver,
            "/root"
        )

    def test_add(self, **_):
        package = mock.MagicMock(
            reponame="os", filename="test.rpm", baseurl="/root"
        )
        self.writer.add(package)
        self.assertItemsEqual(
            [package.filename],
            self.writer.repos[package.reponame]
        )

    def test_commit(self, os, subprocess, **_):
        package = mock.MagicMock(reponame="os", filename="test.rpm")
        self.writer.add(package)
        os.path.join = path.join
        os.path.exists.return_value = True
        self.writer.commit(True)

        subprocess.check_call.assert_called_once_with(
            ["createrepo", "/root/os/x86_64", "--update"]
        )
        self.assertEqual(0, os.remove.call_count)

    def test_commit_with_cleanup(self, os, subprocess, **_):
        package = mock.MagicMock(reponame="os", filename="test.rpm")
        package2 = mock.MagicMock(reponame="os", filename="test2.rpm")
        self.writer.add(package)
        os.path.join = path.join
        os.path.exists.return_value = True
        self.writer.driver.load = lambda *x: x[-1](package2)
        self.writer.driver.get_path.return_value = "/root/os/x86_64/test2.rpm"
        self.writer.commit(False)

        subprocess.check_call.assert_called_once_with(
            ["createrepo", "/root/os/x86_64", "--update"]
        )
        os.remove.assert_called_with("/root/os/x86_64/test2.rpm")
