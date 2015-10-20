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

from __future__ import with_statement

import logging
import six

from eventlet.greenpool import GreenPool


logger = logging.getLogger(__package__)


class AsynchronousSection(object):
    """Allows calling function asynchronously with waiting on exit."""

    MIN_POOL_SIZE = 1

    def __init__(self, size=0, ignore_errors_num=0):
        """Initialises.

        :param size: the max number of parallel tasks
        :param ignore_errors_num:
               number of errors which does not stop the execution
        """

        self.executor = GreenPool(max(size, self.MIN_POOL_SIZE))
        self.ignore_errors_num = ignore_errors_num
        self.errors = 0
        self.tasks = set()

    def __enter__(self):
        self.errors = 0
        return self

    def __exit__(self, etype, *_):
        self.wait(etype is not None)

    def execute(self, func, *args, **kwargs):
        """Calls function asynchronously."""
        if 0 <= self.ignore_errors_num < self.errors:
            raise RuntimeError("Too many errors.")

        gt = self.executor.spawn(func, *args, **kwargs)
        self.tasks.add(gt)
        gt.link(self.on_complete)

    def on_complete(self, gt):
        """Callback to handle task completion."""

        try:
            gt.wait()
        except Exception as e:
            self.errors += 1
            logger.exception("Task failed: %s", six.text_type(e))
        finally:
            self.tasks.discard(gt)

    def wait(self, ignore_errors=False):
        """Waits until all tasks will be completed.

        Do not use directly, will be called from context manager.
        """
        self.executor.waitall()
        if not ignore_errors and self.errors > 0:
            raise RuntimeError(
                "Operations completed with errors. See log for more details."
            )
