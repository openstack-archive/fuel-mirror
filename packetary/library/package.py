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

import abc
import collections
import operator
import six


@six.add_metaclass(abc.ABCMeta)
class Package(object):
    """Structure to describe package object."""

    @property
    @abc.abstractmethod
    def name(self):
        """The package`s name."""

    @property
    @abc.abstractmethod
    def version(self):
        """The package`s version."""

    @property
    @abc.abstractmethod
    def size(self):
        """The package`s size in bytes."""

    @property
    @abc.abstractmethod
    def filename(self):
        """The package`s relative path."""

    @property
    @abc.abstractmethod
    def origin(self):
        """The url of origin repository."""

    @property
    @abc.abstractmethod
    def checksum(self):
        """The package`s checksum.

        :return: tuple(algorithm, checksum).
        """

    @property
    @abc.abstractmethod
    def requires(self):
        """The list of packages(name, version), that requires by packages."""

    @property
    @abc.abstractmethod
    def provides(self):
        """The list of relations, that provides by package."""

    @property
    @abc.abstractmethod
    def obsoletes(self):
        """The list of packages(name, version), that replaces by package."""

    def __hash__(self):
        return hash((self.name, self.version))

    def __cmp__(self, other):
        if self.name < other.name:
            return -1
        if self.name > other.name:
            return 1
        if self.version < other.version:
            return -1
        if self.version > other.version:
            return 1
        return 0

    def __lt__(self, other):
        return self.__cmp__(other) < 0

    def __le__(self, other):
        return self.__cmp__(other) <= 0

    def __gt__(self, other):
        return self.__cmp__(other) > 0

    def __ge__(self, other):
        return self.__cmp__(other) >= 0

    def __eq__(self, other):
        return self.__cmp__(other) == 0


_RelationBase = collections.namedtuple(
    "Relation", ("package", "version", "choice")
)


_VersionRangeBase = collections.namedtuple(
    "_VersionRangeBase", ("opname", "value")
)


class VersionRange(_VersionRangeBase):
    """Describes version in package`s relation."""

    def __new__(cls, opname=None, value=None):
        if isinstance(opname, (list, tuple)):
            if len(opname) > 1:
                value = opname[1]
                opname = opname[0]
            else:
                opname = opname[0]

        return _VersionRangeBase.__new__(cls, opname, value)

    def __str__(self):
        if self.value is not None:
            return "%s %s" % (self.opname, self.value)
        return "any"

    def has_intersection(self, other):
        if not isinstance(other, VersionRange):
            raise TypeError(
                "Unordered type <type 'VersionRelation'> and %s" % type(other)
            )

        if self.opname is None or other.opname is None:
            return True

        op1 = getattr(operator, self.opname)
        op2 = getattr(operator, other.opname)
        if self.opname[0] == other.opname[0]:
            if self.opname[0] == 'l':
                if self.value < other.value:
                    return op1(self.value, other.value)
                return op2(other.value, self.value)
            elif self.opname[0] == 'g':
                if self.value > other.value:
                    return op1(self.value, other.value)
                return op2(other.value, self.value)

        if self.opname == 'eq':
            return op2(self.value, other.value)

        if other.opname == 'eq':
            return op1(other.value, self.value)

        return (
            op1(other.value, self.value) and
            op2(self.value, other.value)
        )


class Relation(_RelationBase):
    """Describes the package`s relation."""

    def __new__(cls, package, version, choice=None):
        return _RelationBase.__new__(cls, package, version, choice)

    def __str__(self):
        if self.choice:
            return "%s (%s) | %s" % (self.package, self.version, self.choice)
        return "%s (%s)" % (self.package, self.version)
