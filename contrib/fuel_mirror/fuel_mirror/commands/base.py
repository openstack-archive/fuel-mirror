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

import abc
import os

from cliff import command
import six

from fuel_mirror.common.url_builder import get_url_builder
from fuel_mirror.common.utils import filter_from_choices
from fuel_mirror.common.utils import find_by_criteria
from fuel_mirror.common.utils import lists_merge


@six.add_metaclass(abc.ABCMeta)
class BaseCommand(command.Command):
    """The Base command for fuel-mirror."""
    REPO_ARCH = "x86_64"

    @property
    def stdout(self):
        """Shortcut for self.app.stdout."""
        return self.app.stdout

    def get_parser(self, prog_name):
        """Specifies common options."""
        parser = super(BaseCommand, self).get_parser(prog_name)
        repos_group = parser.add_argument_group()
        repos_group.add_argument(
            "-M", "--mos",
            dest="sources",
            action="append_const",
            const="mos",
            help="Clones the repositories for MOS."
        )
        repos_group.add_argument(
            "-B", "--base",
            dest="sources",
            action="append_const",
            const="system",
            help="Clones the repositories for base system."
        )

        dist_group = parser.add_argument_group()
        dist_group.add_argument(
            "-U", "--ubuntu",
            dest="releases",
            action="append_const",
            const="ubuntu",
            help="Clones the repositories for Ubuntu."
        )
        dist_group.add_argument(
            "-C", "--centos",
            dest="releases",
            action="append_const",
            const="centos",
            help="Clones the repositories for CentOs."
        )
        return parser

    def filter_repositories(self, parsed_args):
        """Filter origin repositories according to cmdline arguments.

        :param parsed_args: the command-line arguments
        :return: the sequence of repositories to process
        """
        sources = self.app.sources

        if parsed_args.sources:
            sources_filter = set(parsed_args.sources)
            if "system" in sources_filter:
                sources_filter.remove("system")
                sources = (x for x in sources if x["name"] == x["osname"])
            if sources_filter:
                sources = filter_from_choices(
                    parsed_args.sources, sources, key="name"
                )
        if parsed_args.releases:
            sources = filter_from_choices(
                parsed_args.releases, sources, key="osname"
            )
        return sources

    def get_repositories_for_fuel(self, parsed_args):
        """Get repositories to in fuel format.

        :param parsed_args: the command-line arguments
        :return: the description of repositories
        """
        base_url = self.app.config["base_url"]
        if base_url.endswith("/"):
            base_url = base_url[:-1]

        result = dict()
        for config in self.filter_repositories(parsed_args):
            name = config["name"]
            osname = config["osname"]
            url_parser = get_url_builder(config["type"])
            folder = (name, osname) if osname != name else (name,)
            url = "/".join((base_url, "mirror") + folder)
            os_repos = result.setdefault(osname, [])
            for repo in config["repositories"]:
                os_repos.append(
                    url_parser.get_repo_config(
                        name,
                        url, repo, self.REPO_ARCH,
                        **self.app.versions
                    )
                )
        return result


@six.add_metaclass(abc.ABCMeta)
class CopyRepositoryCommand(BaseCommand):
    """Base command for copying repository."""

    def get_parser(self, prog_name):
        parser = super(CopyRepositoryCommand, self).get_parser(prog_name)
        parser.add_argument(
            "-F", "--full",
            dest="partial",
            action="store_false",
            default=True,
            help="Do no analyze dependencies, create full mirror."
        )
        return parser

    def copy_repositories(self, parsed_args):
        """Copies repositories to local folder."""
        target_dir = self.app.config["target_dir"]

        total = None
        for repo_config in self.filter_repositories(parsed_args):
            stat = self._copy_repository(
                repo_config,
                target_dir,
                parsed_args.partial,
            )
            if total is None:
                total = stat
            else:
                total += stat

        if total is not None:
            self.stdout.write(
                "Packages processed: {0.copied}/{0.total}\n".format(total)
            )
        else:
            self.stdout.write(
                "No packages.\n"
            )

    def _copy_repository(self, config, folder, partial):
        """Copies one repository."""
        name = config["name"]
        osname = config["osname"]
        baseurl = config["baseurl"]
        repo_type = config["type"]
        repo_manager = self.app.repo_manager_accessor(
            repo_type, self.REPO_ARCH
        )
        url_parser = get_url_builder(repo_type)
        sub_folder = (name, osname) if osname != name else (name,)
        destination = os.path.abspath(
            os.path.join(folder, "mirror", *sub_folder)
        )

        if partial and 'master' in config:
            master = find_by_criteria(
                self.app.sources,
                name=config["master"],
                osname=osname,
                type=repo_type
            )
            deps = url_parser.get_urls(
                master["baseurl"],
                master["repositories"],
                **self.app.versions
            )
            requires = config.get('bootstrap')
        else:
            deps = None
            requires = None

        repository_urls = []
        for repo in config["repositories"]:
            repository_urls.append(
                url_parser.get_repo_url(baseurl, repo, **self.app.versions)
            )
        stat = repo_manager.clone_repositories(
            repository_urls,
            destination,
            deps,
            requires
        )
        # optimisation, in next iteration will read from local repository
        config["baseurl"] = "file://" + destination
        self.app.configure_logging()
        return stat


class FuelCommandMixin(object):
    """Adds methods to communicate with the Fuel backend."""
    app = None

    def update_clusters(self, repositories, ids=None):
        """Applies repositories for existing clusters.

        :param repositories: the meta information of repositories.
        :param ids: the cluster ids.
        """
        self.app.LOG.info("Updating repositories...")

        if ids:
            clusters = self.app.fuel.Environment.get_by_ids(ids)
        else:
            clusters = self.app.fuel.Environment.get_all()

        for cluster in clusters:
            release = self.app.fuel.Release.get_by_ids(
                [cluster.data["release_id"]]
            )[0]
            osname = release.data["operating_system"].lower()
            if osname not in repositories:
                self.app.LOG.info(
                    'Cluster "%s" does not relevant repositories was updated.',
                    cluster.data["name"]
                )
                continue

            modified = self.update_repository_settings(
                cluster.get_settings_data(),
                repositories[osname]
            )
            if modified:
                self.app.LOG.debug(
                    "Try to update cluster attributes: %s", modified
                )
                cluster.set_settings_data(modified)

    def update_default_repos(self, repositories):
        """Applies repositories for existing default settings.

        :param repositories: the meta information of repositories.
        """

        for release in self.app.fuel.Release.get_all():
            osname = release.data['operating_system'].lower()
            if osname not in repositories:
                self.app.LOG.info(
                    'Release "%s" does not relevant repositories was updated.',
                    release.data["name"]
                )
                continue

            if self.update_repository_settings(
                release.data["attributes_metadata"], repositories[osname]
            ):
                # TODO(need to add method for release object)
                release.connection.put_request(
                    release.instance_api_path.format(release.id),
                    release.data
                )

    def update_repository_settings(self, settings, repositories):
        """Updates repository settings.

        :param settings: the target settings.
        :param repositories: the meta of repositories
        """
        editable = settings["editable"]
        if 'repo_setup' not in editable:
            self.app.LOG.info('Attributes is read-only.')
            return

        repos_attr = editable["repo_setup"]["repos"]
        lists_merge(repos_attr['value'], repositories, "name")
        return {"editable": {"repo_setup": {"repos": repos_attr}}}
