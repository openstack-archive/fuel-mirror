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
