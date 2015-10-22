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

from debian import debian_support

from packetary.library.package import Package
from packetary.library.package import Relation
from packetary.library.package import VersionRange


_OPERATORS_MAPPING = {
    '>>': 'gt',
    '<<': 'lt',
    '=': 'eq',
    '>=': 'ge',
    '<=': 'le',
}


def _get_version_range(rel_version):
    if rel_version is None:
        return VersionRange()
    return VersionRange(
        _OPERATORS_MAPPING[rel_version[0]],
        rel_version[1],
    )


class DebPackage(Package):
    """Debian package."""

    def __init__(self, dpkg, baseurl, suite, comp):
        self.dpkg = dpkg
        self.suite = suite
        self.comp = comp
        self._baseurl = baseurl
        self._version = debian_support.Version(dpkg['version'])
        self._size = int(dpkg['size'])

    @property
    def name(self):
        return self.dpkg['package']

    @property
    def version(self):
        return self._version

    @property
    def size(self):
        return self._size

    @property
    def checksum(self):
        if 'sha1' in self.dpkg:
            return 'sha1', self.dpkg['sha1']
        if 'MD5sum' in self.dpkg:
            return 'md5', self.dpkg['MD5sum']
        return None, None

    @property
    def filename(self):
        return self.dpkg["Filename"]

    @property
    def baseurl(self):
        return self._baseurl

    @property
    def requires(self):
        return self._get_relations('depends') + \
            self._get_relations('pre-depends')

    @property
    def provides(self):
        return self._get_relations('provides')

    @property
    def obsoletes(self):
        return self._get_relations('replaces')

    def _get_relations(self, name):
        if hasattr(self, '_' + name):
            return getattr(self, '_' + name)

        relations = list()
        for variants in self.dpkg.relations[name]:
            choice = None
            for v in reversed(variants):
                choice = Relation(
                    v['name'],
                    _get_version_range(v.get('version')),
                    choice
                )

            if choice is not None:
                relations.append(choice)

        setattr(self, '_' + name, relations)
        return relations
