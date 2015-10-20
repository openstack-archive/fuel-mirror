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

from contextlib import closing
import copy
import datetime
import errno
import fcntl
import gzip
import os

from debian import deb822
from debian import debfile
from debian.debian_support import Version
import six

from packetary.drivers.base import RepositoryDriverBase
from packetary.library.checksum import composite as checksum_composite
from packetary.library.streams import GzipDecompress
from packetary.objects import FileChecksum
from packetary.objects import Package
from packetary.objects import PackageRelation
from packetary.objects import Repository
from packetary.objects import VersionRange


_OPERATORS_MAPPING = {
    '>>': 'gt',
    '<<': 'lt',
    '=': 'eq',
    '>=': 'ge',
    '<=': 'le',
}

_ARCHITECTURES = {
    "x86_64": "amd64",
    "i386": "i386",
    "source": "Source",
    "amd64": "x86_64",
}

_PRIORITIES = {
    "required": 1,
    "important": 2,
    "standard": 3,
    "optional": 4,
    "extra": 5
}

# Order is important
_REPOSITORY_FILES = [
    "Packages",
    "Release",
    "Packages.gz"
]

# TODO(should be configurable)
_MANDATORY_PRIORITY = 3

_CHECKSUM_METHODS = (
    "MD5Sum",
    "SHA1",
    "SHA256"
)

_checksum_collector = checksum_composite('md5', 'sha1', 'sha256')


class DebRepositoryDriver(RepositoryDriverBase):
    def parse_urls(self, urls):
        """Overrides method of superclass."""
        for url in urls:
            base, suite, components = url.split(" ", 2)
            if base.endswith("dists/"):
                base = base[:-7]
            elif base.endswith("dists"):
                base = base[:-6]
            elif base.endswith("/"):
                base = base[:-1]
            for component in components.split():
                yield (base, suite, component)

    def get_repository(self, connection, url, arch, consumer):
        """Overrides method of superclass."""

        base, suite, component = url
        release = "/".join((
            base, "dists", suite, component,
            "binary-" + _ARCHITECTURES[arch],
            "Release"
        ))
        deb_release = deb822.Release(connection.open_stream(release))
        consumer(Repository(
            name=(deb_release["Archive"], deb_release["Component"]),
            architecture=arch,
            origin=deb_release["origin"],
            url=base + "/"
        ))

    def get_packages(self, connection, repository, consumer):
        """Overrides method of superclass."""
        index = _get_meta_url(repository, "Packages.gz")
        stream = GzipDecompress(connection.open_stream(index))
        self.logger.info("loading packages from %s ...", repository)
        pkg_iter = deb822.Packages.iter_paragraphs(stream)
        counter = 0
        for dpkg in pkg_iter:
            try:
                consumer(Package(
                    repository=repository,
                    name=dpkg["package"],
                    version=Version(dpkg['version']),
                    filesize=int(dpkg.get('size', -1)),
                    filename=dpkg["filename"],
                    checksum=FileChecksum(
                        md5=dpkg.get("md5sum"),
                        sha1=dpkg.get("sha1"),
                        sha256=dpkg.get("sha256"),
                    ),
                    mandatory=_is_mandatory(dpkg),
                    # Recommends are installed by default (since Lucid)
                    requires=_get_relations(
                        dpkg, "depends", "pre-depends", "recommends"
                    ),
                    obsoletes=_get_relations(dpkg, "replaces"),
                    provides=_get_relations(dpkg, "provides"),
                ))
            except KeyError as e:
                self.logger.error(
                    "Malformed index %s - %s: %s",
                    repository, six.text_type(dpkg), six.text_type(e)
                )
                raise
            counter += 1

        self.logger.info("loaded: %d packages from %s.", counter, repository)

    def rebuild_repository(self, repository, packages):
        """Overrides method of superclass."""
        basedir = _get_filepath(repository.url)
        path = _get_meta_path(repository, "")
        try:
            os.makedirs(path)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise

        index = os.path.join(path, "Packages")
        index_gz = os.path.join(path, "Packages.gz")
        count = 0
        with closing(open(index, "wb")) as fd1:
            with closing(gzip.open(index_gz, "wb")) as fd2:
                writer = _composite_writer(fd1, fd2)
                for pkg in packages:
                    filename = os.path.join(basedir, pkg.filename)
                    with closing(debfile.DebFile(filename)) as deb:
                        debcontrol = deb.debcontrol()
                    debcontrol.setdefault("Origin", repository.origin)
                    debcontrol["Size"] = str(pkg.filesize)
                    debcontrol["Filename"] = pkg.filename
                    for k, v in six.moves.zip(_CHECKSUM_METHODS, pkg.checksum):
                        debcontrol[k] = v
                    writer(debcontrol.dump())
                    writer("\n")
                    count += 1
        self.logger.info("saved %d packages in %s", count, repository)
        self._update_suite_index(repository)

    def clone_repository(self, connection, repository, destination,
                         source=False, locale=False):
        """Overrides method of superclass."""
        # TODO(download gpk)
        # TODO(sources and locales)
        if not destination.endswith(os.path.sep):
            destination += os.path.sep

        clone = copy.copy(repository)
        clone.url = destination
        path = _get_meta_path(clone, "")
        self.logger.info("clone repository %s to %s", repository, path)
        try:
            os.makedirs(path)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise

        release = deb822.Release()
        release["Origin"] = repository.origin
        release["Label"] = repository.origin
        release["Archive"] = repository.name[0]
        release["Component"] = repository.name[1]
        release["Architecture"] = _ARCHITECTURES[repository.architecture]

        with closing(open(os.path.join(path, "Release"), "wb")) as fd:
            release.dump(fd)
        # creates default files
        open(os.path.join(path, "Packages"), "ab").close()
        gzip.open(os.path.join(path, "Packages.gz"), "ab").close()
        return clone

    def _update_suite_index(self, repository):
        """Updates the Release file in the suite."""
        path = os.path.join(
            _get_filepath(repository.url), "dists", repository.name[0]
        )
        release_path = os.path.join(path, "Release")
        self.logger.info("updated suite release file: %s", release_path)
        with closing(open(release_path, "a+b")) as fd:
            fcntl.flock(fd.fileno(), fcntl.LOCK_EX)
            try:
                fd.seek(0)
                meta = deb822.Release(fd)
                if len(meta) == 0:
                    self.logger.debug("create suite index %s.", release_path)
                    meta["Origin"] = repository.origin
                    meta["Label"] = repository.origin
                    meta["Suite"] = repository.name[0]
                    meta["Codename"] = repository.name[0].split("-")[0]
                    meta["Description"] = "The packages repository."
                    for m in _CHECKSUM_METHODS:
                        meta[m] = []

                    for fpath, size, cs in _get_files_info(repository):
                        fname = fpath[len(path) + 1:]
                        for m, checksum in cs:
                            meta[m].append(deb822.Deb822Dict({
                                m: checksum,
                                "size": size,
                                "name": fname
                            }))
                else:
                    self.logger.debug("update suite index %s.", release_path)
                    for m in _CHECKSUM_METHODS:
                        if m not in meta:
                            meta[m] = []

                    for fpath, size, cs in _get_files_info(repository):
                        fname = fpath[len(path) + 1:]
                        for m, checksum in cs:
                            for v in meta[m]:
                                if v["name"] == fname:
                                    v[m] = checksum
                                    v["size"] = size
                                    break
                            else:
                                meta[m].append(deb822.Deb822Dict({
                                    m: checksum,
                                    "size": size,
                                    "name": fpath[len(path) + 1:]
                                }))

                meta["Date"] = datetime.datetime.now().strftime(
                    "%a, %d %b %Y %H:%M:%S %Z"
                )
                _add_to_string_list(
                    meta, "Architectures",
                    _ARCHITECTURES[repository.architecture]
                )
                _add_to_string_list(
                    meta, "Components", repository.name[1]
                )
                fd.truncate(0)
                meta.dump(fd)
            finally:
                fcntl.flock(fd.fileno(), fcntl.LOCK_UN)


def _get_meta_url(repository, filename):
    """Get the meta file url.

    :param repository: the repository object
    :param filename: the name of meta-file
    """
    return "/".join((
        repository.url[:-1], "dists", repository.name[0], repository.name[1],
        "binary-" + _ARCHITECTURES[repository.architecture],
        filename
    ))


def _get_meta_path(repository, filename):
    """Get the local filepath for meta-file.

    :param repository: the repository object
    :param filename: the name of meta-file
    """
    basepath = _get_filepath(repository.url)
    return os.path.join(
        basepath, "dists", repository.name[0], repository.name[1],
        "binary-" + _ARCHITECTURES[repository.architecture],
        filename
    )


def _get_filepath(url):
    """Get the local filepath from the URL.

    :param url: the URL
    :return: the local-filepath
    :raises ValueError
    """
    if url.startswith("file://"):
        url = url[7:]
    if not url.startswith("/"):
        raise ValueError("The absolute path is expected: {0}."
                         .format(url))
    return url


def _is_mandatory(dpkg):
    """Checks that package is mandatory.

    :param dpkg: the debian-package object
    :type dpkg: deb822.Packages
    """
    if dpkg.get("essential") == "yes":
        return True

    return _PRIORITIES.get(
        dpkg.get("priority"), _MANDATORY_PRIORITY + 1
    ) < _MANDATORY_PRIORITY


def _get_relations(dpkg, *names):
    """Gets the package relations.

    :param dpkg: the debian-package object
    :type dpkg: deb822.Packages
    :param names: the relation names
    :return: the list of PackageRelation objects
    """
    relations = list()
    for name in names:
        for variants in dpkg.relations[name]:
            alternative = None
            for v in reversed(variants):
                alternative = PackageRelation(
                    v['name'],
                    _get_version_range(v.get('version')),
                    alternative
                )
            if alternative is not None:
                relations.append(alternative)
    return relations


def _get_version_range(rel_version):
    """Gets the version range.

    :param rel_version: the version of package range(op, version)
    :type rel_version: tuple
    return: The VersionRange object
    """
    if rel_version is None:
        return VersionRange()
    return VersionRange(
        _OPERATORS_MAPPING[rel_version[0]],
        rel_version[1],
    )


def _get_files_info(repository):
    """Gets the information about meta-file for repository."""
    for fname in _REPOSITORY_FILES:
        filepath = _get_meta_path(repository, fname)
        with closing(open(filepath, "rb")) as stream:
            size = os.fstat(stream.fileno()).st_size
            checksum = six.moves.zip(
                _CHECKSUM_METHODS,
                _checksum_collector(stream)
            )
        yield filepath, six.text_type(size), checksum


def _add_to_string_list(target, key, value):
    """Adds new value for string separated meta value.

    :param target: the dictionary of meta-information
    :param key: the name of key
    :param value: new value
    """
    if key in target:
        values = target[key].split()
        if value not in values:
            values.append(value)
            values.sort()
            target[key] = " ".join(values)
    else:
        target[key] = value


def _composite_writer(*files):
    """Makes helper, that writes into several files simultaneously."""
    def write(s):
        if isinstance(s, six.text_type):
            s = s.encode("utf-8")
        for f in files:
            f.write(s)
    return write
