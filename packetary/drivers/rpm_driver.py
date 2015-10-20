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
import multiprocessing
import os
import shutil

try:
    import createrepo
except ImportError:
    createrepo = None

import lxml.etree as etree
import six

from packetary.drivers.base import RepositoryDriverBase
from packetary.library.streams import GzipDecompress
from packetary.library import utils
from packetary.objects import FileChecksum
from packetary.objects import Package
from packetary.objects import PackageRelation
from packetary.objects import PackageVersion
from packetary.objects import Repository


urljoin = six.moves.urllib.parse.urljoin

# TODO(configurable option for drivers)
_CORE_GROUPS = ("core", "base")

_MANDATORY_TYPES = ("mandatory", "default")

_NAMESPACES = {
    "main": "http://linux.duke.edu/metadata/common",
    "md": "http://linux.duke.edu/metadata/repo",
    "rpm": "http://linux.duke.edu/metadata/rpm"
}


class CreaterepoCallBack(object):
    """Callback object for createrepo"""
    def __init__(self, logger):
        self.logger = logger

    def errorlog(self, msg):
        """Error log output."""
        self.logger.error(msg)

    def log(self, msg):
        """Logs message."""
        self.logger.info(msg)

    def progress(self, item, current, total):
        """"Progress bar."""
        pass


class RpmRepositoryDriver(RepositoryDriverBase):
    def parse_urls(self, urls):
        """Overrides method of superclass."""
        for url in urls:
            yield url.rstrip("/")

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
                name = tag.find("./main:name", _NAMESPACES).text
                consumer(Package(
                    repository=repository,
                    name=tag.find("./main:name", _NAMESPACES).text,
                    version=self._unparse_version_attrs(
                        tag.find("./main:version", _NAMESPACES).attrib
                    ),
                    filesize=int(
                        tag.find("./main:size", _NAMESPACES)
                        .attrib.get("package", -1)
                    ),
                    filename=tag.find(
                        "./main:location", _NAMESPACES
                    ).attrib["href"],
                    checksum=self._get_checksum(tag),
                    mandatory=name in mandatory,
                    requires=self._get_relations(tag, "requires"),
                    obsoletes=self._get_relations(tag, "obsoletes"),
                    provides=self._get_relations(tag, "provides")
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
            raise RuntimeError(
                "Please add createrepo package to python."
            )

        basepath = utils.get_path_from_url(repository.url)
        self.logger.info("rebuild repository in %s", basepath)
        md_config = createrepo.MetaDataConfig()
        try:
            md_config.workers = multiprocessing.cpu_count()
            md_config.directory = str(basepath)
            md_config.update = True
            mdgen = createrepo.MetaDataGenerator(
                config_obj=md_config, callback=CreaterepoCallBack(self.logger)
            )
            mdgen.doPkgMetadata()
            mdgen.doRepoMetadata()
            mdgen.doFinalMove()
        except createrepo.MDError as e:
            err_msg = six.text_type(e)
            self.logger.exception(
                "failed to create yum repository in %s: %s",
                basepath,
                err_msg
            )
            shutil.rmtree(
                os.path.join(md_config.outputdir, md_config.tempdir),
                ignore_errors=True
            )
            raise RuntimeError(
                "Failed to create yum repository in {0}."
                .format(err_msg))

    def fork_repository(self, connection, repository, destination,
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
        utils.ensure_dir_exist(destination)
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

    def _get_relations(self, pkg_tag, name):
        """Gets package relations by name from package tag.

        :param pkg_tag: the xml-tag with package description
        :param name: the relations name
        :return: list of PackageRelation objects
        """
        relations = list()
        append = relations.append
        tags_iter = pkg_tag.iterfind(
            "./main:format/rpm:%s/rpm:entry" % name,
            _NAMESPACES
        )
        for elem in tags_iter:
            append(PackageRelation.from_args(
                self._unparse_relation_attrs(elem.attrib)
            ))

        return relations

    def _get_checksum(self, pkg_tag):
        """Gets checksum from package tag."""
        checksum = dict.fromkeys(("md5", "sha1", "sha256"), None)
        checksum_tag = pkg_tag.find("./main:checksum", _NAMESPACES)
        checksum[checksum_tag.attrib["type"]] = checksum_tag.text
        return FileChecksum(**checksum)

    def _unparse_relation_attrs(self, attrs):
        """Gets the package relation from attributes.

        :param attrs: the relation tag attributes
        :return tuple(name, version_op, version_edge)
        """
        if "flags" not in attrs:
            return attrs['name'], None

        return (
            attrs['name'],
            attrs["flags"].lower(),
            self._unparse_version_attrs(attrs)
        )

    @staticmethod
    def _unparse_version_attrs(attrs):
        """Gets the package version from attributes.

        :param attrs: the relation tag attributes
        :return: the PackageVersion object
        """

        return PackageVersion(
            int(attrs.get("epoch", 0)),
            attrs.get("ver", "0.0").split("."),
            attrs.get("rel", "0").split(".")
        )
