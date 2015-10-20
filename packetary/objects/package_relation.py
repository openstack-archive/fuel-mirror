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

import operator

from packetary.objects.base import PlainObject


class VersionRange(PlainObject):
    def __init__(self, op=None, edge=None):
        if isinstance(op, (list, tuple)):
            if len(op) > 1:
                edge = op[1]
            op = op[0]
        self.op = op
        self.edge = edge

    def __hash__(self):
        return hash((self.op, self.edge))

    def __str__(self):
        if self.edge is not None:
            return "%s %s" % (self.op, self.edge)
        return "any"

    def __unicode__(self):
        if self.edge is not None:
            return u"%s %s" % (self.op, self.edge)
        return u"any"

    def __cmp__(self, other):
        if self.op is None:
            if other.op is None:
                return 0
            return -1
        if other.op is None:
            return 1
        if self.op < other.op:
            return -1
        if self.op > other.op:
            return 1
        if self.edge < other.edge:
            return -1
        if self.edge > other.edge:
            return 1
        return 0

    def has_intersection(self, other):
        if not isinstance(other, VersionRange):
            raise TypeError(
                "Unordered type <type 'VersionRelation'> and %s" % type(other)
            )

        if self.op is None or other.op is None:
            return True

        my_op = getattr(operator, self.op)
        other_op = getattr(operator, other.op)
        if self.op[0] == other.op[0]:
            if self.op[0] == 'l':
                if self.edge < other.edge:
                    return my_op(self.edge, other.edge)
                return other_op(other.edge, self.edge)
            elif self.op[0] == 'g':
                if self.edge > other.edge:
                    return my_op(self.edge, other.edge)
                return other_op(other.edge, self.edge)

        if self.op == 'eq':
            return other_op(self.edge, other.edge)

        if other.op == 'eq':
            return my_op(other.edge, self.edge)

        return (
            my_op(other.edge, self.edge) and
            other_op(self.edge, other.edge)
        )


class PackageRelation(PlainObject):
    """Describes the package`s relation."""
    def __init__(self, name, version=None, alternative=None):
        """Initialises.

        :param name: the name of required package
        :param version: the version range of required package
        :param alternative: the alternative relation
        """
        if isinstance(name, (list, tuple)):
            if len(name) > 1:
                version = VersionRange(name[1:3])
            if len(name) > 3:
                alternative = PackageRelation(name[3:])
            name = name[0]
        if version is None:
            version = VersionRange()

        self.name = name
        self.version = version
        self.alternative = alternative

    def __iter__(self):
        """Iterates over alternatives."""
        r = self
        while r is not None:
            yield r
            r = r.alternative

    def __str__(self):
        if self.alternative is None:
            return "%s (%s)" % (self.name, self.version)
        return "%s (%s) | %s" % (self.name, self.version, self.alternative)

    def __unicode__(self):
        if self.alternative is None:
            return u"%s (%s)" % (self.name, self.version)
        return u"%s (%s) | %s" % (self.name, self.version, self.alternative)

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
