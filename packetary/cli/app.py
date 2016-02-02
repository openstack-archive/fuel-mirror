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

from cliff import app
from cliff.commandmanager import CommandManager

import packetary


class Application(app.App):
    """Main cliff application class.

    Performs initialization of the command manager and
    configuration of basic engines.
    """

    def build_option_parser(self, description, version, argparse_kwargs=None):
        """Specifies global options."""
        p_inst = super(Application, self)
        parser = p_inst.build_option_parser(description=description,
                                            version=version,
                                            argparse_kwargs=argparse_kwargs)

        parser.add_argument(
            "--ignore-errors-num",
            type=int,
            default=2,
            metavar="NUMBER",
            help="The number of errors that can be ignored."
        )
        parser.add_argument(
            "--retries-num",
            type=int,
            default=5,
            metavar="NUMBER",
            help="The number of retries."
        )
        parser.add_argument(
            "--retry-interval",
            type=int,
            default=2,
            metavar="SECONDS",
            help="The minimal time between retries in seconds."
        )
        parser.add_argument(
            "--threads-num",
            default=3,
            type=int,
            metavar="NUMBER",
            help="The number of threads."
        )
        parser.add_argument(
            "--http-proxy",
            default=None,
            metavar="http://username:password@proxy_host:proxy_port",
            help="The URL of http proxy."
        )
        parser.add_argument(
            "--https-proxy",
            default=None,
            metavar="https://username:password@proxy_host:proxy_port",
            help="The URL of https proxy."
        )
        return parser


def main(argv=None):
    return Application(
        description="The utility manages packages and repositories.",
        version=packetary.__version__,
        command_manager=CommandManager("packetary", convert_underscores=True)
    ).run(argv)


def debug(name, cmd_class, argv=None):
    """Helper for debugging single command without package installation."""
    import sys

    if argv is None:
        argv = sys.argv[1:]

    argv = [name] + argv + ["-v", "-v", "--debug"]
    cmd_mgr = CommandManager("test_packetary", convert_underscores=True)
    cmd_mgr.add_command(name, cmd_class)
    return Application(
        description="The utility manages packages and repositories.",
        version="0.0.1",
        command_manager=cmd_mgr
    ).run(argv)
