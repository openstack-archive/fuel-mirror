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
