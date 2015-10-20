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

    def cmp(self, other):
        if not isinstance(other, PackageVersion):
            other = PackageVersion.from_string(str(other))

        if not isinstance(other, PackageVersion):
            raise TypeError
        if self.epoch < other.epoch:
            return -1
        if self.epoch > other.epoch:
            return 1
        if self.version < other.version:
            return -1
        if self.version > other.version:
            return 1
        if self.release < other.release:
            return -1
        if self.release > other.release:
            return 1
        return 0

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
