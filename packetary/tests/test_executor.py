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

import mock
import six
import threading
import time

from packetary.library import executor
from packetary.tests import base


def _raise_value_error(*_):
    raise ValueError("error")


@mock.patch("packetary.library.executor.logger")
class TestAsynchronousSection(base.TestCase):
    def setUp(self):
        super(TestAsynchronousSection, self).setUp()
        self.executor = executor.Executor(max_workers=2)
        self.results = []

    def test_isolation(self, _):
        section1 = executor.AsynchronousSection(self.executor)
        section2 = executor.AsynchronousSection(self.executor)
        event = threading.Event()
        section1.execute(event.wait)
        section2.execute(time.sleep, 0)
        section2.wait()
        event.set()
        section1.wait()

    def test_ignore_errors(self, logger):
        section = executor.AsynchronousSection(self.executor, 0, 1)
        section.execute(_raise_value_error)
        section.execute(time.sleep, 0)
        section.wait(ignore_errors=True)
        self.assertEqual(1, section.errors)
        logger.exception.assert_called_with(
            "Task failed: %s", "error"
        )

    def test_fail_if_too_many_errors(self, _):
        section = executor.AsynchronousSection(
            self.executor, ignore_errors_num=0
        )
        section.execute(_raise_value_error)
        section.wait(ignore_errors=True)
        with self.assertRaisesRegexp(RuntimeError, "Too many errors"):
            section.execute(time.sleep, 0)

        with self.assertRaisesRegexp(
                RuntimeError, "Operations completed with errors"):
            section.wait(ignore_errors=False)

    def test_limits(self, _):
        with executor.AsynchronousSection(self.executor, 2) as section:
            for _ in six.moves.range(10):
                section.execute(time.sleep, 0)
            # the queue limit is max_size + 1
            self.assertLessEqual(len(section.tasks), 3)
