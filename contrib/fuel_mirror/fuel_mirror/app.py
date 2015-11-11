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

from cliff import app
from cliff.commandmanager import CommandManager
import yaml


import fuel_mirror
from fuel_mirror.common import accessors
from fuel_mirror.common import utils


class Application(app.App):
    """Main cliff application class.

    Performs initialization of the command manager and
    configuration of basic engines.
    """

    config = None
    fuel = None
    repo_manager_accessor = None
    sources = None
    versions = None

    def build_option_parser(self, description, version, argparse_kwargs=None):
        """Specifies common cmdline arguments."""
        p_inst = super(Application, self)
        parser = p_inst.build_option_parser(description=description,
                                            version=version,
                                            argparse_kwargs=argparse_kwargs)

        parser.add_argument(
            "--config",
            default="/etc/fuel-mirror/config.yaml",
            metavar="PATH",
            help="Path to config file."
        )
        parser.add_argument(
            "-S", "--fuel-server",
            metavar="FUEL-SERVER",
            help="The public address of Fuel Master."
        )
        parser.add_argument(
            "--fuel-user",
            help="Fuel Master admin login."
                 " Alternatively, use env var KEYSTONE_USER)."
        )
        parser.add_argument(
            "--fuel-password",
            help="Fuel Master admin password."
                 " Alternatively, use env var KEYSTONE_PASSWORD)."
        )
        return parser

    def initialize_app(self, argv):
        """Initialises common options."""
        with open(self.options.config, "r") as stream:
            config = yaml.load(stream)

        fuel_default = utils.get_fuel_settings()
        self.config = config['common']
        self.versions = config["versions"]
        self.sources = config['sources']

        fuel_server = utils.first(
            self.options.fuel_server,
            self.config.get("fuel_server"),
            fuel_default["server"]
        )
        fuel_user = utils.first(
            self.options.fuel_user,
            fuel_default["user"]
        )
        fuel_password = utils.first(
            self.options.fuel_password,
            fuel_default["password"]
        )
        self.config.setdefault(
            "base_url", "http://{0}:8080".format(
                fuel_server.split(":", 1)[0]
            )
        )

        self.fuel = accessors.get_fuel_api_accessor(
            fuel_server,
            fuel_user,
            fuel_password
        )
        fuel_ver = self.fuel.FuelVersion.get_all_data()
        self.versions['mos_version'] = fuel_ver['release']
        self.versions['openstack_version'] = fuel_ver['openstack_version']

        self.repo_manager_accessor = accessors.get_packetary_accessor(
            threads_num=int(self.config.get('threads_num', 0)),
            retries_num=int(self.config.get('retries_num', 0)),
            ignore_errors_num=int(self.config.get('ignore_errors_num', 0)),
            http_proxy=self.config.get('http_proxy'),
            https_proxy=self.config.get('https_proxy'),
        )


def main(argv=None):
    """Entry point."""
    return Application(
        description="The utility to create local mirrors.",
        version=fuel_mirror.__version__,
        command_manager=CommandManager("fuel_mirror", convert_underscores=True)
    ).run(argv)


def debug(name, cmd_class, argv=None):
    """Helps to debug command."""
    import sys

    if argv is None:
        argv = sys.argv[1:]

    argv = [name] + argv + ["-v", "-v", "--debug"]
    cmd_mgr = CommandManager("test_fuel_mirror", convert_underscores=True)
    cmd_mgr.add_command(name, cmd_class)
    return Application(
        description="The fuel mirror utility test.",
        version="0.0.1",
        command_manager=cmd_mgr
    ).run(argv)
