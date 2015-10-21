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
import logging

import six


@six.add_metaclass(abc.ABCMeta)
class RepositoryDriverBase(object):
    """The super class for Repository Drivers.

    To implement support for new type of repository:
    - inherit from this class
    - implement all abstract methods
    - register your class in 'packetary.drivers' namespace.
    """
    def __init__(self):
        self.logger = logging.getLogger(__package__)

    @abc.abstractmethod
    def parse_urls(self, urls):
        """Parses the repository url.

        :return: the sequence of parsed urls
        """

    @abc.abstractmethod
    def get_repository(self, connection, url, arch, consumer):
        """Loads the repository meta information from URL.

        :param connection: the connection manager instance
        :param url: the repository`s url
        :param arch: the repository`s architecture
        :param consumer: the callback to consume result
        """

    @abc.abstractmethod
    def get_packages(self, connection, repository, consumer):
        """Loads packages from repository.

        :param connection: the connection manager instance
        :param repository: the repository object
        :param consumer: the callback to consume result
        """

    @abc.abstractmethod
    def clone_repository(self, connection, repository, destination,
                         source=False, locale=False):
        """Creates copy of repository.

        :param connection: the connection manager instance
        :param repository: the source repository
        :param destination: the destination folder
        :param source: copy source files
        :param locale: copy localisation
        :return: The copy of repository
        """

    @abc.abstractmethod
    def rebuild_repository(self, repository, packages):
        """Re-builds the repository.

        :param repository: the target repository
        :param packages: the set of packages
        """
