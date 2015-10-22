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

from collections import namedtuple

from packetary.library.package import Package
from packetary.library.package import Relation
from packetary.library.package import VersionRange


_Version = namedtuple(
    "_PackageVersion", ("epoch", "version", "release")
)


_namespaces = {
    "main": "http://linux.duke.edu/metadata/common",
    "rpm": "http://linux.duke.edu/metadata/rpm"
}


class Version(_Version):
    def __new__(cls, args):
        return _Version.__new__(
            cls,
            int(args.get("epoch", 0)),
            tuple(args.get("ver", "0.0").split(".")),
            tuple(args.get("rel", "0").split('.'))
        )

    def __str__(self):
        return "%s-%s-%s" % (
            self.epoch, ".".join(self.version), ".".join(self.release)
        )


def _get_version_range(args):
    if "flags" not in args:
        return VersionRange()
    return VersionRange(
        args["flags"].lower(),
        Version(args)
    )


def _find(tag, path):
    return tag.find(path, namespaces=_namespaces)


def _iterfind(tag, path):
    return tag.iterfind(path, namespaces=_namespaces)


def _get_checksum(tag):
    checksum = _find(tag, "./main:checksum")
    return checksum.attrib["type"], checksum.text


def _get_relations(tag, name):
    relations = list()
    append = relations.append
    for elem in _iterfind(tag, "./main:format/rpm:%s/rpm:entry" % name):
        rel = Relation(
            elem.attrib['name'],
            _get_version_range(elem.attrib)
        )
        append(rel)

    return relations


class YumPackage(Package):
    """Yum package."""
    def __init__(self, pkg_tag, baseurl, reponame):
        self.reponame = reponame
        self.repo = tuple(baseurl.rsplit("/", 3)[1:-1])
        self._baseurl = baseurl
        self._name = _find(pkg_tag, "./main:name").text
        self._version = Version(
            _find(pkg_tag, "./main:version").attrib
        )
        self._size = int(_find(pkg_tag, "./main:size").attrib.get("package"))
        self._checksum = _get_checksum(pkg_tag)
        self._filename = _find(pkg_tag, "./main:location").attrib["href"]
        self._requires = _get_relations(pkg_tag, "requires")
        self._provides = _get_relations(pkg_tag, "provides")
        self._obsoletes = _get_relations(pkg_tag, "obsoletes")

    @property
    def name(self):
        return self._name

    @property
    def version(self):
        return self._version

    @property
    def size(self):
        return self._size

    @property
    def checksum(self):
        return self._checksum

    @property
    def filename(self):
        return self._filename

    @property
    def baseurl(self):
        return self.baseurl

    @property
    def requires(self):
        return self._requires

    @property
    def provides(self):
        return self._provides

    @property
    def obsoletes(self):
        return self._obsoletes
