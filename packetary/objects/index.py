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

from bintrees import FastRBTree
from collections import defaultdict
import functools
import operator
import six


def _make_operator(direction, op):
    """Makes search operator from low-level operation and search direction."""
    return functools.partial(direction, condition=op)


def _start_upperbound(versions, version, condition):
    """Gets all versions from [start, version] that meet condition.

    :param versions: the tree of versions.
    :param version: the required version
    :param condition: condition for search
    :return: the list of found versions
    """

    result = list(versions.value_slice(None, version))
    try:
        bound = versions.ceiling_item(version)
        if condition(bound[0], version):
            result.append(bound[1])
    except KeyError:
        pass
    return result


def _lowerbound_end(versions, version, condition):
    """Gets all versions from [version, end] that meet condition.

    :param versions: the tree of versions.
    :param version: the required version
    :param condition: condition for search
    :return: the list of found versions
    """
    result = []
    items = iter(versions.item_slice(version, None))
    bound = next(items, None)
    if bound is None:
        return result
    if condition(bound[0], version):
        result.append(bound[1])
    result.extend(x[1] for x in items)
    return result


def _equal(tree, version):
    """Gets the package with specified version."""
    if version in tree:
        return [tree[version]]
    return []


def _any(tree, _):
    """Gets the package with max version."""
    return list(tree.values())


class Index(object):
    """The search index for packages.

    Builds three search-indexes:
    - index of packages with versions.
    - index of virtual packages (provides).
    - index of obsoleted packages (obsoletes).

    Uses to find package by name and range of versions.
    """

    operators = {
        None: _any,
        "lt": _make_operator(_start_upperbound, operator.lt),
        "le": _make_operator(_start_upperbound, operator.le),
        "gt": _make_operator(_lowerbound_end, operator.gt),
        "ge": _make_operator(_lowerbound_end, operator.ge),
        "eq": _equal,
    }

    def __init__(self):
        self.packages = defaultdict(FastRBTree)
        self.obsoletes = defaultdict(FastRBTree)
        self.provides = defaultdict(FastRBTree)

    def __iter__(self):
        """Iterates over all packages including versions."""
        return self.get_all()

    def __len__(self, _reduce=six.functools.reduce):
        """Returns the total number of packages with versions."""
        return _reduce(
            lambda x, y: x + len(y),
            six.itervalues(self.packages),
            0
        )

    def get_all(self):
        """Gets sequence from all of packages including versions."""

        for versions in six.itervalues(self.packages):
            for version in versions.values():
                yield version

    def find(self, name, version):
        """Finds the package by name and range of versions.

        :param name: the package`s name.
        :param version: the range of versions.
        :return: the package if it is found, otherwise None
        """
        candidates = self.find_all(name, version)
        if len(candidates) > 0:
            return candidates[-1]
        return None

    def find_all(self, name, version):
        """Finds the packages by name and range of versions.

        :param name: the package`s name.
        :param version: the range of versions.
        :return: the list of suitable packages
        """

        if name in self.packages:
            candidates = self._find_versions(
                self.packages[name], version
            )
            if len(candidates) > 0:
                return candidates

        if name in self.obsoletes:
            return self._resolve_relation(
                self.obsoletes[name], version
            )

        if name in self.provides:
            return self._resolve_relation(
                self.provides[name], version
            )
        return []

    def add(self, package):
        """Adds new package to indexes.

        :param package: the package object.
        """
        self.packages[package.name][package.version] = package
        key = package.name, package.version

        for obsolete in package.obsoletes:
            self.obsoletes[obsolete.name][key] = obsolete

        for provide in package.provides:
            self.provides[provide.name][key] = provide

    def _resolve_relation(self, relations, version):
        """Resolve relation according to relations index.

        :param relations: the index of relations
        :param version: the range of versions
        :return: package if found, otherwise None
        """
        for key, candidate in relations.iter_items(reverse=True):
            if candidate.version.has_intersection(version):
                return [self.packages[key[0]][key[1]]]
        return []

    @staticmethod
    def _find_versions(versions, version):
        """Searches accurate version.

        Search for the highest version out of intersection
        of existing and required range of versions.

        :param versions: the existing versions
        :param version: the required range of versions
        :return: package if found, otherwise None
        """

        try:
            op = Index.operators[version.op]
        except KeyError:
            raise ValueError(
                "Unsupported operation: {0}"
                .format(version.op)
            )
        return op(versions, version.edge)
