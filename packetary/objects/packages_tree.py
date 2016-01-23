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

import warnings

from packetary.objects.index import Index


class UnresolvedWarning(UserWarning):
    """Warning about unresolved depends."""
    pass


class PackagesTree(Index):
    """Helper class to deal with dependency graph."""

    def __init__(self):
        super(PackagesTree, self).__init__()
        self.mandatory_packages = []

    def add(self, package):
        super(PackagesTree, self).add(package)
        # store all mandatory packages in separated list for quick access
        if package.mandatory:
            self.mandatory_packages.append(package)

    def get_unresolved_dependencies(self, base=None):
        """Gets the set of unresolved dependencies.

        :param base: the base index to resolve dependencies
        :return: the set of unresolved depends.
        """
        external = self.__get_unresolved_dependencies(self)
        if base is None:
            return external

        unresolved = set()
        for relation in external:
            for rel in relation:
                if base.find(rel.name, rel.version) is not None:
                    break
            else:
                unresolved.add(relation)
        return unresolved

    def get_minimal_subset(self, main, requirements):
        """Gets the minimal work subset.

        :param main: the main index, to complete requirements.
        :param requirements: additional requirements.
        :return: The set of resolved depends.
        """

        unresolved = set()
        resolved = set()
        if main is None:
            def pkg_filter(*_):
                pass
        else:
            pkg_filter = main.find
            self.__get_unresolved_dependencies(main, requirements)

        stack = list()
        stack.append(requirements)

        # add all mandatory packages
        for pkg in self.mandatory_packages:
            resolved.add(pkg)
            stack.append(pkg.requires)

        while len(stack) > 0:
            required = stack.pop()
            for require in required:
                for rel in require:
                    if rel not in unresolved:
                        if pkg_filter(rel.name, rel.version) is not None:
                            break
                        # use all packages that meets depends
                        candidates = self.find_all(rel.name, rel.version)
                        for cand in candidates:
                            if cand not in resolved:
                                resolved.add(cand)
                                stack.append(cand.requires)
                        if len(candidates) > 0:
                            break
                else:
                    unresolved.add(require)
                    msg = "Unresolved depends: {0}".format(require)
                    warnings.warn(UnresolvedWarning(msg))

        return resolved

    @staticmethod
    def __get_unresolved_dependencies(index, unresolved=None):
        """Gets the set of unresolved dependencies.

        :param index: the search index.
        :param unresolved: the known list of unresolved packages.
        :return: the set of unresolved depends.
        """

        if unresolved is None:
            unresolved = set()

        for pkg in index:
            for require in pkg.requires:
                for rel in require:
                    if rel not in unresolved:
                        candidate = index.find(rel.name, rel.version)
                        if candidate is not None and candidate != pkg:
                            break
                else:
                    unresolved.add(require)
        return unresolved
