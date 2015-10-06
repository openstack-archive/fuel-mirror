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

from . import cmd


curl = cmd.find_executable("curl")

logger = logging.getLogger(__package__)
# see "man curl" for more details.
_RETRYABLE_ERRORS = set((5, 6, 7, 26, 28, 89))


def copy(url, dst, size=None, sha1=None, **kwargs):
    logger.debug("copy: %s %s (%s, %s)", url, dst, size, sha1)
    return cmd.check_execute(
        [curl, '--create-dirs', '-o', dst, url],
        retryable=_RETRYABLE_ERRORS, **kwargs
    )


def exists(url, **kwargs):
    logger.debug("exists: %s", url)
    kwargs['dry_run'] = False
    code = cmd.get_output(
        [curl, '-I', '-s', '-o', '/dev/null', '-w', "%{http_code}", url],
        retryable=_RETRYABLE_ERRORS, **kwargs
    )
    code = int(code)
    if code < 300:
        return True
    if code == 404:
        return False
    raise RuntimeError("Unexpected http status: {0}".format(code))
