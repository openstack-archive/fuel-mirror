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

import six

from packetary.controllers import RepositoryController
from packetary.library.connections import ConnectionsManager
from packetary.library.executor import AsynchronousSection
from packetary.objects import Index
from packetary.objects import PackageRelation
from packetary.objects import PackagesTree
from packetary.objects.statistics import CopyStatistics


logger = logging.getLogger(__package__)


class Configuration(object):
    """The configuration holder."""

    def __init__(self, http_proxy=None, https_proxy=None,
                 retries_num=0, threads_num=0,
                 ignore_errors_num=0, retry_interval=0):
        """Initialises.

        :param http_proxy: the url of proxy for connections over http,
                           no-proxy will be used if it is not specified
        :param https_proxy: the url of proxy for connections over https,
                            no-proxy will be used if it is not specified
        :param retries_num: the number of retries on errors
        :param retry_interval: the time between retries (in seconds)
        :param threads_num: the max number of active threads
        :param ignore_errors_num: the number of errors that may occurs
                before stop processing
        """

        self.http_proxy = http_proxy
        self.https_proxy = https_proxy
        self.ignore_errors_num = ignore_errors_num
        self.retries_num = retries_num
        self.retry_interval = retry_interval
        self.threads_num = threads_num


class Context(object):
    """The infra-objects holder."""

    def __init__(self, config):
        """Initialises.

        :param config: the configuration
        """
        self._connection = ConnectionsManager(
            proxy=config.http_proxy,
            secure_proxy=config.https_proxy,
            retries_num=config.retries_num,
            retry_interval=config.retry_interval
        )
        self._threads_num = config.threads_num
        self._ignore_errors_num = config.ignore_errors_num

    @property
    def connection(self):
        """Gets the connection."""
        return self._connection

    def async_section(self, ignore_errors_num=None):
        """Gets the execution scope.

        :param ignore_errors_num: custom value for ignore_errors_num,
                                  the class value is used if omitted.
        """
        if ignore_errors_num is None:
            ignore_errors_num = self._ignore_errors_num

        return AsynchronousSection(self._threads_num, ignore_errors_num)


class RepositoryApi(object):
    """Provides high-level API to operate with repositories."""

    def __init__(self, controller):
        """Initialises.

        :param controller: the repository controller.
        """
        self.controller = controller

    @classmethod
    def create(cls, config, repotype, repoarch):
        """Creates the repository API instance.

        :param config: the configuration
        :param repotype: the kind of repository(deb, yum, etc)
        :param repoarch: the architecture of repository (x86_64 or i386)
        """
        context = config if isinstance(config, Context) else Context(config)
        return cls(RepositoryController.load(context, repotype, repoarch))

    def get_packages(self, origin, debs=None, requirements=None):
        """Gets the list of packages from repository(es).

        :param origin: The list of repository`s URLs
        :param debs: the list of repository`s URL to calculate list of
                     dependencies, that will be used to filter packages.
        :param requirements: the list of package relations,
                        to resolve the list of mandatory packages.
        :return: the set of packages
        """
        repositories = self._get_repositories(origin)
        return self._get_packages(repositories, debs, requirements)

    def clone_repositories(self, origin, destination, debs=None,
                           requirements=None, keep_existing=True,
                           include_source=False, include_locale=False):
        """Creates the clones of specified repositories in local folder.

        :param origin: The list of repository`s URLs
        :param destination: the destination folder path
        :param debs: the list of repository`s URL to calculate list of
                     dependencies, that will be used to filter packages.
        :param requirements: the list of package relations,
                        to resolve the list of mandatory packages.
        :param keep_existing: If False - local packages that does not exist
                              in original repo will be removed.
        :param include_source: if True, the source packages
                               will be copied as well.
        :param include_locale: if True, the locales
                               will be copied as well.
        :return: count of copied and total packages.
        """
        repositories = self._get_repositories(origin)
        packages = self._get_packages(repositories, debs, requirements)
        mirrors = self.controller.clone_repositories(
            repositories, destination, include_source, include_locale
        )

        package_groups = dict((x, set()) for x in repositories)
        for pkg in packages:
            package_groups[pkg.repository].add(pkg)

        stat = CopyStatistics()
        for repo, packages in six.iteritems(package_groups):
            mirror = mirrors[repo]
            logger.info("copy packages from - %s", repo)
            self.controller.copy_packages(
                mirror, packages, keep_existing, stat.on_package_copied
            )
        return stat

    def get_unresolved_dependencies(self, origin, main=None):
        """Gets list of unresolved dependencies for repository(es).

        :param origin: The list of repository`s URLs
        :param main: The main repository(es) URL
        :return: list of unresolved dependencies
        """
        packages = PackagesTree()
        self.controller.load_packages(
            self._get_repositories(origin),
            packages.add
        )

        if main is not None:
            base = Index()
            self.controller.load_packages(
                self._get_repositories(main),
                base.add
            )
        else:
            base = None

        return packages.get_unresolved_dependencies(base)

    def _get_repositories(self, urls):
        """Gets the set of repositories by url."""
        repositories = set()
        self.controller.load_repositories(urls, repositories.add)
        return repositories

    def _get_packages(self, repositories, master, requirements):
        """Gets the list of packages according to master and requirements."""
        if master is None and requirements is None:
            packages = set()
            self.controller.load_packages(repositories, packages.add)
            return packages

        packages = PackagesTree()
        self.controller.load_packages(repositories, packages.add)
        if master is not None:
            main_index = Index()
            self.controller.load_packages(
                self._get_repositories(master),
                main_index.add
            )
        else:
            main_index = None

        return packages.get_minimal_subset(
            main_index,
            self._parse_requirements(requirements)
        )

    @staticmethod
    def _parse_requirements(requirements):
        """Gets the list of relations from requirements.

        :param requirements: the list of requirement in next format:
                             'name [cmp version]|[alt [cmp version]]'
        """
        if requirements is not None:
            return set(
                PackageRelation.from_args(
                    *(x.split() for x in r.split("|"))) for r in requirements
            )
        return set()
