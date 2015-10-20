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


from packetary.drivers import debian_driver
from packetary.tests import base
from packetary.tests.stubs.generator import gen_package
from packetary.tests.stubs.generator import gen_repository
from packetary.tests.stubs.helpers import get_compressed


PACKAGES = path.join(path.dirname(__file__), "data", "Packages")
RELEASE = path.join(path.dirname(__file__), "data", "Release")


class TestDebDriver(base.TestCase):
    @classmethod
    def setUpClass(cls):
        super(TestDebDriver, cls).setUpClass()
        cls.driver = debian_driver.DebRepositoryDriver()

    def setUp(self):
        self.connection = mock.MagicMock()

    def test_parse_urls(self):
        self.assertItemsEqual(
            [
                ("http://host", "trusty", "main"),
                ("http://host", "trusty", "restricted"),
            ],
            self.driver.parse_urls(
                ["http://host/dists/ trusty main restricted"]
            )
        )
        self.assertItemsEqual(
            [("http://host", "trusty", "main")],
            self.driver.parse_urls(
                ["http://host/dists trusty main"]
            )
        )
        self.assertItemsEqual(
            [("http://host", "trusty", "main")],
            self.driver.parse_urls(
                ["http://host/ trusty main"]
            )
        )
        self.assertItemsEqual(
            [
                ("http://host", "trusty", "main"),
                ("http://host2", "trusty", "main"),
            ],
            self.driver.parse_urls(
                [
                    "http://host/ trusty main",
                    "http://host2/dists/ trusty main",
                ]
            )
        )

    def test_get_repository(self):
        repos = []
        with open(RELEASE, "rb") as stream:
            self.connection.open_stream.return_value = stream
            self.driver.get_repository(
                self.connection,
                ("http://host", "trusty", "main"),
                "x86_64",
                repos.append
            )
        self.connection.open_stream.assert_called_once_with(
            "http://host/dists/trusty/main/binary-amd64/Release"
        )
        self.assertEqual(1, len(repos))
        repo = repos[0]
        self.assertEqual(("trusty", "main"), repo.name)
        self.assertEqual("Ubuntu", repo.origin)
        self.assertEqual("x86_64", repo.architecture)
        self.assertEqual("http://host/", repo.url)

    def test_get_packages(self):
        packages = []
        repo = gen_repository(name=("trusty", "main"), url="http://host/")
        with open(PACKAGES, "rb") as s:
            self.connection.open_stream.return_value = get_compressed(s)
            self.driver.get_packages(
                self.connection,
                repo,
                packages.append
            )

        self.connection.open_stream.assert_called_once_with(
            "http://host/dists/trusty/main/binary-amd64/Packages.gz",
        )
        self.assertEqual(1, len(packages))
        package = packages[0]
        self.assertEqual("test", package.name)
        self.assertEqual("1.1.1-1~u14.04+test", package.version)
        self.assertEqual(100, package.filesize)
        self.assertEqual(
            debian_driver.FileChecksum(
                '1ae09f80109f40dfbfaf3ba423c8625a',
                '402bd18c145ae3b5344edf07f246be159397fd40',
                '14d6e308d8699b7f9ba2fe1ef778c0e3'
                '8cf295614d308039d687b6b097d50859'),
            package.checksum
        )
        self.assertEqual(
            "pool/main/t/test.deb", package.filename
        )
        self.assertTrue(package.mandatory)
        self.assertItemsEqual(
            [
                'test-main (any)',
                'test2 (ge 0.8.16~exp9) | tes2-old (any)',
                'test3 (any)'
            ],
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

    @mock.patch.multiple(
        "packetary.drivers.debian_driver",
        deb822=mock.DEFAULT,
        debfile=mock.DEFAULT,
        fcntl=mock.DEFAULT,
        gzip=mock.DEFAULT,
        utils=mock.DEFAULT,
        os=mock.DEFAULT,
        open=mock.DEFAULT
    )
    def test_rebuild_repository(self, os, debfile, deb822, fcntl,
                                gzip, utils, open):
        repo = gen_repository(name=("trusty", "main"), url="file:///repo")
        package = gen_package(name="test", repository=repo)
        os.path.join = lambda *x: "/".join(x)
        utils.get_path_from_url.return_value = "/root"

        files = [
            mock.MagicMock(),  # Packages, w
            mock.MagicMock(),  # Release, a+b
            mock.MagicMock(),  # Packages, rb
            mock.MagicMock(),  # Release, rb
            mock.MagicMock()   # Packages.gz, rb
        ]
        open.side_effect = files
        self.driver.rebuild_repository(repo, [package])
        open.assert_any_call("/root/Packages", "wb")
        gzip.open.assert_called_once_with("/root/Packages.gz", "wb")
        debfile.DebFile.assert_called_once_with("/root/test.pkg")

    @mock.patch.multiple(
        "packetary.drivers.debian_driver",
        deb822=mock.DEFAULT,
        gzip=mock.DEFAULT,
        open=mock.DEFAULT,
        os=mock.DEFAULT,
        utils=mock.DEFAULT
    )
    def test_clone_repository(self, deb822, gzip, open, os, utils):
        os.path.sep = "/"
        os.path.join = lambda *x: "/".join(x)
        utils.get_path_from_url.return_value = "/root"
        repo = gen_repository(name=("trusty", "main"), url="http://localhost")
        files = [
            mock.MagicMock(),
            mock.MagicMock()
        ]
        open.side_effect = files
        clone = self.driver.clone_repository(self.connection, repo, "/root")
        self.assertEqual(repo.name, clone.name)
        self.assertEqual(repo.architecture, clone.architecture)
        self.assertEqual(repo.origin, clone.origin)
        self.assertEqual("/root/", clone.url)
        utils.get_path_from_url.assert_called_once_with(
            "/root/dists/trusty/main/binary-amd64/"
        )
        utils.ensure_dir_exist.assert_called_once_with("/root")
        open.assert_any_call("/root/Release", "wb")
        open.assert_any_call("/root/Packages", "ab")
        gzip.open.assert_called_once_with("/root/Packages.gz", "ab")
        deb822.Release.return_value.dump.assert_called_once_with(files[0])

    @mock.patch.multiple(
        "packetary.drivers.debian_driver",
        fcntl=mock.DEFAULT,
        gzip=mock.DEFAULT,
        open=mock.DEFAULT,
        os=mock.DEFAULT,
        utils=mock.DEFAULT
    )
    def test_update_suite_index(
            self, os, fcntl, gzip, open, utils):
        repo = gen_repository(name=("trusty", "main"), url="/repo")
        files = [
            mock.MagicMock(),  # Release, a+b
            mock.MagicMock(),  # Packages, rb
            mock.MagicMock(),  # Release, rb
            mock.MagicMock()   # Packages.gz, rb
        ]
        files[0].items.return_value = [
            ("SHA1", "invalid  1  main/binary-amd64/Packages\n"),
            ("Architectures", "i386"),
            ("Components", "restricted"),
        ]
        os.path.join = lambda *x: "/".join(x)
        open.side_effect = files
        utils.get_path_from_url.return_value = "/root"
        utils.append_token_to_string.side_effect = [
            "amd64 i386", "main restricted"
        ]

        utils.get_size_and_checksum_for_files.return_value = (
            (
                "/root/dists/trusty/main/binary-amd64/{0}".format(name),
                10,
                (k + "_value" for k in debian_driver._CHECKSUM_METHODS)
            )
            for name in debian_driver._REPOSITORY_FILES
        )
        self.driver._update_suite_index(repo)
        open.assert_any_call("/root/dists/trusty/Release", "a+b")
        files[0].seek.assert_called_once_with(0)
        files[0].truncate.assert_called_once_with(0)
        files[0].write.assert_any_call(six.b("Architectures: amd64 i386\n"))
        files[0].write.assert_any_call(six.b("Components: main restricted\n"))
        for k in debian_driver._CHECKSUM_METHODS:
            files[0].write.assert_any_call(six.b(
                '{0}:\n'
                ' {1}               10 main/binary-amd64/Packages\n'
                ' {1}               10 main/binary-amd64/Release\n'
                ' {1}               10 main/binary-amd64/Packages.gz\n'
                .format(k, k + "_value")
            ))
        open.assert_any_call("/root/dists/trusty/Release", "a+b")
        print([x.fileno() for x in files])
        fcntl.flock.assert_any_call(files[0].fileno(), fcntl.LOCK_EX)
        fcntl.flock.assert_any_call(files[0].fileno(), fcntl.LOCK_UN)
