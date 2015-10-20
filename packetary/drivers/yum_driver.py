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

import copy
import errno
import os
import subprocess

import lxml.etree as etree
import six

from packetary.drivers.base import RepositoryDriverBase
from packetary.library.streams import GzipDecompress
from packetary.objects.base import ComparableObject
from packetary.objects import FileChecksum
from packetary.objects import Package
from packetary.objects import PackageRelation
from packetary.objects import Repository
from packetary.objects import VersionRange


urljoin = six.moves.urllib.parse.urljoin

# TODO(should be configurable)
_CORE_GROUPS = ("core", "base")

# TODO(should be configurable)
_MANDATORY_TYPES = ("mandatory", "default")

_NAMESPACES = {
    "main": "http://linux.duke.edu/metadata/common",
    "md": "http://linux.duke.edu/metadata/repo",
    "rpm": "http://linux.duke.edu/metadata/rpm"
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


class RPMVersion(ComparableObject):
    """The RPM package version."""

    def __init__(self, epoch, version, release):
        self.components = (int(epoch), tuple(version), tuple(release))

    def cmp(self, other):
        if not isinstance(other, RPMVersion):
            other = RPMVersion.from_string(str(other))

        if not isinstance(other, RPMVersion):
            raise TypeError
        if self.components < other.components:
            return -1
        if self.components > other.components:
            return 1
        return 0

    def __eq__(self, other):
        if other is self:
            return True
        return self.cmp(other) == 0

    def __str__(self):
        if self.components[0] != 0:
            return "{0}-{1}".format(
                self.components[0],
                "-".join(".".join(x) for x in self.components[1:])
            )
        return "-".join(".".join(x) for x in self.components[1:])

    def __unicode__(self):
        if self.components[0] != 0:
            return u"{0}-{1}".format(
                self.components[0],
                u"-".join(u".".join(x) for x in self.components[1:])
            )
        return u"-".join(u".".join(x) for x in self.components[1:])

    @classmethod
    def from_string(cls, s):
        """Constructs from string."""
        components = s.split("-")
        if len(components) > 2:
            epoch = components[0]
            components = components[1:]
        else:
            epoch = 0
        return cls(epoch, components[0].split("."), components[1].split("."))

    @classmethod
    def from_dict(cls, d):
        """Constructs from dictionary."""
        return cls(
            d.get("epoch", 0),
            d.get("ver", "0.0").split("."),
            d.get("rel", "0").split(".")
        )


class YumRepositoryDriver(RepositoryDriverBase):
    def parse_urls(self, urls):
        """Overrides method of superclass."""
        for url in urls:
            if url.endswith("/"):
                url = url[:-1]
            yield url

    def get_repository(self, connection, url, arch, consumer):
        """Overrides method of superclass."""
        name = url.rsplit("/", 1)[-1]
        baseurl = "/".join((url, arch, ""))
        consumer(Repository(
            name=name,
            architecture=arch,
            origin="",
            url=baseurl
        ))

    def get_packages(self, connection, repository, consumer):
        """Overrides method of superclass."""
        baseurl = repository.url
        repomd = urljoin(baseurl, "repodata/repomd.xml")
        self.logger.debug("repomd: %s", repomd)

        repomd_tree = etree.parse(connection.open_stream(repomd))
        mandatory = self._get_mandatory_packages(
            self._load_db(connection, baseurl, repomd_tree, "group_gz")
        )
        primary_db = self._load_db(connection, baseurl, repomd_tree, "primary")
        if primary_db is None:
            raise ValueError("Malformed repository: {0}".format(repository))

        counter = 0
        for tag in primary_db.iterfind("./main:package", _NAMESPACES):
            try:
                name = _find(tag, "./main:name").text
                consumer(Package(
                    repository=repository,
                    name=_find(tag, "./main:name").text,
                    version=RPMVersion.from_dict(
                        _find(tag, "./main:version").attrib
                    ),
                    filesize=int(_find(
                        tag, "./main:size").attrib.get("package", -1)
                    ),
                    filename=_find(tag, "./main:location").attrib["href"],
                    checksum=_get_checksum(tag),
                    mandatory=name in mandatory,
                    requires=_get_relations(tag, "requires"),
                    obsoletes=_get_relations(tag, "obsoletes"),
                    provides=_get_relations(tag, "provides")
                ))
            except (ValueError, KeyError) as e:
                self.logger.error(
                    "Malformed tag %s - %s: %s",
                    repository, etree.tostring(tag), six.text_type(e)
                )
                raise
            counter += 1
        self.logger.info("loaded: %d packages from %s.", counter, repository)

    def rebuild_repository(self, repository, packages):
        """Overrides method of superclass."""

        if createrepo is None:
            six.print_(
                "Please install createrepo utility and run the following "
                "commands manually:"
            )

            def launcher(args):
                six.print_("\t", subprocess.list2cmdline(args))

            executable = "createrepo"
        else:
            launcher = subprocess.check_call
            executable = createrepo

        basepath = repository.url
        if basepath.startswith("file://"):
            basepath = basepath[7:]
        if not basepath.startswith("/"):
            raise ValueError(
                "The absolute path expected instead of: {0}"
                .format(basepath)
            )
        launcher([executable, basepath, "--update"])

    def clone_repository(self, connection, repository, destination,
                         source=False, locale=False):
        """Overrides method of superclass."""
        # TODO(download gpk)
        # TODO(sources and locales)
        destination = os.path.join(
            destination,
            repository.name,
            repository.architecture,
            ""
        )

        clone = copy.copy(repository)
        clone.url = destination
        self.logger.info("clone repository %s to %s", repository, destination)
        try:
            os.makedirs(destination)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise

        self.rebuild_repository(clone, set())
        return clone

    def _load_db(self, connection, baseurl, repomd, dbname):
        """Loads database.

        :param connection: the connection object
        :param baseurl: the base repository URL
        :param repomd: the parsed metadata of repository
        :param dbname: the name of database
        :return: parsed database file or None if db does not exist
        """
        self.logger.debug("loading %s database...", dbname)
        node = repomd.find(
            "./md:data[@type='{0}']".format(dbname), _NAMESPACES
        )
        if node is None:
            return

        url = urljoin(
            baseurl,
            node.find("./md:location", _NAMESPACES).attrib["href"]
        )
        self.logger.debug("loading %s - %s...", dbname, url)
        return etree.parse(
            GzipDecompress(connection.open_stream(url))
        )

    def _get_mandatory_packages(self, groups_db):
        """Get the set of mandatory package names.

        :param groups_db: the parsed groups database
        """
        package_names = set()
        if groups_db is None:
            return package_names
        count = 0
        for name in _CORE_GROUPS:
            result = groups_db.xpath("./group/id[text()='{0}']".format(name))
            if len(result) == 0:
                self.logger.warning("the group '%s' is not found.", name)
                continue
            group = result[0].getparent()
            for t in _MANDATORY_TYPES:
                xpath = "./packagelist/packagereq[@type='{0}']".format(t)
                for tag in group.iterfind(xpath):
                    package_names.add(tag.text)
                    count += 1
        self.logger.info("detected %d mandatory packages.", count)
        return package_names


def _find(tag, path):
    """Wrapper around etree.tag.find that uses rpm namespaces."""
    return tag.find(path, namespaces=_NAMESPACES)


def _iterfind(tag, path):
    """Wrapper around etree.tag.iterfind that uses rpm namespaces."""
    return tag.iterfind(path, namespaces=_NAMESPACES)


def _get_checksum(pkg_tag):
    """Gets checksum from package tag."""
    checksum = dict.fromkeys(("md5", "sha1", "sha256"), None)
    tag = _find(pkg_tag, "./main:checksum")
    checksum[tag.attrib["type"]] = tag.text
    return FileChecksum(**checksum)


def _get_relations(pkg_tag, name):
    """Gets package relations by name from package tag.

    :param pkg_tag: the xml-tag with package description
    :param name: the relations name
    :return: list of PackageRelation objects
    """
    relations = list()
    append = relations.append
    for elem in _iterfind(pkg_tag, "./main:format/rpm:%s/rpm:entry" % name):
        rel = PackageRelation(
            elem.attrib['name'],
            _get_version_range(elem.attrib)
        )
        append(rel)

    return relations


def _get_version_range(attrs):
    """Gets the version range for relation from its attributes.

    :param attrs: the version attributes
    :return VersionRange object
    """
    if "flags" not in attrs:
        return VersionRange()
    return VersionRange(
        attrs["flags"].lower(),
        RPMVersion.from_dict(attrs)
    )
