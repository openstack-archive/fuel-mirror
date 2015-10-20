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


class VersionRange(object):
    """Describes the range of versions.

    Range of version is compare operation and edge.
    the compare operation can be one of:
    equal, greater, less, greater or equal, less or equal.
    """
    def __init__(self, op=None, edge=None):
        """Initialises.

        :param op: the name of operator to compare.
        :param edge: the edge of versions.
        """
        if isinstance(op, (list, tuple)):
            if len(op) > 1:
                edge = op[1]
            op = op[0]
        self.op = op
        self.edge = edge

    def __hash__(self):
        return hash((self.op, self.edge))

    def __eq__(self, other):
        if not isinstance(other, VersionRange):
            return False

        return self.op == other.op and \
            self.edge == other.edge

    def __str__(self):
        if self.edge is not None:
            return "%s %s" % (self.op, self.edge)
        return "any"

    def __unicode__(self):
        if self.edge is not None:
            return u"%s %s" % (self.op, self.edge)
        return u"any"

    def has_intersection(self, other):
        """Checks that 2 ranges has intersection."""

        if not isinstance(other, VersionRange):
            raise TypeError(
                "Unorderable type <type 'VersionRange'> and %s" % type(other)
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


class PackageRelation(object):
    """Describes the package`s relation.

    Relation includes the name of required package
    and range of versions that satisfies requirement.
    """

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

    def __hash__(self):
        return hash((self.name, self.version))

    def __eq__(self, other):
        if not isinstance(other, PackageRelation):
            return False

        return self.name == other.name and \
            self.version == other.version

    def __str__(self):
        if self.alternative is None:
            return "%s (%s)" % (self.name, self.version)
        return "%s (%s) | %s" % (self.name, self.version, self.alternative)

    def __unicode__(self):
        if self.alternative is None:
            return u"%s (%s)" % (self.name, self.version)
        return u"%s (%s) | %s" % (self.name, self.version, self.alternative)
