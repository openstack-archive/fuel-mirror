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
import os.path as path
import sys

import six

from packetary.library.utils import localize_repo_url
from packetary.objects import FileChecksum
from packetary.tests import base
from packetary.tests.stubs.generator import gen_repository
from packetary.tests.stubs.helpers import get_compressed


REPOMD = path.join(path.dirname(__file__), "data", "repomd.xml")

REPOMD2 = path.join(path.dirname(__file__), "data", "repomd2.xml")

PRIMARY_DB = path.join(path.dirname(__file__), "data", "primary.xml")

GROUPS_DB = path.join(path.dirname(__file__), "data", "groups.xml")


class TestRpmDriver(base.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.createrepo = sys.modules["createrepo"] = mock.MagicMock()
        # import driver class after patching sys.modules
        from packetary.drivers import rpm_driver

        super(TestRpmDriver, cls).setUpClass()
        cls.driver = rpm_driver.RpmRepositoryDriver()

    def setUp(self):
        self.createrepo.reset_mock()
        self.connection = mock.MagicMock()

    def test_parse_urls(self):
        self.assertItemsEqual(
            [
                "http://host/centos/os",
                "http://host/centos/updates"
            ],
            self.driver.parse_urls([
                "http://host/centos/os",
                "http://host/centos/updates/",
            ])
        )

    def test_get_repository(self):
        repos = []

        self.driver.get_repository(
            self.connection,
            "http://host/centos/os/x86_64",
            "x86_64",
            repos.append
        )

        self.assertEqual(1, len(repos))
        repo = repos[0]
        self.assertEqual("/centos/os/x86_64", repo.name)
        self.assertEqual("", repo.origin)
        self.assertEqual("x86_64", repo.architecture)
        self.assertEqual("http://host/centos/os/x86_64/", repo.url)

    def test_get_packages(self):
        streams = []
        for conv, fname in zip(
                (lambda x: six.BytesIO(x.read()),
                 get_compressed, get_compressed),
                (REPOMD, GROUPS_DB, PRIMARY_DB)
        ):
            with open(fname, "rb") as s:
                streams.append(conv(s))

        packages = []
        self.connection.open_stream.side_effect = streams
        self.driver.get_packages(
            self.connection,
            gen_repository("test", url="http://host/centos/os/x86_64/"),
            packages.append
        )
        self.connection.open_stream.assert_any_call(
            "http://host/centos/os/x86_64/repodata/repomd.xml"
        )
        self.connection.open_stream.assert_any_call(
            "http://host/centos/os/x86_64/repodata/groups.xml.gz"
        )
        self.connection.open_stream.assert_any_call(
            "http://host/centos/os/x86_64/repodata/primary.xml.gz"
        )
        self.assertEqual(2, len(packages))
        package = packages[0]
        self.assertEqual("test1", package.name)
        self.assertEqual("1.1.1.1-1.el7", package.version)
        self.assertEqual(100, package.filesize)
        self.assertEqual(
            FileChecksum(
                None,
                None,
                'e8ed9e0612e813491ed5e7c10502a39e'
                '43ec665afd1321541dea211202707a65'),
            package.checksum
        )
        self.assertEqual(
            "Packages/test1.rpm", package.filename
        )
        self.assertItemsEqual(
            ['test2 (eq 0-1.1.1.1-1.el7)'],
            (str(x) for x in package.requires)
        )
        self.assertItemsEqual(
            ["file (any)"],
            (str(x) for x in package.provides)
        )
        self.assertItemsEqual(
            ["test-old (any)"],
            (str(x) for x in package.obsoletes)
        )
        self.assertTrue(package.mandatory)
        self.assertFalse(packages[1].mandatory)

    def test_get_packages_if_group_not_gzipped(self):
        streams = []
        for conv, fname in zip(
                (lambda x: six.BytesIO(x.read()),
                 lambda x: six.BytesIO(x.read()),
                 get_compressed),
                (REPOMD2, GROUPS_DB, PRIMARY_DB)
        ):
            with open(fname, "rb") as s:
                streams.append(conv(s))

        packages = []
        self.connection.open_stream.side_effect = streams
        self.driver.get_packages(
            self.connection,
            gen_repository("test", url="http://host/centos/os/x86_64/"),
            packages.append
        )
        self.connection.open_stream.assert_any_call(
            "http://host/centos/os/x86_64/repodata/groups.xml"
        )
        self.assertEqual(2, len(packages))
        package = packages[0]
        self.assertTrue(package.mandatory)

    @mock.patch("packetary.drivers.rpm_driver.shutil")
    def test_rebuild_repository(self, shutil):
        self.createrepo.MDError = ValueError
        self.createrepo.MetaDataGenerator().doFinalMove.side_effect = [
            None, self.createrepo.MDError()
        ]
        repo = gen_repository("test", url="file:///repo/os/x86_64")
        self.createrepo.MetaDataConfig().outputdir = "/repo/os/x86_64"
        self.createrepo.MetaDataConfig().tempdir = "tmp"

        self.driver.rebuild_repository(repo, set())

        self.assertEqual(
            "/repo/os/x86_64",
            self.createrepo.MetaDataConfig().directory
        )
        self.assertTrue(self.createrepo.MetaDataConfig().update)
        self.createrepo.MetaDataGenerator()\
            .doPkgMetadata.assert_called_once_with()
        self.createrepo.MetaDataGenerator()\
            .doRepoMetadata.assert_called_once_with()
        self.createrepo.MetaDataGenerator()\
            .doFinalMove.assert_called_once_with()

        with self.assertRaises(RuntimeError):
            self.driver.rebuild_repository(repo, set())
        shutil.rmtree.assert_called_once_with(
            "/repo/os/x86_64/tmp", ignore_errors=True
        )

    @mock.patch("packetary.drivers.rpm_driver.utils")
    def test_fork_repository(self, utils):
        repo = gen_repository("os", url="http://localhost/os/x86_64/")
        utils.localize_repo_url = localize_repo_url
        new_repo = self.driver.fork_repository(
            self.connection,
            repo,
            "/repo"
        )

        utils.ensure_dir_exist.assert_called_once_with("/repo/os/x86_64/")
        self.assertEqual(repo.name, new_repo.name)
        self.assertEqual(repo.architecture, new_repo.architecture)
        self.assertEqual("/repo/os/x86_64/", new_repo.url)
        self.createrepo.MetaDataGenerator()\
            .doFinalMove.assert_called_once_with()
