# -*- coding: utf-8 -*-

#    Copyright 2015 Mirantis, Inc.
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License along
#    with this program; if not, write to the Free Software Foundation, Inc.,
#    51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

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
            "--replace",
            dest="replace",
            action="store_true",
            default=False,
            help="Replace default repos with generated mirrors."
        )
        parser.add_argument(
            "-e", "--env",
            dest="env", nargs="+",
            help="Fuel environment ID to update, "
                 "by default applies for all environments."
        )

        return parser

    def take_action(self, parsed_args):
        if self.app.fuel is None:
            raise ValueError("Please specify the fuel-server option.")

        data = self.load_data(parsed_args)
        base_url = self.app.config["base_url"]
        release_match = data["fuel_release_match"]
        replace_repos = parsed_args.replace

        localized_repos = []
        for _, repos in self.get_groups(parsed_args, data):
            for repo_data in repos:
                new_data = repo_data.copy()
                new_data['uri'] = localize_repo_url(
                    base_url, repo_data['uri']
                )
                localized_repos.append(new_data)

        localized_repos.sort(key=lambda x: not x.pop('main', False))

        self.update_clusters(
            parsed_args.env,
            localized_repos,
            release_match,
            replace_repos=replace_repos)

        if parsed_args.set_default:
            self.update_release_repos(
                localized_repos,
                release_match,
                replace_repos=replace_repos)

        self.app.stdout.write(
            "Operations have been completed successfully.\n"
        )

    def update_clusters(self,
                        ids,
                        repositories,
                        release_match,
                        replace_repos=False):
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
                repositories,
                replace_repos=replace_repos)

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

    def update_release_repos(self,
                             repositories,
                             release_match,
                             replace_repos=False):
        """Applies repositories for existing default settings.

        :param repositories: the meta information of repositories
        :param release_match: The pattern to check Fuel Release
        """
        self.app.stdout.write("Updating the release repositories...\n")
        releases = six.moves.filter(
            lambda x: is_subdict(release_match, x.data),
            self.app.fuel.Release.get_all()
        )
        for release in releases:
            modified = self._update_repository_settings(
                release.data["attributes_metadata"],
                repositories,
                replace_repos=replace_repos)
            if modified:
                release.data["attributes_metadata"] = modified
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

    def _update_repository_settings(self,
                                    settings,
                                    repositories,
                                    replace_repos=False):
        """Updates repository settings.

        :param settings: the target settings
        :param repositories: the meta of repositories
        """
        editable = settings["editable"]
        if 'repo_setup' not in editable:
            self.app.LOG.info('Attributes are read-only.')
            return

        repos_attr = editable["repo_setup"]["repos"]
        if replace_repos:
            repos_attr['value'] = repositories
        else:
            lists_merge(repos_attr['value'], repositories, "name")

        # NOTE(akostrikov) That assignment is only for informational purpose.
        settings["editable"]["repo_setup"]["repos"] = repos_attr

        return settings


def debug(argv=None):
    """Helper for debugging Apply command."""
    from fuel_mirror.app import debug

    return debug("apply", ApplyCommand, argv)


if __name__ == "__main__":
    debug()
