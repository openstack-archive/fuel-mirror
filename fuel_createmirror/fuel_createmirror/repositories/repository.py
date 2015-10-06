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
from collections import defaultdict
from collections import namedtuple

from bintrees import FastRBTree

import six


class Search(object):
    def __init__(self, condition, required_version):
        self.condition = condition
        self.required_version = required_version

    def __call__(self, versions):
        return self.condition(versions, self.required_version)

    def __str__(self):
        return '{0} ({1})'.format(
            self.condition.__name__.rsplit('.', 1)[-1],
            self.required_version
        )


Dependency = namedtuple(
    "Dependency",
    ("package", "condition", "alt")
)


@six.add_metaclass(abc.ABCMeta)
class Package(object):
    @abc.abstractmethod
    def get_name(self):
        """Gets the package name."""

    @abc.abstractmethod
    def get_version(self):
        """Gets the package version."""

    @abc.abstractmethod
    def get_depends(self):
        """Gets the package depends."""

    def __hash__(self):
        return hash((self.get_name(), self.get_version()))

    def __eq__(self, other):
        return isinstance(other, Package) and\
            self.get_name() == other.get_name() and\
            self.get_version() == other.get_version()


@six.add_metaclass(abc.ABCMeta)
class Repository(object):
    def __init__(self):
        self.packages = defaultdict(FastRBTree)

    def __iter__(self):
        for versions in six.viewvalues(self.packages):
            for version in versions.values():
                yield version

    def __getitem__(self, item):
        return self.packages[item]

    def __contains__(self, item):
        return item in self.packages

    def add(self, package):
        """Adds new package."""
        self.packages[package.get_name()][package.get_version()] = package

    @abc.abstractmethod
    def clone(self, path, executor, counter):
        """Creates the clone of repository in local fs."""
