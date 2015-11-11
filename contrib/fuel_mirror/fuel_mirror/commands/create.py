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

    debug("create", CreateCommand, argv)


if __name__ == "__main__":
    debug()
