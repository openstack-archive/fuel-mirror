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
import six


from packetary.library.drivers import deb_driver
from packetary.library.package import Relation
from packetary.tests import base
from packetary.tests.stubs.context import Context


PACKAGES_GZ = path.join(path.dirname(__file__), "data", "packages.gz")


class TestDebDriver(base.TestCase):
    @classmethod
    def setUpClass(cls):
        super(TestDebDriver, cls).setUpClass()
        cls.driver = deb_driver.Driver(
            Context(),
            "x86_64"
        )

    def test_get_path(self):
        package = mock.MagicMock()
        package.baseurl = "."
        package.filename = "test.dpkg"
        self.assertEqual(
            "dir/test.dpkg",
            self.driver.get_path("dir", package)
        )
        self.assertEqual(
            "./test.dpkg",
            self.driver.get_path(None, package)
        )

    def test_load(self):
        packages = []
        connection = self.driver.connections.connection
        with open(PACKAGES_GZ, "rb") as stream:
            connection.open_stream.return_value = stream
            self.driver.load(
                "http://host", ("trusty", "main"), packages.append
            )

        connection.open_stream.assert_called_once_with(
            "http://host/dists/trusty/main/binary-amd64/Packages.gz",
        )
        self.assertEqual(1, len(packages))
        package = packages[0]
        self.assertEqual("test", package.name)
        self.assertEqual("1.1.1-1~u14.04+test", package.version)
        self.assertEqual(100, package.size)
        self.assertEqual(
            ("sha1", "402bd18c145ae3b5344edf07f246be159397fd40"),
            packages[0].checksum
        )
        self.assertEqual(
            "pool/main/t/test.deb", package.filename
        )
        self.assertItemsEqual(
            [Relation(['test2', 'ge', '0.8.16~exp9', 'tes2-old']),
             Relation('test3'),
             Relation('test-main')],
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
                ("http://host", ("trusty", "main")),
                ("http://host", ("trusty", "restricted")),
            ],
            self.driver.parse_urls(
                ["http://host/dists/ trusty main restricted"]
            )
        )
        self.assertItemsEqual(
            [("http://host", ("trusty", "main"))],
            self.driver.parse_urls(
                ["http://host/dists trusty main"]
            )
        )
        self.assertItemsEqual(
            [("http://host", ("trusty", "main"))],
            self.driver.parse_urls(
                ["http://host/ trusty main"]
            )
        )
        self.assertItemsEqual(
            [
                ("http://host", ("trusty", "main")),
                ("http://host2", ("trusty", "main")),
            ],
            self.driver.parse_urls(
                [
                    "http://host/ trusty main",
                    "http://host2/dists/ trusty main",
                ]
            )
        )

    def test_parse_urls_fail_if_invalid(self):
        with self.assertRaisesRegexp(ValueError, "Invalid url:"):
            next(self.driver.parse_urls(["http://host/dists/trusty main"]))
        with self.assertRaisesRegexp(ValueError, "Invalid url:"):
            next(self.driver.parse_urls(["http://host/dists trusty,main"]))


@mock.patch.multiple(
    "packetary.library.drivers.deb_driver",
    os=mock.DEFAULT,
    gzip=mock.DEFAULT,
    open=mock.DEFAULT,
    fcntl=mock.DEFAULT,
)
class TestDebIndexWriter(base.TestCase):
    def setUp(self):
        super(TestDebIndexWriter, self).setUp()
        driver = mock.MagicMock()
        driver.arch = "x86_64"
        self.writer = deb_driver.DebIndexWriter(
            driver,
            "/root"
        )

    def test_add(self, **_):
        package = mock.MagicMock(suite="trusty", comp="main")
        package.dpkg.get.return_value = None
        self.writer.add(package)
        package.dpkg.get.return_value = 'test'
        self.writer.add(package)
        package.dpkg.get.return_value = 'unknown'
        self.writer.add(package)
        self.assertEqual("test", self.writer.origin)

    def test_commit(self, gzip, open, os, fcntl):
        package = mock.MagicMock(suite="trusty", comp="main")
        package.dpkg.get.return_value = "Test"
        self.writer.add(package)
        os.path.join = path.join
        os.path.exists.return_value = True
        self.writer.commit(True)
        open.assert_any_call(
            "/root/dists/trusty/main/binary-x86_64/Packages", "wb"
        )
        open.assert_any_call(
            "/root/dists/trusty/main/binary-x86_64/Release", "w"
        )
        open.assert_any_call(
            "/root/dists/trusty/Release", "w"
        )
        gzip.open.assert_any_call(
            "/root/dists/trusty/main/binary-x86_64/Packages.gz", "wb"
        )
        self.writer.driver.load.assert_called_with(
            "/root", ("trusty", "main"), mock.ANY
        )
        fcntl.flock.assert_any_call(mock.ANY, fcntl.LOCK_EX)
        fcntl.flock.assert_any_call(mock.ANY, fcntl.LOCK_UN)

    def test_commit_with_cleanup(self, os, **_):
        self.writer.driver.load = \
            lambda *x: x[-1](mock.MagicMock(filename="test.pkg"))
        self.writer.driver.get_path.return_value = "/root/test.pkg"
        os.path.join = path.join
        os.path.exists.return_value = True

        package = mock.MagicMock(suite="trusty", comp="main")
        package.dpkg.get.return_value = "Test"
        self.writer.add(package)
        self.writer.commit(False)

        os.remove.assert_called_once_with("/root/test.pkg")

    def test_updates_global_releases(self, os, open, **_):
        os.path.join = path.join
        os.listdir.return_value = ["main"]
        os.walk.return_value = [(
            "/root/dists/trusty/main",
            [],
            ["Release", "Packages", "Packages.gz", "test.pkg"]
        )]
        os.path.isdir.return_value = True
        os.fstat.side_effect = [
            mock.MagicMock(st_size=1),
            mock.MagicMock(st_size=10),
            mock.MagicMock(st_size=10000000000000000),
        ]

        meta_stream = six.StringIO()
        open.return_value = mock.MagicMock(write=meta_stream.write)
        open.return_value.read.side_effect = [
            b"f1", "",
            b"f2", "",
            b"f3", "",
        ]
        self.writer.origin = "test"
        self.writer._updates_global_releases(["trusty"])

        content = meta_stream.getvalue()
        start = content.find("Components:")
        self.assertNotEqual(-1, start)
        end = content.find("\n", start)
        self.assertEqual(
            "Components: main", content[start:end]
        )

        files = [
            ("10", "Packages"),
            ("1", "Release"),
            ("10000000000000000", "Packages.gz"),
        ]

        for h in ("MD5Sum:", "SHA1", "SHA256"):
            start = content.find(h, end + 1)
            self.assertNotEqual(-1, start)
            start += len(h) + 1
            for size, name in files:
                end = content.find("\n", start + 1)
                expected = "{0}{1} main/{2}".format(
                    " " * (deb_driver._SIZE_ALIGNMENT - len(size)),
                    size,
                    name
                )
                self.assertTrue(
                    content[start:end].endswith(expected)
                )
                start = end + 1
