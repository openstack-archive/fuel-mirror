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

import os.path
from string import Template

from cliff import command
from fuel_mirror.schemas.input_data_schema import SCHEMA
from jsonschema import validate
from jsonschema import ValidationError
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

    @staticmethod
    def validate_data(data, schema):
        """Validate the input data using jsonschema validation.

        :param data: the input data
        :param schema: jsonschema for validate input data
        """
        try:
            validate(data, schema)
        except ValidationError as ex:
            if len(ex.path) > 0:
                detail = ("Invalid input for field/attribute %(path)s."
                          " Value: %(value)s. %(message)s") % {
                    'path': ex.path.pop(), 'value': ex.instance,
                    'message': ex.message
                }
            else:
                detail = ex.message
            raise ValidationError(detail)

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
            data = yaml.load(Template(fd.read()).safe_substitute(
                mos_version=self.app.config["mos_version"],
                openstack_version=self.app.config["openstack_version"],
            ))
            self.validate_data(data, SCHEMA)
            return data

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
