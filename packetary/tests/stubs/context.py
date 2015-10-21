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

from packetary.tests.stubs.executor import Executor


class Context(object):
    def __init__(self):
        self.executor = Executor()
        self.connections = mock.MagicMock()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.shutdown()

    def create_scope(self, ignore_errors=None):
        return self.executor

    def shutdown(self, wait=True):
        pass
