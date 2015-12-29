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

from packetary.cli.commands.base import BaseProduceOutputCommand
from packetary.cli.commands.utils import read_lines_from_file


class ListOfUnresolved(BaseProduceOutputCommand):
    """Gets the list of external dependencies for repository(es)."""

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
