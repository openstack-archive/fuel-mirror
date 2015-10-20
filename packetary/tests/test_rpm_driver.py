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
import os.path as path
import six

from packetary.drivers import rpm_driver
from packetary.tests import base
from packetary.tests.stubs.generator import gen_repository
from packetary.tests.stubs.helpers import get_compressed


REPOMD = path.join(path.dirname(__file__), "data", "repomd.xml")

PRIMARY_DB = path.join(path.dirname(__file__), "data", "primary.xml")

GROUPS_DB = path.join(path.dirname(__file__), "data", "groups.xml")


class TestRpmDriver(base.TestCase):
    @classmethod
    def setUpClass(cls):
        super(TestRpmDriver, cls).setUpClass()
        cls.driver = rpm_driver.RpmRepositoryDriver()

    def setUp(self):
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
            self.connection, "http://host/centos/os", "x86_64", repos.append
        )

        self.assertEqual(1, len(repos))
        repo = repos[0]
        self.assertEqual("os", repo.name)
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
            rpm_driver.FileChecksum(
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

    @mock.patch.multiple(
        "packetary.drivers.rpm_driver",
        createrepo=mock.DEFAULT,
        shutil=mock.DEFAULT,
    )
    def test_rebuild_repository(self, createrepo, shutil):
        createrepo.MDError = ValueError
        createrepo.MetaDataGenerator().doFinalMove.side_effect = [
            None, createrepo.MDError()
        ]
        repo = gen_repository("test", url="file:///repo/os/x86_64")
        createrepo.MetaDataConfig().outputdir = "/repo/os/x86_64"
        createrepo.MetaDataConfig().tempdir = "tmp"

        self.driver.rebuild_repository(repo, set())

        self.assertEqual(
            "/repo/os/x86_64",
            createrepo.MetaDataConfig().directory
        )
        self.assertTrue(createrepo.MetaDataConfig().update)
        createrepo.MetaDataGenerator()\
            .doPkgMetadata.assert_called_once_with()
        createrepo.MetaDataGenerator()\
            .doRepoMetadata.assert_called_once_with()
        createrepo.MetaDataGenerator()\
            .doFinalMove.assert_called_once_with()

        with self.assertRaises(RuntimeError):
            self.driver.rebuild_repository(repo, set())
        shutil.rmtree.assert_called_once_with(
            "/repo/os/x86_64/tmp", ignore_errors=True
        )

    @mock.patch.multiple(
        "packetary.drivers.rpm_driver",
        utils=mock.DEFAULT,
        createrepo=mock.DEFAULT
    )
    def test_fork_repository(self, createrepo, utils):
        repo = gen_repository("os", url="http://localhost/os/x86_64")
        clone = self.driver.fork_repository(
            self.connection,
            repo,
            "/repo"
        )

        utils.ensure_dir_exist.assert_called_once_with("/repo/os/x86_64/")
        self.assertEqual(repo.name, clone.name)
        self.assertEqual(repo.architecture, clone.architecture)
        self.assertEqual("/repo/os/x86_64/", clone.url)
        createrepo.MetaDataGenerator()\
            .doFinalMove.assert_called_once_with()
