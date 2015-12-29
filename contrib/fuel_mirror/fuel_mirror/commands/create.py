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

from fuel_mirror.commands.base import BaseCommand
from fuel_mirror.common.url_builder import get_url_builder


class CreateCommand(BaseCommand):
    """Creates a new local mirrors."""

    def take_action(self, parsed_args):
        """See the Command.take_action."""
        data = self.load_data(parsed_args)
        repos_reqs = data.get('requirements', {})
        inheritance = data.get('inheritance', {})
        target_dir = self.app.config["target_dir"]

        total_stats = None
        for group_name, repos in self.get_groups(parsed_args, data):
            url_builder = get_url_builder(repos[0]["type"])
            repo_manager = self.app.repo_manager_accessor(
                repos[0]["type"], self.REPO_ARCH
            )
            if group_name in inheritance:
                child_group = inheritance[group_name]
                dependencies = [
                    url_builder.get_repo_url(x)
                    for x in data['groups'][child_group]
                ]
            else:
                dependencies = None

            stat = repo_manager.clone_repositories(
                [url_builder.get_repo_url(x) for x in repos],
                target_dir,
                dependencies,
                repos_reqs.get(group_name)
            )

            if total_stats is None:
                total_stats = stat
            else:
                total_stats += stat

        if total_stats is not None:
            self.stdout.write(
                "Packages processed: {0.copied}/{0.total}\n"
                .format(total_stats)
            )
        else:
            self.stdout.write(
                "No packages.\n"
            )


def debug(argv=None):
    """Helper for debugging Create command."""
    from fuel_mirror.app import debug

    return debug("create", CreateCommand, argv)


if __name__ == "__main__":
    debug()
