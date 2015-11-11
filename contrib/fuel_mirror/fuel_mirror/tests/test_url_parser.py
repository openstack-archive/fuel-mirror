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

from fuel_mirror.common import url_parser
from fuel_mirror.tests import base


class TestUrlParser(base.TestCase):
    def test_get_url_parser(self):
        self.assertIsInstance(
            url_parser.get_url_parser("deb"),
            url_parser.DebUrlParser
        )
        self.assertIsInstance(
            url_parser.get_url_parser("yum"),
            url_parser.YumUrlParser
        )
        with self.assertRaises(KeyError):
            url_parser.get_url_parser("unknown")

    def test_format_url(self):
        parser = url_parser.get_url_parser("deb")
        self.assertEqual(
            "http://localhost/ubuntu trusty main",
            parser.format_url("http://localhost/ubuntu",
                              "{version} main",
                              version="trusty")
        )

    def test_get_urls(self):
        parser = url_parser.get_url_parser("deb")
        self.assertItemsEqual(
            ["http://localhost/ubuntu trusty main"],
            parser.get_urls("http://localhost/ubuntu",
                            ["{version} main"],
                            version="trusty")
        )


class TestDebUrlParser(base.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parser = url_parser.get_url_parser("deb")

    def test_get_name(self):
        self.assertEqual(
            "ubuntu",
            self.parser.get_name("ubuntu", "trusty")
        )

        self.assertEqual(
            "ubuntu-updates",
            self.parser.get_name("ubuntu", "trusty-updates")
        )

    def test_join(self):
        self.assertEqual(
            "http://localhost/ubuntu trusty main restricted",
            self.parser.join(
                "http://localhost/ubuntu",
                "trusty main restricted"
            )
        )

        self.assertEqual(
            "http://localhost/ubuntu trusty main restricted",
            self.parser.join(
                "http://localhost/ubuntu  ",
                "trusty main restricted"
            )
        )

    def test_get_repo_config(self):
        self.assertEqual(
            {
                "name": "ubuntu-updates",
                "suite": "trusty-updates",
                "section": "main restricted",
                "type": "deb",
                "uri": "http://localhost/ubuntu"
            },
            self.parser.get_repo_config(
                "ubuntu",
                "http://localhost/ubuntu trusty-updates main restricted"
            )
        )


class TestYumUrlParser(base.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parser = url_parser.get_url_parser("yum")

    def test_join(self):
        self.assertEqual(
            "http://localhost/centos/os",
            self.parser.join("http://localhost/centos", "os")
        )
        self.assertEqual(
            "http://localhost/centos/os",
            self.parser.join("http://localhost/centos/", "os")
        )

    def test_get_repo_config(self):
        self.assertEqual(
            {
                "name": "centos",
                "type": "rpm",
                "uri": "http://localhost/centos/os"
            },
            self.parser.get_repo_config(
                "centos",
                "http://localhost/centos/os"
            )
        )
        self.assertEqual(
            {
                "name": "centos-updates",
                "type": "rpm",
                "uri": "http://localhost/centos/updates"
            },
            self.parser.get_repo_config(
                "centos",
                "http://localhost/centos/updates"
            )
        )
