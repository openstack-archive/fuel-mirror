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

from packetary.cli.commands.base import BaseProduceOutputCommand
from packetary.cli.commands.utils import read_lines_from_file


class ListOfUnresolved(BaseProduceOutputCommand):
    """Get the list of external dependencies for repository."""

    columns = (
        "name",
        "version",
        "alternative",
    )

    def get_parser(self, prog_name):
        parser = super(ListOfUnresolved, self).get_parser(prog_name)
        main_group = parser.add_mutually_exclusive_group(required=False)
        main_group.add_argument(
            '-m', '--main-url',
            nargs="+",
            dest='main',
            metavar='URL',
            help='Space separated list of URLs of repository(es) '
                 ' that are used to resolve dependencies.')

        main_group.add_argument(
            '-M', '--main-file',
            type=read_lines_from_file,
            dest='main',
            metavar='FILENAME',
            help='The path to the file, that contains '
                 'list of URLs of repository(es) '
                 ' that are used to resolve dependencies.')
        return parser

    def take_repo_action(self, api, parsed_args):
        """Overrides the method of superclass."""
        return api.get_unresolved_dependencies(
            parsed_args.origins,
            parsed_args.main,
        )


def debug(argv=None):
    """Helper to debug the ListOfUnresolved command."""

    from packetary.cli.app import debug
    debug("unresolved", ListOfUnresolved, argv)


if __name__ == "__main__":
    debug()
