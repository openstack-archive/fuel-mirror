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


import abc
import six


@six.add_metaclass(abc.ABCMeta)
class IndexWriter(object):
    """Helpers to generate index of repository."""

    @abc.abstractmethod
    def add(self, package):
        """Adds package to index."""

    @abc.abstractmethod
    def commit(self, keep_existing=False):
        """Saves changes to disk."""


@six.add_metaclass(abc.ABCMeta)
class RepoDriver(object):
    """The driver to access the repository."""

    @abc.abstractmethod
    def create_index(self, destination):
        """Creates the index writer."""

    @abc.abstractmethod
    def load(self, baseurl, reponame, consumer):
        """Loads packages from url."""

    @abc.abstractmethod
    def get_path(self, base, package):
        """Gets the package full path."""

    @abc.abstractmethod
    def parse_urls(self, urls):
        """Parses urls.

        :return: The sequence of url.
        """
