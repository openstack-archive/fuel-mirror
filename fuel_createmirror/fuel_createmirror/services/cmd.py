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

import distutils.spawn as _spawn
import functools
import logging
import os
import subprocess
import time

from fuel_createmirror.options import options


logger = logging.getLogger(__package__)


if hasattr(subprocess, 'DEVNULL'):
    DEVNULL = subprocess.DEVNULL
else:
    DEVNULL = open(os.devnull, 'wb+')


CalledProcessError = subprocess.CalledProcessError


def find_executable(executable, path=None):
    """Finds executable in system pathes by name."""
    r = _spawn.find_executable(executable, path)
    if r is None:
        logger.warning("cannot find %s in search path", executable)
        r = executable
    return r


def _get_cmdline(cmd):
    """Get command line string."""
    if isinstance(cmd, (list, tuple)):
        return subprocess.list2cmdline(cmd)
    return str(cmd)


def _enable_dry_run(func):
    """Enables dry-run functional."""
    @functools.wraps(func)
    def wrapper(cmd, **kwargs):
        dry_run = kwargs.pop('dry_run', options.globals.dry_run)
        if dry_run:
            print(_get_cmdline(cmd))
            return 0, None, None
        else:
            return func(cmd, **kwargs)
    return wrapper


@_enable_dry_run
def _exec(cmd, **kwargs):
    """Executes command and retries if required."""

    retries = kwargs.pop('retries', options.globals.retries)
    sleep = kwargs.pop("sleep", options.globals.retry_delay)
    retryable = kwargs.pop('retryable', [])

    cmd_str = _get_cmdline(cmd)
    n = 1
    while True:
        logging.info("%s [%d/%d]", cmd_str, n, retries)
        p = subprocess.Popen(cmd, **kwargs)
        stdout, stderr = p.communicate()
        rcode = p.poll()
        if rcode != 0 and rcode in retryable and n < retries:
            n += 1
            time.sleep(sleep)
            continue
        return rcode, stdout, stderr


def get_output(cmd, **kwargs):
    """Executes command and returns stdout."""
    if "stdout" in kwargs:
        raise ValueError('stdout argument not allowed, it will be overridden.')
    kwargs['stdout'] = subprocess.PIPE
    kwargs.setdefault('stderr', subprocess.PIPE)
    rcode, stdout, stderr = _exec(cmd, **kwargs)
    if rcode != 0:
        cmd = _get_cmdline(_get_cmdline(cmd))
        logger.error("%s - completed with code %d: %s", cmd, rcode, stderr)
        raise CalledProcessError(rcode, cmd)
    return stdout


def execute(cmd, **kwargs):
    """Executes command."""
    kwargs.setdefault('stdout', DEVNULL)
    kwargs.setdefault('stderr', subprocess.PIPE)
    rcode, _, stderr = _exec(cmd, **kwargs)
    if rcode != 0:
        logger.error("%s - completed with code %d: %s",
                     _get_cmdline(cmd), rcode, stderr)
    return rcode


def check_execute(cmd, **kwargs):
    """Calls the command and raises if completed with error."""
    rcode = execute(cmd, **kwargs)
    if rcode != 0:
        raise CalledProcessError(rcode, _get_cmdline(cmd))
