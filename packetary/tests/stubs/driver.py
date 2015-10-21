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

from packetary.library import driver
from packetary.tests.stubs import package


class RepoDriver(driver.RepoDriver):
    def __init__(self, *_):
        self.packages = None
        self.index_writer = mock.MagicMock()

    def generate_packages(self, count=1, **kwargs):
        packages = []
        for i in six.moves.range(count):
            requires = [
                package.Relation(
                    "package{0}_r".format(i), package.VersionRange())
            ]
            obsoletes = [
                package.Relation(
                    "package{0}_o".format(i), package.VersionRange("le", 2))
            ]
            provides = [
                package.Relation(
                    "package{0}_p".format(i), package.VersionRange("gt", 1))
            ]
            packages.append(package.Package(
                name="package%d" % i,
                requires=requires,
                obsoletes=obsoletes,
                provides=provides,
                **kwargs
            ))

        self.packages = packages

    def parse_urls(self, urls):
        for url in urls:
            yield url, "test"

    def get_path(self, base, p):
        return "/".join((base or p.baseurl, p.filename))

    def create_index(self, destination):
        return self.index_writer

    def load(self, baseurl, reponame, consumer):
        if self.packages is None:
            self.generate_packages(baseurl=baseurl)
        for p in self.packages:
            consumer(p)
