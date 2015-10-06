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

import logging
import os

from . import cmd


logger = logging.getLogger(__package__)

rsync = cmd.find_executable("rsync")

# see "man rsync" for more details.
_RETRYABLE_ERRORS = set((10, 11, 12, 23, 30))


def copy(url, dst, size=None, sha1=None, **kwargs):
    """Copies remote file to local via rsync."""
    logger.debug("rsync.copy: %s %s (%s, %s)", url, dst, size, sha1)
    target_dir = os.path.dirname(dst)
    if not os.path.exists(target_dir):
        cmd.check_execute(['mkdir', '-p', target_dir], **kwargs)

    return cmd.check_execute([
        rsync, '--no-motd', '--perms', '--copy-links',
        '--times', '--hard-links', '--sparse', '--safe-links',
        url, dst
    ], retryable=_RETRYABLE_ERRORS, **kwargs)


def exists(url, **kwargs):
    """Checks that remote file exist."""
    logger.debug("rsync.exists: %s", url)
    kwargs['dry_run'] = False
    try:
        cmd.check_execute(
            [rsync, '--no-motd', '--list-only', url],
            retryable=_RETRYABLE_ERRORS, **kwargs
        )
        return True
    except cmd.CalledProcessError as e:
        if e.returncode != 2:
            raise
    return False


def _filter_files(line):
    """Check that line contains information about file."""
    return line and not line.startswith('d')


def _get_filepath(line):
    """extracts filename from line."""
    return line.rsplit(' ', 1)[-1]
