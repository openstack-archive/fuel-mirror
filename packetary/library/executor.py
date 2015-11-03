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
import sys

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
        self.errors = []
        self.tasks = set()

    def __enter__(self):
        self.errors[:] = []
        return self

    def __exit__(self, etype, *_):
        self.wait(etype is not None)

    def execute(self, func, *args, **kwargs):
        """Calls function asynchronously."""
        if 0 <= self.ignore_errors_num < len(self.errors):
            raise RuntimeError("Too many errors.")

        gt = self.executor.spawn(func, *args, **kwargs)
        self.tasks.add(gt)
        gt.link(self.on_complete)
        return gt

    def on_complete(self, gt):
        """Callback to handle task completion."""

        try:
            gt.wait()
        except Exception as e:
            logger.error("Task failed: %s", six.text_type(e))
            self.errors.append(sys.exc_info())
        finally:
            self.tasks.discard(gt)

    def wait(self, ignore_errors=False):
        """Waits until all tasks will be completed.

        Do not use directly, will be called from context manager.
        """
        self.executor.waitall()
        if len(self.errors) > 0:
            for exc_info in self.errors:
                logger.exception("error details.", exc_info=exc_info)

            self.errors[:] = []
            if not ignore_errors:
                raise RuntimeError(
                    "Operations completed with errors.\n"
                    "See log for more details."
                )
