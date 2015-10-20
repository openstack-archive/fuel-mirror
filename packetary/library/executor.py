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
import threading

from concurrent import futures


logger = logging.getLogger(__package__)

Executor = futures.ThreadPoolExecutor


class AsynchronousSection(object):
    """Allows calling function asynchronously with waiting on exit."""

    def __init__(self, executor, max_queue=0, ignore_errors_num=0):
        """Initialises.

        :param executor: the futures.Executor instance
        :param ignore_errors_num:
               number of errors which does not stop the execution
        """
        self.executor = executor
        self.ignore_errors_num = ignore_errors_num
        self.max_queue = max_queue
        self.errors = 0
        self.mutex = threading.Lock()
        self.condition = threading.Condition(self.mutex)
        self.tasks = set()

    def __enter__(self):
        self.errors = 0
        return self

    def __exit__(self, etype, *_):
        self.wait(etype is not None)

    def execute(self, func, *args, **kwargs):
        """Calls function asynchronously."""

        if 0 < self.max_queue:
            with self.condition:
                while self.max_queue < len(self.tasks):
                    self.condition.wait()

        if 0 <= self.ignore_errors_num < self.errors:
            raise RuntimeError("Too many errors.")

        fut = self.executor.submit(func, *args, **kwargs)
        self.tasks.add(fut)
        fut.add_done_callback(self.on_complete)

    def on_complete(self, fut):
        """Callback to handle task completion."""

        try:
            fut.result()
            delta = 0
        except Exception as e:
            delta = 1
            logger.exception(
                "Task failed: %s", six.text_type(e),
            )

        with self.condition:
            self.errors += delta
            self.tasks.discard(fut)
            self.condition.notify_all()

    def wait(self, ignore_errors=False):
        """Waits until all tasks will be completed.

        Do not use directly, will called from context manager.
        """
        futures.wait(self.tasks, return_when=futures.ALL_COMPLETED)

        # synchronise with callbacks
        with self.condition:
            while len(self.tasks) > 0:
                self.condition.wait()

        if not ignore_errors and self.errors > 0:
            raise RuntimeError(
                "Operations completed with errors. See log for more details."
            )
