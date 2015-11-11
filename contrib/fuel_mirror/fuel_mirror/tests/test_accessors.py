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

from fuel_mirror.common import accessors
from fuel_mirror.tests import base


class TestAccessors(base.TestCase):
    def test_get_packetary_accessor(self):
        packetary = mock.MagicMock()
        with mock.patch.dict("sys.modules", packetary=packetary):
            accessor = accessors.get_packetary_accessor(
                http_proxy="http://localhost",
                https_proxy="https://localhost",
                retries_num=1,
                threads_num=2,
                ignore_errors_num=3
            )
            accessor("deb")
            accessor("yum")
            packetary.Configuration.assert_called_once_with(
                http_proxy="http://localhost",
                https_proxy="https://localhost",
                retries_num=1,
                threads_num=2,
                ignore_errors_num=3
            )
            packetary.Context.assert_called_once_with(
                packetary.Configuration()
            )
            self.assertEqual(2, packetary.RepositoryApi.create.call_count)
            packetary.RepositoryApi.create.assert_any_call(
                packetary.Context(), "deb"
            )
            packetary.RepositoryApi.create.assert_any_call(
                packetary.Context(), "yum"
            )

    @mock.patch("fuel_mirror.common.accessors.os")
    def test_get_fuel_api_accessor(self, os):
        fuelclient = mock.MagicMock()
        patch = {
            "fuelclient": fuelclient,
            "fuelclient.objects": fuelclient.objects
        }
        with mock.patch.dict("sys.modules", patch):
            accessor = accessors.get_fuel_api_accessor(
                "localhost:8080", "guest", "123"
            )
            accessor.Environment.get_all()

            os.environ.__setitem__.asseert_any_call(
                "SERVER_ADDRESS", "localhost"
            )
            os.environ.__setitem__.asseert_any_call(
                "LISTEN_PORT", "8080"
            )
            os.environ.__setitem__.asseert_any_call(
                "KEYSTONE_USER", "guest"
            )
            os.environ.__setitem__.asseert_any_call(
                "KEYSTONE_PASS", "123"
            )
            fuelclient.objects.Environment.get_all.assert_called_once_with()
            os.environ.__setitem__.reset_mock()
            accessors.get_fuel_api_accessor()
            os.environ.__setitem__.assert_not_called()
