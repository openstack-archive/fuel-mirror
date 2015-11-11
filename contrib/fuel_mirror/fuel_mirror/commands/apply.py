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

from collections import defaultdict


from packetary.library.utils import localize_repo_url
import six

from fuel_mirror.commands.base import BaseCommand
from fuel_mirror.common.utils import lists_merge


class ApplyCommand(BaseCommand):
    """Applies local mirrors for Fuel-environments."""

    def get_parser(self, prog_name):
        parser = super(ApplyCommand, self).get_parser(prog_name)
        parser.add_argument(
            "--default",
            dest="set_default",
            action="store_true",
            default=False,
            help="Set as default repository."
        )
        parser.add_argument(
            "-e", "--env",
            dest="env", nargs="+",
            help="Fuel environment ID to update, "
                 "by default applies for all environments."
        )

        return parser

    def take_action(self, parsed_args):
        data = self.load_data(parsed_args)
        base_url = self.app.config["base_url"]
        osnames = data['osnames']
        repositories_by_os = defaultdict(list)
        for group_name, repos in self.get_groups(parsed_args, data):
            repo_osname = osnames.get(group_name, group_name)
            for repo_data in repos:
                new_data = repo_data.copy()
                new_data['uri'] = localize_repo_url(
                    base_url, repo_data['uri']
                )
                repositories_by_os[repo_osname].append(
                    new_data
                )

        for osname, repositories in six.iteritems(repositories_by_os):
            self.update_clusters(
                osname, repositories, parsed_args.env
            )
            if parsed_args.set_default:
                self.app.stdout.write("Updated defaults:\n")
                self.update_default_repos(osname, repositories)

        self.app.stdout.write("Operations have been completed successfully.\n")

    def update_clusters(self, osname, repositories, ids=None):
        """Applies repositories for existing clusters.

        :param osname: The target OS for repositories
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
            release_osname = release.data["operating_system"].lower()
            if release_osname != osname:
                continue

            modified = self._update_repository_settings(
                cluster.get_settings_data(),
                repositories
            )
            if modified:
                self.app.LOG.info(
                    "Try to update the Cluster '%s'",
                    cluster.data['name']
                )
                self.app.LOG.debug(
                    "The modified cluster attributes: %s",
                    modified
                )
                cluster.set_settings_data(modified)

    def update_default_repos(self, osname, repositories):
        """Applies repositories for existing default settings.

        :param osname: The target OS for repositories
        :param repositories: the meta information of repositories.
        """

        for release in self.app.fuel.Release.get_all():
            release_osname = release.data['operating_system'].lower()
            if release_osname != osname:
                continue

            if self._update_repository_settings(
                release.data["attributes_metadata"], repositories
            ):
                self.app.LOG.info(
                    "Try to update the Release '%s'",
                    release.data['name']
                )
                self.app.LOG.debug(
                    "The modified release attributes: %s",
                    release.data
                )
                # TODO(need to add method for release object)
                release.connection.put_request(
                    release.instance_api_path.format(release.id),
                    release.data
                )

    def _update_repository_settings(self, settings, repositories):
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


def debug(argv=None):
    """Helper for debugging Apply command."""
    from fuel_mirror.app import debug

    debug("apply", ApplyCommand, argv)


if __name__ == "__main__":
    debug()
