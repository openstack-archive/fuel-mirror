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
        """Specify command-specific options."""
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
        """Get the list of packages from repositories."""
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
