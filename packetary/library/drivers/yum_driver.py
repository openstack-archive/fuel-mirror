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

from collections import defaultdict
import logging
import lxml.etree as etree
import os
import six
import six.moves.urllib.parse as urlparse
import subprocess

from packetary.library.driver import IndexWriter
from packetary.library.driver import RepoDriver
from packetary.library.drivers.yum_package import YumPackage
from packetary.library.streams import GzipDecompress


logger = logging.getLogger(__package__)


_namespaces = {
    "main": "http://linux.duke.edu/metadata/common",
    "md": "http://linux.duke.edu/metadata/repo"
}


def _find_createrepo():
    """Finds the createrepo executable"""
    paths = os.environ['PATH'].split(os.pathsep)
    executable = os.environ.get("CREATEREPO_PATH", "createrepo")
    if not os.path.isfile(executable):
        for p in paths:
            f = os.path.join(p, executable)
            if os.path.isfile(f):
                return f
        return None
    else:
        return executable


createrepo = _find_createrepo()


class YumIndexWriter(IndexWriter):
    def __init__(self, driver, destination):
        self.destination = os.path.abspath(destination)
        self.driver = driver
        self.repos = defaultdict(set)

    def add(self, p):
        self.repos[p.reponame].add(p.filename)

    def commit(self, keep_existing=False):
        if createrepo is None:
            six.print_(
                "Please install createrepo utility and run the following "
                "commands manually:"
            )
            command = lambda x: six.print_("\t", subprocess.list2cmdline(x))
            executable = "createrepo"
        else:
            command = subprocess.check_call
            executable = createrepo

        for reponame, files in six.iteritems(self.repos):
            path = os.path.join(self.destination, reponame, self.driver.arch)
            if os.path.exists(os.path.join(path, "repodata", "repomd.xml")):
                if not keep_existing:
                    self.driver.load(
                        self.destination, reponame,
                        lambda x: self._remove_dirty_package(x, files)
                    )
                cmd = [executable, path, "--update"]
            else:
                cmd = [executable, path]
            command(cmd)

    def _remove_dirty_package(self, p, known_files):
        filename = p.filename
        if filename not in known_files:
            os.remove(self.driver.get_path(None, p))
            logger.info("File %s was removed.", p.filename)


class Driver(RepoDriver):
    """Driver for yum repositories."""

    def __init__(self, context, arch):
        self.connections = context.connections
        self.arch = arch

    def create_index(self, destination):
        return YumIndexWriter(self, destination)

    def parse_urls(self, urls):
        for url in urls:
            if url.endswith("/"):
                url = url[:-1]
            yield url.rsplit("/", 1)

    def get_path(self, base, package):
        baseurl = base or package.baseurl
        return "/".join((
            baseurl, package.reponame, self.arch, package.filename
        ))

    def load(self, baseurl, reponame, consumer):
        """Reads packages from metdata."""
        current_url = "/".join((baseurl, reponame, self.arch, ""))
        repomd = current_url + "repodata/repomd.xml"
        logger.info("repomd: %s", repomd)

        nodes = None
        with self.connections.get() as connection:
            repomd_tree = etree.parse(connection.open_stream(repomd))

            node = repomd_tree.find("./md:data[@type='primary']", _namespaces)
            if node is None:
                raise ValueError("malformed meta: %s" % repomd)
            location = node.find("./md:location", _namespaces).attrib["href"]
            location = urlparse.urljoin(current_url, location)
            logger.info("primary-db: %s", location)

            stream = GzipDecompress(connection.open_stream(location))
            nodes = etree.parse(stream)

        for pkg_tag in nodes.iterfind("./main:package", _namespaces):
            consumer(YumPackage(
                pkg_tag,
                baseurl,
                reponame
            ))
