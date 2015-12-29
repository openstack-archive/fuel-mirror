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

import os.path
from string import Template

from cliff import command
import yaml


class BaseCommand(command.Command):
    """The Base command for fuel-mirror."""
    REPO_ARCH = "x86_64"

    @property
    def stdout(self):
        """Shortcut for self.app.stdout."""
        return self.app.stdout

    def get_parser(self, prog_name):
        """Specifies common options."""
        parser = super(BaseCommand, self).get_parser(prog_name)

        input_group = parser.add_mutually_exclusive_group(required=True)
        input_group.add_argument(
            '-I', '--input-file',
            metavar='PATH',
            help='The path to file with input data.')

        input_group.add_argument(
            '-P', '--pattern',
            metavar='NAME',
            help='The builtin input file name.'
        )

        parser.add_argument(
            "-G", "--group",
            dest="groups",
            required=True,
            nargs='+',
            help="The name of repository groups."
        )
        return parser

    def resolve_input_pattern(self, pattern):
        """Gets the full path to input file by pattern.

        :param pattern: the config file name without ext
        :return: the full path
        """
        return os.path.join(
            self.app.config['pattern_dir'], pattern + ".yaml"
        )

    def load_data(self, parsed_args):
        """Load the input data.

        :param parsed_args: the command-line arguments
        :return: the input data
        """
        if parsed_args.pattern:
            input_file = self.resolve_input_pattern(parsed_args.pattern)
        else:
            input_file = parsed_args.input_file

        # TODO(add input data validation scheme)
        with open(input_file, "r") as fd:
            return yaml.load(Template(fd.read()).safe_substitute(
                mos_version=self.app.config["mos_version"],
                openstack_version=self.app.config["openstack_version"],
            ))

    @classmethod
    def get_groups(cls, parsed_args, data):
        """Gets repository groups from input data.

        :param parsed_args: the command-line arguments
        :param data: the input data
        :return: the sequence of pairs (group_name, repositories)
        """
        all_groups = data['groups']
        return (
            (x, all_groups[x]) for x in parsed_args.groups if x in all_groups
        )
