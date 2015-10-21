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


class CallbacksAdapter(mock.MagicMock):
    """Helper to return data through callback."""

    def __call__(self, *args, **kwargs):
        if len(args) > 0:
            callback = args[-1]
        else:
            callback = None

        if not callable(callback):
            return super(CallbacksAdapter, self).__call__(*args, **kwargs)

        args = args[:-1]
        data = super(CallbacksAdapter, self).__call__(*args, **kwargs)

        if isinstance(data, list):
            for d in data:
                callback(d)
        else:
            callback(data)
