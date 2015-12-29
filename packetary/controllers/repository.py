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

import logging
import os

import six
import stevedore


logger = logging.getLogger(__package__)

urljoin = six.moves.urllib.parse.urljoin


class RepositoryController(object):
    """Implements low-level functionality to communicate with drivers."""

    _drivers = None

    def __init__(self, context, driver, arch):
        self.context = context
        self.driver = driver
        self.arch = arch

    @classmethod
    def load(cls, context, driver_name, repoarch):
        """Creates the repository manager.

        :param context: the context
        :param driver_name: the name of required driver
        :param repoarch: the architecture of repository (x86_64 or i386)
        """
        if cls._drivers is None:
            cls._drivers = stevedore.ExtensionManager(
                "packetary.drivers", invoke_on_load=True
            )
        try:
            driver = cls._drivers[driver_name].obj
        except KeyError:
            raise NotImplementedError(
                "The driver {0} is not supported yet.".format(driver_name)
            )
        return cls(context, driver, repoarch)

    def load_repositories(self, urls, consumer):
        """Loads the repository objects from url.

        :param urls: the list of repository urls.
        :param consumer: the callback to consume objects
        """
        if isinstance(urls, six.string_types):
            urls = [urls]

        connection = self.context.connection
        for parsed_url in self.driver.parse_urls(urls):
            self.driver.get_repository(
                connection, parsed_url, self.arch, consumer
            )

    def load_packages(self, repositories, consumer):
        """Loads packages from repository.

        :param repositories: the repository object
        :param consumer: the callback to consume objects
        """
        connection = self.context.connection
        for r in repositories:
            self.driver.get_packages(connection, r, consumer)

    def assign_packages(self, repository, packages, keep_existing=True):
        """Assigns new packages to the repository.

         It replaces the current repository`s packages.

        :param repository: the target repository
        :param packages: the set of new packages
        :param keep_existing:
            if True, all existing packages will be kept as is.
            if False, all existing packages, that are not included
            to new packages will be removed.
        """

        if not isinstance(packages, set):
            packages = set(packages)
        else:
            packages = packages.copy()

        if keep_existing:
            consume_exist = packages.add
        else:
            def consume_exist(package):
                if package not in packages:
                    filepath = os.path.join(
                        package.repository.url, package.filename
                    )
                    logger.info("remove package - %s.", filepath)
                    os.remove(filepath)

        self.driver.get_packages(
            self.context.connection, repository, consume_exist
        )
        self.driver.rebuild_repository(repository, packages)

    def copy_packages(self, repository, packages, keep_existing, observer):
        """Copies packages to repository.

        :param repository: the target repository
        :param packages: the set of packages
        :param keep_existing: see assign_packages for more details
        :param observer: the package copying process observer
        """
        with self.context.async_section() as section:
            for package in packages:
                section.execute(
                    self._copy_package, repository, package, observer
                )
        self.assign_packages(repository, packages, keep_existing)

    def clone_repositories(self, repositories, destination,
                           source=False, locale=False):
        """Creates copy of repositories.

        :param repositories: the origin repositories
        :param destination: the target folder
        :param source: If True, the source packages will be copied too.
        :param locale: If True, the localisation will be copied too.
        :return: the mapping origin to cloned repository.
        """
        mirros = dict()
        destination = os.path.abspath(destination)
        with self.context.async_section(0) as section:
            for r in repositories:
                section.execute(
                    self._fork_repository,
                    r, destination, source, locale, mirros
                )
        return mirros

    def _fork_repository(self, r, destination, source, locale, mirrors):
        """Creates clone of repository and stores it in mirrors."""
        new_repository = self.driver.fork_repository(
            self.context.connection, r, destination, source, locale
        )
        mirrors[r] = new_repository

    def _copy_package(self, target, package, observer):
        """Synchronises remote file to local fs."""
        dst_path = os.path.join(target.url, package.filename)
        src_path = urljoin(package.repository.url, package.filename)
        bytes_copied = self.context.connection.retrieve(
            src_path, dst_path, size=package.filesize
        )
        if package.filesize < 0:
            package.filesize = bytes_copied
        observer(bytes_copied)
