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

from fuel_mirror.common import url_builder
from fuel_mirror.tests import base


class TestUrlBuilder(base.TestCase):
    def test_get_url_builder(self):
        self.assertIsInstance(
            url_builder.get_url_builder("deb"),
            url_builder.AptRepoUrlBuilder
        )
        self.assertIsInstance(
            url_builder.get_url_builder("rpm"),
            url_builder.YumRepoUrlBuilder
        )
        with self.assertRaises(KeyError):
            url_builder.get_url_builder("unknown")

    def test_format_url(self):
        builder = url_builder.get_url_builder("deb")
        self.assertEqual(
            "http://localhost/ubuntu trusty main",
            builder.format_url("http://localhost/ubuntu",
                               "{version} main",
                               version="trusty")
        )

    def test_get_urls(self):
        builder = url_builder.get_url_builder("deb")
        self.assertItemsEqual(
            ["http://localhost/ubuntu trusty main"],
            builder.get_urls("http://localhost/ubuntu",
                             ["{version} main"],
                             version="trusty")
        )


class TestAptUrlBuilder(base.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.builder = url_builder.get_url_builder("deb")

    def test_get_name(self):
        self.assertEqual(
            "ubuntu",
            self.builder.get_name("ubuntu", "trusty")
        )

        self.assertEqual(
            "ubuntu-updates",
            self.builder.get_name("ubuntu", "trusty-updates")
        )

    def test_join(self):
        self.assertEqual(
            "http://localhost/ubuntu trusty main restricted",
            self.builder.join(
                "http://localhost/ubuntu",
                "trusty main restricted"
            )
        )

        self.assertEqual(
            "http://localhost/ubuntu trusty main restricted",
            self.builder.join(
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
            self.builder.get_repo_config(
                "ubuntu",
                "http://localhost/ubuntu trusty-updates main restricted"
            )
        )


class TestYumUrlBuilder(base.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.builder = url_builder.get_url_builder("rpm")

    def test_join(self):
        self.assertEqual(
            "http://localhost/centos/os",
            self.builder.join("http://localhost/centos", "os")
        )
        self.assertEqual(
            "http://localhost/centos/os",
            self.builder.join("http://localhost/centos/", "os")
        )

    def test_get_repo_config(self):
        self.assertEqual(
            {
                "name": "centos",
                "type": "rpm",
                "uri": "http://localhost/centos/os"
            },
            self.builder.get_repo_config(
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
            self.builder.get_repo_config(
                "centos",
                "http://localhost/centos/updates"
            )
        )
