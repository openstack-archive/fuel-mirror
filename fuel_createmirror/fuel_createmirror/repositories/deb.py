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

from __future__ import with_statement

from collections import defaultdict
import gzip
import logging
import six

from debian import deb822
from debian import debian_support

from fuel_createmirror.locations import local
from fuel_createmirror.locations import open_location

from . import conditions
from .repository import Dependency
from .repository import Package
from .repository import Repository
from .repository import Search


logger = logging.getLogger(__package__)

_relations = {
    '>>': conditions.greater_than,
    '<<': conditions.less_than,
    '=': conditions.equal,
    '>=': conditions.greater_or_equal,
    '<=': conditions.less_or_equal,
}


_arch_mapping = {
    'i386': 'binary-i386',
    'x86_64': 'binary-amd64',
    'source': 'source',
    None: 'binary-i386',
}


class DebPackage(Package):
    """Debian package."""

    def __init__(self, location, dist, component, dpkg):
        self.dist = dist
        self.comp = component
        self.location = location
        self.dpkg = dpkg
        self.depends = None

    def get_name(self):
        return self.dpkg['package']

    def get_version(self):
        return debian_support.Version(self.dpkg['version'])

    def get_depends(self):
        if self.depends is not None:
            return self.depends

        depends = list()
        for alts in self.dpkg.relations["depends"]:
            for dep in reversed(alts):
                if 'version' in dep:
                    se = Search(
                        _relations[dep['version'][0]],
                        debian_support.Version(dep['version'][1])
                    )
                else:
                    se = Search(conditions.newest, None)

                depends.append(
                    Dependency(dep['name'], se, dep)
                )
        self.depends = depends


class DebRepository(Repository):
    """Debian repository."""

    def clone(self, path, executor, counter):
        indexes = defaultdict(set)
        for p in self:
            executor.execute(DebRepository._copy_package, p, path, counter)
            indexes[(p.dist, p.comp)].add(p)

        executor.wait()

        for comp, packages in six.viewitems(indexes):
            dir_path = local.mkdir(path, *comp)
            executor.put(DebRepository._update_index, dir_path, packages)
        executor.wait()

    @staticmethod
    def _copy_package(package, path, callback):
        """copy package to local fs."""
        package.location.fetch(
            "../" + package.dpkg['filename'],
            local.join_path(path, package.dpkg['filename']),
            sha1=package.dpkg['sha1'],
            size=package.dpkg['size']
        )
        callback()

    @staticmethod
    def _update_index(path, packages):
        """Saves the index file in local file system."""
        index_file = local.join_path(path, "Packages.gz")
        tmp = local.join_path(path, "Packages.tmp.gz")
        if local.exists(index_file):
            with local.open_gzip(index_file) as stream:
                _load_from_index(
                    stream,
                    lambda x: DebPackage(None, None, None, x),
                    packages,
                    lambda: None
                )

        with local.create_gzip(tmp) as pkg_gz:
            for p in packages:
                p.dpkg.dump(fd=pkg_gz)

        local.rename(tmp, index_file)


def open_repository(urls, arch=None, counter=None):
    """Loads packages from Debian repository."""
    repo = DebRepository()
    if counter is None:
        counter = lambda: None

    arch = _arch_mapping[arch]
    locations = dict()
    for url in urls:
        deb, url, dist, components = url.split(" ", 3)
        if deb != 'deb':
            raise ValueError("Unexpected token: {0}".format(deb))
        if url in locations:
            loc = locations[url]
        else:
            loc = locations[url] = open_location(url)

        for comp in components.split():
            _load_packages(loc, dist, comp, arch, repo, counter)
    return repo


def _load_packages(loc, dist, comp, arch, repo, counter):
    """Loads from Packages.gz."""
    index = "{0}/{1}/{2}/Packages.gz".format(dist, comp, arch)
    with loc.open(index, "rb") as stream:
        _load_from_index(
            gzip.GzipFile(fileobj=stream, mode='rb'),
            lambda x: DebPackage(loc, dist, comp, x),
            repo,
            counter
        )


def _load_from_index(stream, factory, repo, counter):
    """Loads packages from index."""
    pkg_iter = deb822.Packages.iter_paragraphs(stream)
    dep_packages = six.moves.map(factory, pkg_iter)
    for package in dep_packages:
        repo.add(package)
        counter()
