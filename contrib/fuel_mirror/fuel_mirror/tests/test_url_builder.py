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
        self.assertTrue(issubclass(
            url_builder.get_url_builder("deb"),
            url_builder.AptRepoUrlBuilder
        ))
        self.assertTrue(issubclass(
            url_builder.get_url_builder("rpm"),
            url_builder.YumRepoUrlBuilder
        ))
        with self.assertRaises(KeyError):
            url_builder.get_url_builder("unknown")


class TestAptUrlBuilder(base.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.builder = url_builder.get_url_builder("deb")
        cls.repo_data = {
            "name": "ubuntu",
            "suite": "trusty",
            "section": "main restricted",
            "type": "deb",
            "uri": "http://localhost/ubuntu"
        }

    def test_get_repo_url(self):
        self.assertEqual(
            "http://localhost/ubuntu trusty main restricted",
            self.builder.get_repo_url(self.repo_data)
        )


class TestYumUrlBuilder(base.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.builder = url_builder.get_url_builder("rpm")
        cls.repo_data = {
            "name": "centos",
            "type": "rpm",
            "uri": "http://localhost/os/x86_64"
        }

    def test_get_repo_url(self):
        self.assertEqual(
            "http://localhost/os/x86_64",
            self.builder.get_repo_url(self.repo_data)
        )
