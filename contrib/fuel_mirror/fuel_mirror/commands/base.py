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
import six
import yaml


class BaseCommand(command.Command):
    """The Base command for fuel-mirror."""
    REPO_ARCH = "x86_64"
    REPO_DIR = "mirrors"

    @property
    def stdout(self):
        """Shortcut for self.app.stdout."""
        return self.app.stdout

    def get_parser(self, prog_name):
        """Specifies common options."""
        parser = super(BaseCommand, self).get_parser(prog_name)
        parser.add_argument(
            nargs=1,
            dest='input',
            help="The path to file with input data."
        )
        parser.add_argument(
            "-R", "--repository",
            dest="repositories",
            nargs='+',
            help="The repository names, by default use all of repositories."
        )
        return parser

    def load_data(self, parsed_args):
        """Load the input data.

        :param parsed_args: the command-line arguments
        :return: the input data
        """
        input_file = os.path.join(
            self.app.config.get('working_dir', os.path.curdir),
            parsed_args.input[0]
        )
        # TODO(add input data validation scheme)
        with open(input_file, "r") as fd:
            return yaml.load(Template(fd.read()).safe_substitute(
                mos_version=self.app.config["mos_version"],
                openstack_version=self.app.config["openstack_version"],
            ))

    @classmethod
    def get_repositories(cls, parsed_args, data):
        """Gets the repositories from input data.

        :param parsed_args: the command-line arguments
        :param data: the input data
        :return: the sequence of repositories
        """
        all_repositories = data['repositories']
        if parsed_args.repositories:
            repositories = (
                (x, all_repositories[x]) for x in parsed_args.repositories
            )
        else:
            repositories = six.iteritems(all_repositories)

        return repositories

    @classmethod
    def build_repo_url(cls, prefix, suffix, osname):
        """Builds repository url.

        :param prefix: the repository`s url prefix
        :param suffix: the repository`s suffix
        :param osname: the target OS
        :return: the repository`s base URL
        """
        if suffix != osname:
            return "/".join((
                prefix.rstrip("/"), cls.REPO_DIR, suffix, osname
            ))
        return "/".join((prefix.rstrip("/"), cls.REPO_DIR, suffix))
