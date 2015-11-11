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
            {
                "server": "10.20.0.2",
                "user": None,
                "password": None,
            },
            utils.get_fuel_settings()
        )
