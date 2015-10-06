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

from __future__ import print_function

import argparse
import logging
import sys

from fuel_createmirror import actions
from fuel_createmirror.options import options


logger = logging.getLogger(__package__)


def parse_args(args=None):
    """Parses command line arguments."""

    parser = argparse.ArgumentParser()
    parser.add_argument('-M', '--mos',
                        dest='backward.mos',
                        action='store_true',
                        default=False,
                        help='copy only MOS repository.')
    parser.add_argument('-U', '--ubuntu',
                        dest='backward.ubuntu',
                        action='store_true',
                        default=False,
                        help='copy system repository for ubuntu.')
    parser.add_argument("--os",
                        dest="filters.os",
                        choices=("ubuntu", "centos"),
                        action="append",
                        default=argparse.SUPPRESS,
                        help="select the linux distributive")
    parser.add_argument("--repo",
                        dest="filters.repo",
                        choices=("mos", "system"),
                        action="append",
                        default=argparse.SUPPRESS,
                        help='select the repository to copy.')
    parser.add_argument('-N', '--dry-run',
                        action='store_true',
                        dest='globals.dry_run',
                        default=argparse.SUPPRESS,
                        help='dry run')
    parser.add_argument('--no-progress',
                        action='store_true',
                        dest='globals.no_progress',
                        default=argparse.SUPPRESS,
                        help='do not show progress')
    parser.add_argument('--no-updates',
                        action='store_true',
                        dest='filters.noupdates',
                        default=argparse.SUPPRESS,
                        help='Skip all updates.')
    parser.add_argument('--full',
                        action='store_const',
                        const=set(),
                        dest='repositories.depends',
                        default=argparse.SUPPRESS,
                        help='copy all packages.')
    parser.add_argument('-T', '--target',
                        dest='repositories.localpath',
                        default=argparse.SUPPRESS,
                        help='the destination directory path')
    parser.add_argument('--log',
                        dest='logging.filename',
                        default=argparse.SUPPRESS,
                        help='the log file path')
    parser.add_argument('--log-level',
                        dest='logging.level',
                        choices=["debug", "info", "warning", "error"],
                        default=argparse.SUPPRESS,
                        help='the config file path')
    parser.add_argument('--config',
                        default='/etc/fuel-createmirror/config.yaml',
                        help='The config file path')

    options.clear()
    parser.parse_args(args, options)

    try:
        options.load_from_file(options.config)
    except Exception as e:
        parser.error(str(e))

    options.set_defaults()
    if options.backward.mos:
        options.filters.append("repo", "mos")
        options.filters.append("os", "ubuntu")
    if options.backward.ubuntu:
        options.filters.append("repo", "system")
        options.filters.append("os", "ubuntu")


def setup_log():
    """Setups the logging."""
    if options.logging.filename:
        logger.addHandler(logging.FileHandler(options.logging.filename))
    else:
        # by default write to stderr
        logger.addHandler(logging.StreamHandler())

    logger.setLevel(options.logging.level.upper())


def create_progress_observer():
    """Creates progress observer according to options."""
    if options.globals.no_progress or options.globals.dry_run:
        return lambda x, y: None

    def show_progress(message, value):
        print('\r{0}: {1}'.format(message, value), end='')

    return show_progress


def entry_point(func):
    """Makes entry point."""
    def wrapper():
        try:
            parse_args()
            setup_log()
            status = func(options, create_progress_observer())
        except (SystemExit, KeyboardInterrupt):
            status = 2
        except Exception as e:
            import traceback
            print("Unhandled exception: {0}.".format(e), file=sys.stderr)
            traceback.print_exc()
            if len(logger.handlers) > 0:
                logger.exception(str(e))
            status = 1
        sys.stderr.flush()
        sys.exit(status)

    return wrapper


createmirror = entry_point(actions.create_mirror)

if __name__ == '__main__':
    createmirror()
