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

from fuel_mirror.common import utils
from fuel_mirror.tests import base


class Dict2Obj(object):
    def __init__(self, d):
        self.__dict__.update(d)

    def __eq__(self, other):
        return self.__dict__ == other.__dict__


class TestUtils(base.TestCase):
    def test_filter_from_choices(self):
        self.assertItemsEqual(
            [{"a": 1}],
            utils.filter_from_choices([1], [{"a": 1}, {"a": 2}], key="a")
        )
        self.assertItemsEqual(
            [],
            utils.filter_from_choices([3], [{"a": 1}, {"a": 2}], key="a")
        )
        self.assertItemsEqual(
            [],
            utils.filter_from_choices([], [{"a": 1}, {"a": 2}], key="a")
        )
        self.assertItemsEqual(
            [Dict2Obj({"a": 1})],
            utils.filter_from_choices(
                [1],
                [Dict2Obj({"a": 1}), Dict2Obj({"a": 2})],
                attr="a"
            )
        )
        with self.assertRaises(ValueError):
            utils.filter_from_choices(
                [1],
                utils.filter_from_choices(
                    [], [{"a": 1}, {"a": 2}], key="a", attr="a"
                )
            )

    def test_find_by_criteria(self):
        self.assertIsNone(
            utils.find_by_criteria([{"a": 1, "b": 1}], c=1)
        )

        self.assertIsNone(
            utils.find_by_criteria([{"a": 1, "b": 1}], a=1, b=2)
        )
        self.assertEqual(
            {"a": 1, "b": 1},
            utils.find_by_criteria([{"a": 1, "b": 1}, {"a": 1}], a=1)
        )

        self.assertEqual(
            {"a": 1, "b": 1},
            utils.find_by_criteria([{"a": 1}, {"a": 1, "b": 1}], a=1, b=1)
        )

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
            utils.first(None, [], 1),
        )
        self.assertIsNone(
            utils.first(None, [], 0),
        )
        self.assertIsNone(
            utils.first(),
        )

    @mock.patch("fuel_mirror.common.utils.subprocess")
    def test_get_fuel_settings(self, subprocess):
        subprocess.CalledProcessError = RuntimeError
        subprocess.check_output.side_effect = [
            '"ADMIN_NETWORK":\n'
            '  "ipaddress": "10.20.0.4"\n'
            '"FUEL_ACCESS":\n'
            '  "user": "test"\n'
            '  "password": "test_pwd"\n',
            RuntimeError()
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
