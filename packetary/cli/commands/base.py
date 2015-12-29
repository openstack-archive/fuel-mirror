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

import abc

from cliff import command
import six

from packetary.cli.commands.utils import make_display_attr_getter
from packetary.cli.commands.utils import read_lines_from_file
from packetary import RepositoryApi


@six.add_metaclass(abc.ABCMeta)
class BaseRepoCommand(command.Command):
    """Super class for packetary commands."""

    @property
    def stdout(self):
        """Shortcut for self.app.stdout."""
        return self.app.stdout

    def get_parser(self, prog_name):
        """Specifies common options."""
        parser = super(BaseRepoCommand, self).get_parser(prog_name)
        parser.add_argument(
            '-t',
            '--type',
            type=str,
            choices=['deb', 'rpm'],
            metavar='TYPE',
            default='deb',
            help='The type of repository.')

        parser.add_argument(
            '-a',
            '--arch',
            type=str,
            choices=["x86_64", "i386"],
            metavar='ARCHITECTURE',
            default="x86_64",
            help='The target architecture.')

        origin_gr = parser.add_mutually_exclusive_group(required=True)
        origin_gr.add_argument(
            '-o', '--origin-url',
            nargs="+",
            dest='origins',
            type=six.text_type,
            metavar='URL',
            help='Space separated list of URLs of origin repositories.')

        origin_gr.add_argument(
            '-O', '--origin-file',
            type=read_lines_from_file,
            dest='origins',
            metavar='FILENAME',
            help='The path to file with URLs of origin repositories.')

        return parser

    def take_action(self, parsed_args):
        """See the Command.take_action.

        :param parsed_args: the command-line arguments
        :return: the result of take_repo_action
        :rtype: object
        """
        return self.take_repo_action(
            RepositoryApi.create(
                self.app_args, parsed_args.type, parsed_args.arch
            ),
            parsed_args
        )

    @abc.abstractmethod
    def take_repo_action(self, api, parsed_args):
        """Takes action on repository.

        :param api: the RepositoryApi instance
        :param parsed_args: the command-line arguments
        :return: the action result
        """


class BaseProduceOutputCommand(BaseRepoCommand):
    columns = None

    def get_parser(self, prog_name):
        parser = super(BaseProduceOutputCommand, self).get_parser(prog_name)

        group = parser.add_argument_group(
            title='output formatter',
            description='output formatter options',
        )
        group.add_argument(
            '-c', '--column',
            nargs='+',
            choices=self.columns,
            dest='columns',
            metavar='COLUMN',
            default=[],
            help='Space separated list of columns to include.',
        )
        group.add_argument(
            '-s',
            '--sort-columns',
            type=str,
            nargs='+',
            choices=self.columns,
            metavar='SORT_COLUMN',
            default=[self.columns[0]],
            help='Space separated list of keys for sorting '
                 'the data.'
        )
        group.add_argument(
            '--sep',
            type=six.text_type,
            metavar='ROW SEPARATOR',
            default=six.text_type('; '),
            help='The row separator.'
        )

        return parser

    def produce_output(self, parsed_args, data):
        indexes = dict(
            (c, i) for i, c in enumerate(self.columns)
        )
        sort_index = [indexes[c] for c in parsed_args.sort_columns]
        if isinstance(data, list):
            data.sort(key=lambda x: [x[i] for i in sort_index])
        else:
            data = sorted(data, key=lambda x: [x[i] for i in sort_index])

        if parsed_args.columns:
            include_index = [
                indexes[c] for c in parsed_args.columns
            ]
            data = ((row[i] for i in include_index) for row in data)
            columns = parsed_args.columns
        else:
            columns = self.columns

        stdout = self.stdout
        sep = parsed_args.sep

        # header
        stdout.write("# ")
        stdout.write(sep.join(columns))
        stdout.write("\n")

        for row in data:
            stdout.write(sep.join(row))
            stdout.write("\n")

    def run(self, parsed_args):
        # Use custom output producer.
        # cliff.lister with default formatters does not work
        # with large arrays of data, because it does not support streaming
        # TODO(implement custom formatter)

        formatter = make_display_attr_getter(self.columns)
        data = six.moves.map(formatter, self.take_action(parsed_args))
        self.produce_output(parsed_args, data)
        return 0

    @abc.abstractmethod
    def take_repo_action(self, driver, parsed_args):
        """See Command.take_repo_action."""
