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
        scope1 = executor.AsynchronousSection(self.executor, 0)
        scope2 = executor.AsynchronousSection(self.executor, 0)
        event = threading.Event()
        scope1.execute(event.wait)
        scope2.execute(time.sleep, 0)
        scope2.wait()
        event.set()
        scope1.wait()

    def test_ignore_errors(self, logger):
        scope = executor.AsynchronousSection(self.executor, 1)
        scope.execute(_raise_value_error)
        scope.execute(time.sleep, 0)
        scope.wait(ignore_errors=True)
        self.assertEqual(1, scope.errors)
        logger.exception.assert_called_with(
            "Task failed: %s", "error"
        )

    def test_fail_if_too_many_errors(self, _):
        scope = executor.AsynchronousSection(self.executor, 0)
        scope.execute(_raise_value_error)
        scope.wait(ignore_errors=True)
        with self.assertRaisesRegexp(RuntimeError, "Too many errors"):
            scope.execute(_raise_value_error)

        with self.assertRaisesRegexp(
                RuntimeError, "Operations completed with errors"):
            scope.wait(ignore_errors=False)
