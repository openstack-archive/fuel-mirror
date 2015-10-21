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

    def get_unresolved_dependencies(self, unresolved=None):
        """Gets the set of unresolved dependencies.

        :param unresolved: the known list of unresolved packages.
        :return: the set of unresolved depends.
        """
        return self.__get_unresolved_dependencies(self)

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
        stack.append((None, requirements))

        # add all mandatory packages
        for pkg in self.mandatory_packages:
            stack.append((pkg, pkg.requires))

        while len(stack) > 0:
            pkg, required = stack.pop()
            resolved.add(pkg)
            for require in required:
                for rel in require:
                    if rel not in unresolved:
                        if pkg_filter(rel.name, rel.version) is not None:
                            break
                        # use all packages that meets depends
                        candidates = self.find_all(rel.name, rel.version)
                        found = False
                        for cand in candidates:
                            if cand == pkg:
                                continue
                            found = True
                            if cand not in resolved:
                                stack.append((cand, cand.requires))

                        if found:
                            break
                else:
                    unresolved.add(require)
                    msg = "Unresolved depends: {0}".format(require)
                    warnings.warn(UnresolvedWarning(msg))

        resolved.remove(None)
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
