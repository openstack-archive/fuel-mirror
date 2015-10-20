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

import logging
import six
import threading

from concurrent import futures


logger = logging.getLogger(__package__)

Executor = futures.ThreadPoolExecutor


class AsynchronousSection(object):
    """Allows calling function asynchronously with waiting on exit."""

    def __init__(self, executor, ignore_errors_num):
        """Initialises.

        :param executor: the futures.Executor instance
        :param ignore_errors_num:
               number of errors which does not stop the execution
        """
        self.errors = 0
        self.executor = executor
        self.ignore_errors_num = ignore_errors_num
        self.mutex = threading.Lock()
        self.tasks = []

    def __enter__(self):
        self.errors = 0
        return self

    def __exit__(self, etype, *_):
        self.wait(etype is not None)

    def execute(self, func, *args, **kwargs):
        """Calls function asynchronously."""

        if 0 <= self.ignore_errors_num < self.errors:
            raise RuntimeError("Too many errors.")

        fut = self.executor.submit(func, *args, **kwargs)
        fut.add_done_callback(self.on_complete)
        self.tasks.append(fut)

    def on_complete(self, fut):
        """Callback to handle task completion."""

        try:
            fut.result()
        except Exception as e:
            self.mutex.acquire()
            try:
                self.errors += 1
            finally:
                self.mutex.release()

            logger.exception(
                "Task failed: %s", six.text_type(e),
            )

    def wait(self, ignore_errors=False):
        """Waits until all tasks will be completed.

        Do not use directly, will called from context manager.
        """
        futures.wait(self.tasks, return_when=futures.ALL_COMPLETED)
        self.tasks[:] = []

        if not ignore_errors and self.errors > 0:
            raise RuntimeError(
                "Operations completed with errors. See log for more details."
            )
