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

from bintrees import FastRBTree
from collections import defaultdict
from contextlib import closing
from datetime import datetime
from debian import deb822
import fcntl
import gzip
import logging
import os
import six

from packetary.library.checksum import composite as checksum_composite
from packetary.library.driver import IndexWriter
from packetary.library.driver import RepoDriver
from packetary.library.drivers.deb_package import DebPackage
from packetary.library.streams import GzipDecompress


logger = logging.getLogger(__package__)


_ARCH_MAPPING = {
    'i386': 'i386',
    'x86_64': 'amd64',
}

_META_FILES_WEIGHT = {
    "Packages": 1,
    "Release": 2,
    "Packages.gz": 3,
}

_DEFAULT_ORIGIN = "Unknown"

_SIZE_ALIGNMENT = 16

_CHECKSUM_METHOD_NAMES = ['MD5Sum', 'SHA1', 'SHA256']

_checksum_collector = checksum_composite('md5', 'sha1', 'sha256')


def _format_size(size):
    size = six.text_type(size)
    return (" " * (_SIZE_ALIGNMENT - len(size))) + size


class DebIndexWriter(IndexWriter):
    def __init__(self, driver, destination):
        self.driver = driver
        self.destination = os.path.abspath(destination)
        self.index = defaultdict(FastRBTree)
        self.origin = None

    def add(self, p):
        self.index[(p.suite, p.comp)][p] = None
        if self.origin is None:
            self.origin = p.dpkg.get('origin')

    def commit(self, keep_existing=True):
        suites = set()
        self.origin = self.origin or _DEFAULT_ORIGIN
        for repo, packages in six.iteritems(self.index):
            self._rebuild_index(repo, packages, keep_existing)
            suites.add(repo[0])
        self._updates_global_releases(suites)

    def _rebuild_index(self, repo, packages, keep_existing):
        """Saves the index file in local file system."""
        path = os.path.join(
            self.destination, "dists", repo[0], repo[1],
            "binary-" + self.driver.arch
        )

        index_file = os.path.join(path, "Packages")
        index_gz = os.path.join(path, "Packages.gz")
        logger.info("the index file: %s.", index_file)
        dirty_files = set()
        if keep_existing:
            on_existing_package = lambda x: packages.insert(p, None)
            handler = lambda x: None
        else:
            on_existing_package = lambda x: dirty_files.add(x.filename)
            handler = lambda x: dirty_files.discard(x.filename)

        if os.path.exists(index_gz):
            logger.info("process existing index: %s", index_gz)
            self.driver.load(self.destination, repo, on_existing_package)

        if not os.path.exists(path):
            os.makedirs(path)

        with closing(open(index_file, "wb")) as index:
            with closing(gzip.open(index_gz, "wb")) as index_gz:
                for p in packages.keys():
                    p.dpkg.dump(fd=index)
                    p.dpkg.dump(fd=index_gz)
                    index.write(b"\n")
                    index_gz.write(b"\n")
                    handler(p)

        for f in dirty_files:
            os.remove(os.path.join(self.destination, f))
            logger.info("File %s was removed.", f)

        self._generate_component_release(path, *repo)

        logger.info(
            "the index %s has been updated successfully.", index_file
        )

    def _generate_component_release(self, path, suite, component):
        """Generates the release meta information."""
        meta_filename = os.path.join(path, "Release")
        with closing(open(meta_filename, "w")) as meta:
            self._dump_meta(meta, [
                ("Archive", suite),
                ("Component", component),
                ("Origin", self.origin),
                ("Label", self.origin),
                ("Architecture", self.driver.arch)
            ])

    def _updates_global_releases(self, suites):
        """Generates the overall meta information."""
        path = os.path.join(self.destination, "dists")
        date_str = datetime.now().strftime("%a, %d %b %Y %H:%M:%S %Z")
        for suite in suites:
            suite_dir = os.path.join(path, suite)
            components = [
                d for d in os.listdir(suite_dir)
                if os.path.isdir(os.path.join(suite_dir, d))
            ]
            release_file = os.path.join(suite_dir, "Release")
            with closing(open(release_file, "w")) as meta:
                fcntl.flock(meta.fileno(), fcntl.LOCK_EX)
                try:
                    self._dump_meta(meta, [
                        ("Origin", self.origin),
                        ("Label", self.origin),
                        ("Suite", suite),
                        ("Codename", suite),
                        ("Architecture", self.driver.arch),
                        ("Components", " ".join(components)),
                        ("Date", date_str),
                        ("Description", "{0} {1} Partial".format(
                            self.origin, suite
                        )),
                    ])
                    self._dump_files(meta, suite_dir, components)
                finally:
                    fcntl.flock(meta.fileno(), fcntl.LOCK_UN)

    @staticmethod
    def _dump_files(meta, suite_dir, components):
        """Dumps files meta information."""
        index = defaultdict(list)
        for d in components:
            comp_path = os.path.join(suite_dir, d)
            for root, dirs, files in os.walk(comp_path):
                files = six.moves.filter(
                    _META_FILES_WEIGHT.__contains__, files
                )
                for f in files:
                    filepath = os.path.join(root, f)
                    with closing(open(filepath, "rb")) as stream:
                        size = os.fstat(stream.fileno()).st_size
                        checksum = six.moves.zip(
                            _CHECKSUM_METHOD_NAMES,
                            _checksum_collector(stream)
                        )
                        for n, h in checksum:
                            index[n].append((
                                h,
                                _format_size(size),
                                filepath[len(suite_dir) + 1:],
                                _META_FILES_WEIGHT[f]
                            ))

        index = sorted(six.iteritems(index), key=lambda x: x[0])
        for algo_name, files in index:
            meta.write(":".join((algo_name, "\n")))
            files = sorted(files, key=lambda x: x[-1])
            for checksum, size, filepath, _ in files:
                meta.write(" ".join((checksum, size, filepath)))
                meta.write("\n")

    @staticmethod
    def _dump_meta(stream, meta):
        for k, v in meta:
            stream.write("".join((k, ": ", v, "\n")))


class Driver(RepoDriver):
    """Driver for deb repositories."""

    def __init__(self, context, arch):
        self.connections = context.connections
        self.arch = _ARCH_MAPPING[arch]

    def create_index(self, destination):
        return DebIndexWriter(self, destination)

    def parse_urls(self, urls):
        for url in urls:
            try:
                baseurl, suite, comps = url.split(" ", 2)
            except ValueError:
                raise ValueError(
                    "Invalid url: {0}\n"
                    "Expected: baseurl suite component[ component]"
                    .format(url)
                )

            if baseurl.endswith("/dists/"):
                baseurl = baseurl[:-7]
            elif baseurl.endswith("/dists"):
                baseurl = baseurl[:-6]
            elif baseurl.endswith("/"):
                baseurl = baseurl[:-1]

            for comp in comps.split(" "):
                yield baseurl, (suite, comp)

    def get_path(self, base, package):
        baseurl = base or package.baseurl
        return "/".join((baseurl, package.filename))

    def load(self, baseurl, repo, consumer):
        """Loads from Packages.gz."""
        suite, comp = repo
        index_file = "{0}/dists/{1}/{2}/binary-{3}/Packages.gz".format(
            baseurl, suite, comp, self.arch
        )
        logger.info("loading packages from: %s", index_file)
        with self.connections.get() as connection:
            stream = GzipDecompress(connection.open_stream(index_file))
            pkg_iter = deb822.Packages.iter_paragraphs(stream)
            for dpkg in pkg_iter:
                consumer(DebPackage(dpkg, baseurl, suite, comp))

        logger.info(
            "packages from %s has been loaded successfully.", index_file
        )
