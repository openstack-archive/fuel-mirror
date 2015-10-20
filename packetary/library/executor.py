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

import functools
import logging
import six
import threading


logger = logging.getLogger(__package__)


def _callback(func):
    @functools.wraps(func)
    def wrapper(e):
        try:
            func(e)
        except Exception as e:
            logger.exception("Exception in callback: %s", six.text_type(e))
    return wrapper


class Executor(object):
    """The download service, with concurrent downloads control."""

    _stopper = object()

    def __init__(self, options):
        threads_num = options.get('threads_count', 1)
        queue_size = options.get('queue_size') or 100
        self.tasks = six.moves.queue.Queue(maxsize=queue_size)
        self.threads = threads = []
        self._closed = False
        while threads_num > 0:
            t = threading.Thread(
                target=Executor._worker,
                args=(self,)
            )
            t.daemon = True
            t.start()
            threads.append(t)
            threads_num -= 1

    def execute(self, func, on_complete):
        """Executes in thread-pool."""
        if not self._closed:
            self.tasks.put((func, _callback(on_complete)))

    def shutdown(self, wait=True):
        """Shutdowns thread-pool."""
        if self._closed:
            return
        logger.debug("Shutting down executor...")
        threads_num = len(self.threads)
        while threads_num:
            self.tasks.put(self._stopper)
            threads_num -= 1

        if wait:
            logger.debug("Waiting threads...")
            while self.threads:
                self.threads.pop().join()
            logger.debug("Waiting jobs...")
            self.tasks.join()
        else:
            while self.threads:
                self.threads.pop()
        self._closed = True
        logger.debug("Completed.")

    def _worker(self):
        while True:
            try:
                task = self.tasks.get()
                if task is Executor._stopper:
                    break

                func, on_complete = task
                try:
                    if self._closed:
                        raise RuntimeError("Closed.")
                    func()
                    on_complete(None)
                except Exception as e:
                    on_complete(e)
            finally:
                self.tasks.task_done()


class ExecutionScope(object):
    def __init__(self, executor, ignore_errors):
        self.executor = executor
        self.ignore_errors = ignore_errors
        self.errors = 0
        self.counter = 0
        self.mutex = threading.Lock()
        self.condition = threading.Condition(self.mutex)

    def __enter__(self):
        self.errors = 0
        self.counter = 0
        return self

    def __exit__(self, etype, *_):
        self.wait(etype is not None)

    def execute(self, func, *args, **kwargs):
        if 0 <= self.ignore_errors < self.errors:
            raise RuntimeError("Too many errors.")

        self.executor.execute(
            functools.partial(func, *args, **kwargs), self.on_complete
        )
        self.mutex.acquire()
        try:
            self.counter += 1
        finally:
            self.mutex.release()

    def on_complete(self, err=None):
        if err is not None:
            logger.exception("Task failed: %s", six.text_type(err))
            delta = 1
        else:
            delta = 0

        self.condition.acquire()
        try:
            self.errors += delta
            self.counter -= 1
            self.condition.notify_all()
        finally:
            self.condition.release()

    def wait(self, ignore_errors=False):
        self.condition.acquire()
        try:
            while self.counter > 0:
                logger.debug("%d: tasks left - %d.", id(self), self.counter)
                self.condition.wait(5)
            logger.debug("%d: tasks left - 0.", id(self))
        finally:
            self.condition.release()

        if not ignore_errors and self.errors > 0:
            raise RuntimeError(
                "Operations completed with errors. See log for more details."
            )
