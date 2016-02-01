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
import six

from fuel_mirror.common import utils
from fuel_mirror.tests import base


class DictAsObj(object):
    def __init__(self, d):
        self.__dict__.update(d)

    def __eq__(self, other):
        return self.__dict__ == other.__dict__


class TestUtils(base.TestCase):
    def test_lists_merge(self):
        main = [{"a": 1, "b": 2, "c": 0}, {"a": 2, "b": 3, "c": 1}]
        patch = [{"a": 2, "b": 4}, {"a": 3, "b": 5}]
        utils.lists_merge(
            main,
            patch,
            key="a"
        )
        self.assertItemsEqual(
            [{"a": 1, "b": 2, "c": 0},
             {"a": 2, "b": 4, "c": 1},
             {"a": 3, "b": 5}],
            main
        )

    def test_first(self):
        self.assertEqual(
            1,
            utils.first(0, 1, 0),
        )
        self.assertEqual(
            1,
            utils.first(None, [], '', 1),
        )
        self.assertIsNone(
            utils.first(None, [], 0, ''),
        )
        self.assertIsNone(
            utils.first(),
        )

    def test_is_subdict(self):
        self.assertFalse(utils.is_subdict({"c": 1}, {"a": 1, "b": 1}))
        self.assertFalse(utils.is_subdict({"a": 1, "b": 2}, {"a": 1, "b": 1}))
        self.assertFalse(
            utils.is_subdict({"a": 1, "b": 1, "c": 2}, {"a": 1, "b": 1})
        )
        self.assertFalse(
            utils.is_subdict({"a": 1, "b": None}, {"a": 1})
        )
        self.assertTrue(utils.is_subdict({}, {"a": 1}))
        self.assertTrue(utils.is_subdict({"a": 1}, {"a": 1, "b": 1}))
        self.assertTrue(utils.is_subdict({"a": 1, "b": 1}, {"a": 1, "b": 1}))

    @mock.patch("fuel_mirror.common.utils.open")
    def test_get_fuel_settings(self, m_open):
        m_open().__enter__.side_effect = [
            six.StringIO(
                'ADMIN_NETWORK:\n'
                '  ipaddress: "10.20.0.4"\n'
                'FUEL_ACCESS:\n'
                '  user: "test"\n'
                '  password: "test_pwd"\n',
            ),
            OSError
        ]

        self.assertEqual(
            {
                "server": "10.20.0.4",
                "user": "test",
                "password": "test_pwd",
            },
            utils.get_fuel_settings()
        )

        self.assertEqual(
            {},
            utils.get_fuel_settings()
        )

    @mock.patch("fuel_mirror.common.utils.yaml")
    @mock.patch("fuel_mirror.common.utils.open")
    def test_load_input_data(self, open_mock, yaml_mock):
        data = "$param1: $param2"
        open_mock().__enter__().read.return_value = data
        v = utils.load_input_data("data.yaml", param1="key", param2="value")
        open_mock.assert_called_with("data.yaml", "r")
        yaml_mock.load.assert_called_once_with("key: value")
        self.assertIs(yaml_mock.load(), v)
