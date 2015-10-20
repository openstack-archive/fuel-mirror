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

from collections import namedtuple

from packetary.objects.base import ComparableObject


FileChecksum = namedtuple("FileChecksum", ("md5", "sha1", "sha256"))


class Package(ComparableObject):
    """Structure to describe package object."""

    def __init__(self, repository, name, version, filename,
                 filesize, checksum, mandatory=False,
                 requires=None, provides=None, obsoletes=None):
        """Initialises.

        :param name: the package`s name
        :param version: the package`s version
        :param filename: the package`s relative filename
        :param filesize: the package`s file size
        :param checksum: the package`s checksum
        :param requires: the package`s requirements(optional)
        :param provides: the package`s provides(optional)
        :param obsoletes: the package`s obsoletes(optional)
        :param mandatory: indicates that package is mandatory
        """

        self.repository = repository
        self.name = name
        self.version = version
        self.filename = filename
        self.checksum = checksum
        self.filesize = filesize
        self.requires = requires or []
        self.provides = provides or []
        self.obsoletes = obsoletes or []
        self.mandatory = mandatory

    def __copy__(self):
        """Creates shallow copy of package."""
        return Package(**self.__dict__)

    def __str__(self):
        return "{0} {1}".format(self.name, self.version)

    def __unicode__(self):
        return u"{0} {1}".format(self.name, self.version)

    def __hash__(self):
        return hash((self.name, self.version))

    def cmp(self, other):
        """Compares with other Package object."""
        if self.name < other.name:
            return -1
        if self.name > other.name:
            return 1
        if self.version < other.version:
            return -1
        if self.version > other.version:
            return 1
        return 0
