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

from fuel_mirror.commands.base import CopyRepositoryCommand
from fuel_mirror.commands.base import FuelCommandMixin


class CreateCommand(CopyRepositoryCommand, FuelCommandMixin):
    """Creates a new local mirrors."""

    def get_parser(self, prog_name):
        parser = super(CreateCommand, self).get_parser(prog_name)
        parser.add_argument(
            "--default",
            dest="set_default",
            action="store_true",
            default=False,
            help="Set as default repository."
        )
        parser.add_argument(
            "--no-apply",
            dest="apply",
            action="store_false",
            default=True,
            help="Do not apply for environments."
        )
        parser.add_argument(
            "-e", "--env",
            dest="env", nargs="+",
            help="Fuel environment ID to update"
        )

        return parser

    def take_action(self, parsed_args):
        """See the Command.take_action."""
        self.copy_repositories(parsed_args)
        repos = self.get_repositories_for_fuel(parsed_args)
        if parsed_args.apply:
            self.app.stdout.write("Updated clusters:\n")
            self.update_clusters(repos, parsed_args.env)
        if parsed_args.set_default:
            self.app.stdout.write("Updated defaults:\n")
            self.update_default_repos(repos)
        self.app.stdout.write("Operations have been completed successfully.\n")


def debug(argv=None):
    """Helper for debugging Create command."""
    from fuel_mirror.app import debug

    debug("create", CreateCommand, argv)


if __name__ == "__main__":
    debug()
