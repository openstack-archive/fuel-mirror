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

import operator


class VersionRange(object):
    """Describes the range of versions.

    Range of version is compare operation and edge.
    the compare operation can be one of:
    equal, greater, less, greater or equal, less or equal.
    """

    __slots__ = ["op", "edge"]

    def __init__(self, op=None, edge=None):
        """Initialises.

        :param op: the name of operator to compare.
        :param edge: the edge of versions.
        """
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
            return "{0} {1}".format(self.op, self.edge)
        return "any"

    def __unicode__(self):
        if self.edge is not None:
            return u"{0} {1}".format(self.op, self.edge)
        return u"any"

    def has_intersection(self, other):
        """Checks that 2 ranges has intersection."""

        if not isinstance(other, VersionRange):
            raise TypeError(
                "Unorderable type <type 'VersionRange'> and {0}"
                .format(type(other))
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

    __slots__ = ["name", "version", "alternative"]

    def __init__(self, name, version=None, alternative=None):
        """Initialises.

        :param name: the name of required package
        :param version: the version range of required package
        :param alternative: the alternative relation
        """
        self.name = name
        self.version = VersionRange() if version is None else version
        self.alternative = alternative

    @classmethod
    def from_args(cls, *args):
        """Construct relation from list of arguments.

        :param args: the list of tuples(name, [version_op, version_edge])
        """
        if len(args) == 0:
            return None

        head = args[0]
        name = head[0]
        version = VersionRange(*head[1:])
        alternative = cls.from_args(*args[1:])
        return cls(name, version, alternative)

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
            return "{0} ({1})".format(self.name, self.version)
        return "{0} ({1}) | {2}".format(
            self.name, self.version, self.alternative
        )

    def __unicode__(self):
        if self.alternative is None:
            return u"{0} ({1})".format(self.name, self.version)
        return u"{0} ({1}) | {2}".format(
            self.name, self.version, self.alternative
        )
