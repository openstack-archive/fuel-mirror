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
        self.results = []

    def test_isolation(self, _):
        section1 = executor.AsynchronousSection()
        section2 = executor.AsynchronousSection()
        event = threading.Event()
        section1.execute(event.wait)
        section2.execute(time.sleep, 0)
        section2.wait()
        event.set()
        section1.wait()

    def test_ignore_errors(self, logger):
        section = executor.AsynchronousSection(ignore_errors_num=1)
        section.execute(_raise_value_error)
        section.execute(time.sleep, 0)
        section.wait(ignore_errors=True)
        logger.exception.assert_called_with(
            "error details.", exc_info=mock.ANY
        )

    def test_fail_if_too_many_errors(self, _):
        section = executor.AsynchronousSection(size=1, ignore_errors_num=0)
        section.execute(_raise_value_error)
        time.sleep(0)  # switch context
        with self.assertRaisesRegexp(RuntimeError, "Too many errors"):
            section.execute(time.sleep, 0)

        with self.assertRaisesRegexp(
                RuntimeError, "Operations completed with errors"):
            section.wait(ignore_errors=False)
