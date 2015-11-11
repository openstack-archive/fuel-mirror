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

from packetary.cli.commands import utils
from packetary.tests import base


class Dummy(object):
    pass


class TestCommandUtils(base.TestCase):
    @mock.patch("packetary.cli.commands.utils.open")
    def test_read_lines_from_file(self, open_mock):
        open_mock().__enter__.return_value = [
            "line1\n",
            " # comment\n",
            "line2 \n"
        ]

        self.assertEqual(
            ["line1", "line2"],
            utils.read_lines_from_file("test.txt")
        )

    def test_get_object_attrs(self):
        obj = Dummy()
        obj.attr_int = 0
        obj.attr_str = "text"
        obj.attr_none = None
        self.assertEqual(
            [0, "text", None],
            utils.get_object_attrs(obj, ["attr_int", "attr_str", "attr_none"])
        )

    def test_get_display_value(self):
        self.assertEqual(u"", utils.get_display_value(""))
        self.assertEqual(u"-", utils.get_display_value(None))
        self.assertEqual(u"0", utils.get_display_value(0))
        self.assertEqual(u"", utils.get_display_value([]))
        self.assertEqual(
            u"1, a, None",
            utils.get_display_value([1, "a", None])
        )
        self.assertEqual(u"1", utils.get_display_value(1))

    def test_make_display_attr_getter(self):
        obj = Dummy()
        obj.attr_int = 0
        obj.attr_str = "text"
        obj.attr_none = None
        formatter = utils.make_display_attr_getter(
            ["attr_int", "attr_str", "attr_none"]
        )
        self.assertEqual(
            [u"0", u"text", u"-"],
            formatter(obj)
        )
