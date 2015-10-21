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

import logging
import os

from packetary.library import drivers as _drivers


logger = logging.getLogger(__package__)


class Repository(object):
    def __init__(self, context, kind, arch, drivers=_drivers):
        self.context = context
        try:
            self.driver = getattr(drivers, kind)(context, arch)
        except AttributeError:
            raise NotImplementedError(
                "Unsupported repository: {0}".format(kind)
            )

    def load_packages(self, urls, consumer):
        """Loads packages from url(s)."""
        if not isinstance(urls, (list, tuple)):
            urls = [urls]

        with self.context.async_section() as scope:
            for url, repo in self.driver.parse_urls(urls):
                scope.execute(self.driver.load, url, repo, consumer)

    def copy_packages(self, producer, destination, keep_existing):
        """Copies packages to specified directory."""

        index_writer = self.driver.create_index(destination)
        with self.context.async_section() as scope:
            for package in producer:
                scope.execute(self._copy_package, package, destination)
                index_writer.add(package)
        index_writer.commit(keep_existing)

    def _copy_package(self, package, destination):
        """Synchronises remote file to local fs."""
        connections = self.context.connections
        offset = 0
        dst_path = self.driver.get_path(destination, package)
        src_path = self.driver.get_path(package.baseurl, package)
        try:
            stats = os.stat(dst_path)
            if stats.st_size == package.size:
                logger.info("file %s is same.", dst_path)
                return

            if stats.st_size < package.size:
                offset = stats.st_size
        except OSError as e:
            if e.errno != 2:
                raise

        logger.info(
            "download: %s - %s, offset: %d",
            src_path, dst_path, offset
        )
        with connections.get() as connection:
            connection.retrieve(src_path, dst_path, offset)
