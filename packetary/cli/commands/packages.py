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


class ListOfPackages(BaseProduceOutputCommand):
    """Gets the list of packages from repository(es)."""

    columns = (
        "name",
        "repository",
        "version",
        "filename",
        "filesize",
        "checksum",
        "obsoletes",
        "provides",
        "requires",
    )

    def get_parser(self, prog_name):
        parser = super(ListOfPackages, self).get_parser(prog_name)

        bootstrap_group = parser.add_mutually_exclusive_group(required=False)
        bootstrap_group.add_argument(
            "-b", "--bootstrap",
            nargs='+',
            dest='bootstrap',
            metavar='PACKAGE [OP VERSION]',
            help="Space separated list of package relations, "
                 "to resolve the list of mandatory packages."
        )
        bootstrap_group.add_argument(
            "-B", "--bootstrap-file",
            type=read_lines_from_file,
            dest='bootstrap',
            metavar='FILENAME',
            help="Path to the file with list of package relations, "
                 "to resolve the list of mandatory packages."
        )

        requires_group = parser.add_mutually_exclusive_group(required=False)
        requires_group.add_argument(
            '-r', '--requires-url',
            nargs="+",
            dest='requires',
            metavar='URL',
            help="Space separated list of repository`s URL to calculate list "
                 "of dependencies, that will be used to filter packages")

        requires_group.add_argument(
            '-R', '--requires-file',
            type=read_lines_from_file,
            dest='requires',
            metavar='FILENAME',
            help="The path to the file with list of repository`s URL "
                 "to calculate list of dependencies, "
                 "that will be used to filter packages")
        return parser

    def take_repo_action(self, api, parsed_args):
        return api.get_packages(
            parsed_args.origins,
            parsed_args.requires,
            parsed_args.bootstrap,
        )


def debug(argv=None):
    """Helper to debug the ListOfPackages command."""
    from packetary.cli.app import debug
    debug("packages", ListOfPackages, argv)


if __name__ == "__main__":
    debug()
