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

    @mock.patch("fuel_mirror.common.accessors.os")
    def test_get_fuel_api_accessor_with_default_parameters(self, os):
        fuelclient = mock.MagicMock()
        patch = {
            "fuelclient": fuelclient,
            "fuelclient.objects": fuelclient.objects
        }
        with mock.patch.dict("sys.modules", patch):
            accessors.get_fuel_api_accessor()
            os.environ.__setitem__.assert_not_called()
