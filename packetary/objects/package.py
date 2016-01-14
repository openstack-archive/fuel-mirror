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
