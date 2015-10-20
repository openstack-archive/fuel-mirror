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

from packetary.objects.base import ComparableObject


class PackageVersion(ComparableObject):
    """The Package version."""

    __slots__ = ["epoch", "version", "release"]

    def __init__(self, epoch, version, release):
        self.epoch = int(epoch)
        self.version = tuple(version)
        self.release = tuple(release)

    @classmethod
    def from_string(cls, text):
        """Constructs from string.

        :param text: the version in format '[{epoch-}]-{version}-{release}'
        """
        components = text.split("-")
        if len(components) > 2:
            epoch = components[0]
            components = components[1:]
        else:
            epoch = 0
        return cls(epoch, components[0].split("."), components[1].split("."))

    def cmp(self, other):
        if not isinstance(other, PackageVersion):
            other = PackageVersion.from_string(str(other))

        if not isinstance(other, PackageVersion):
            raise TypeError
        if self.epoch < other.epoch:
            return -1
        if self.epoch > other.epoch:
            return 1

        res = self._cmp_version_part(self.version, other.version)
        if res != 0:
            return res
        return self._cmp_version_part(self.release, other.release)

    def __eq__(self, other):
        if other is self:
            return True
        return self.cmp(other) == 0

    def __str__(self):
        return "{0}-{1}-{2}".format(
            self.epoch,
            ".".join(str(x) for x in self.version),
            ".".join(str(x) for x in self.release)
        )

    @classmethod
    def _order(cls, x):
        """Return an integer value for character x"""
        if x.isdigit():
            return int(x) + 1
        if x.isalpha():
            return ord(x)
        return ord(x) + 256

    @classmethod
    def _cmp_version_string(cls, version1, version2):
        """Compares two versions as string."""
        la = [cls._order(x) for x in version1]
        lb = [cls._order(x) for x in version2]
        while la or lb:
            a = 0
            b = 0
            if la:
                a = la.pop(0)
            if lb:
                b = lb.pop(0)
            if a < b:
                return -1
            elif a > b:
                return 1
        return 0

    @classmethod
    def _cmp_version_part(cls, version1, version2):
        """Compares two versions."""
        ver1_it = iter(version1)
        ver2_it = iter(version2)
        while True:
            v1 = next(ver1_it, None)
            v2 = next(ver2_it, None)

            if v1 is None or v2 is None:
                if v1 is not None:
                    return 1
                if v2 is not None:
                    return -1
                return 0

            if v1.isdigit() and v2.isdigit():
                a = int(v1)
                b = int(v2)
                if a < b:
                    return -1
                if a > b:
                    return 1
            else:
                r = cls._cmp_version_string(v1, v2)
                if r != 0:
                    return r
