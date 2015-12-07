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

import six

from packetary.library.utils import localize_repo_url

from fuel_mirror.commands.base import BaseCommand
from fuel_mirror.common.utils import is_subdict
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
        base_url = self.app.config["base_repos_url"]
        localized_repos = []
        for _, repos in self.get_groups(parsed_args, data):
            for repo_data in repos:
                new_data = repo_data.copy()
                new_data['uri'] = localize_repo_url(
                    base_url, repo_data['uri']
                )
                localized_repos.append(new_data)

        release_match = data["fuel_release_match"]
        self.update_clusters(parsed_args.env, localized_repos, release_match)
        if parsed_args.set_default:
            self.update_default_repos(localized_repos, release_match)

        self.app.stdout.write(
            "Operations have been completed successfully.\n"
        )

    def update_clusters(self, ids, repositories, release_match):
        """Applies repositories for existing clusters.

        :param ids: the cluster ids.
        :param repositories: the meta information of repositories
        :param release_match: The pattern to check Fuel Release
        """
        self.app.stdout.write("Updating the Cluster repositories...\n")

        if ids:
            clusters = self.app.fuel.Environment.get_by_ids(ids)
        else:
            clusters = self.app.fuel.Environment.get_all()

        for cluster in clusters:
            releases = six.moves.filter(
                lambda x: is_subdict(release_match, x.data),
                self.app.fuel.Release.get_by_ids([cluster.data["release_id"]])
            )
            if next(releases, None) is None:
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

    def update_default_repos(self, repositories, release_match):
        """Applies repositories for existing default settings.

        :param repositories: the meta information of repositories
        :param release_match: The pattern to check Fuel Release
        """
        self.app.stdout.write("Updating the default repositories...\n")
        releases = six.moves.filter(
            lambda x: is_subdict(release_match, x.data),
            self.app.fuel.Release.get_all()
        )
        for release in releases:
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

        :param settings: the target settings
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
