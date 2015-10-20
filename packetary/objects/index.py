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


from bintrees import FastRBTree
from collections import defaultdict
import functools
import operator
import six


def _make_operator(direction, op):
    """Makes search operator from low-level operation and search direction."""
    return functools.partial(direction, condition=op)


def _top_down(tree, version, condition):
    """Finds first package from top to down that satisfies condition."""
    result = []
    try:
        bound = tree.ceiling_item(version)
        if bound[0] == version and condition(bound[0], version):
            result.append(bound[1])
        upper = bound[0]
    except KeyError:
        upper = version

    for item in tree.item_slice(None, upper, reverse=True):
        if not condition(item[0], version):
            break
        result.append(item[1])

    result.reverse()
    return result


def _down_up(self, version, condition):
    """Finds first package from down to up that satisfies condition."""
    result = []
    items = iter(self.item_slice(version, None))
    bound = next(items, None)
    if bound is None:
        return result
    if condition(bound[0], version):
        result.append(bound[1])

    for item in items:
        if not condition(item[0], version):
            break
        result.append(item[1])

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
        "lt": _make_operator(_top_down, operator.lt),
        "le": _make_operator(_top_down, operator.le),
        "gt": _make_operator(_down_up, operator.gt),
        "ge": _make_operator(_down_up, operator.ge),
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
