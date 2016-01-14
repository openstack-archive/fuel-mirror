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
