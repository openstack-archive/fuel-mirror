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

from packetary.library import utils
from packetary.tests import base


class TestLibraryUtils(base.TestCase):
    def test_append_token_to_string(self):
        self.assertEqual(
            "v1 v2 v3",
            utils.append_token_to_string("v2 v3", "v1")
        )
        self.assertEqual(
            "v1",
            utils.append_token_to_string("", "v1")
        )
        self.assertEqual(
            "v1 v2 v3 v4",
            utils.append_token_to_string('v1\tv2   v3', "v4")
        )
        self.assertEqual(
            "v1 v2 v3",
            utils.append_token_to_string('v1 v2 v3', "v1")
        )

    def test_composite_writer(self):
        fds = [
            mock.MagicMock(),
            mock.MagicMock()
        ]
        writer = utils.composite_writer(*fds)
        writer(u"text1")
        writer(b"text2")
        for fd in fds:
            fd.write.assert_any_call(b"text1")
            fd.write.assert_any_call(b"text2")

    @mock.patch.multiple(
        "packetary.library.utils",
        os=mock.DEFAULT,
        open=mock.DEFAULT
    )
    def test_get_size_and_checksum_for_files(self, os, open):
        files = [
            "/file1.txt",
            "/file2.txt"
        ]
        os.fstat.side_effect = [
            mock.MagicMock(st_size=1),
            mock.MagicMock(st_size=2)
        ]
        r = list(utils.get_size_and_checksum_for_files(
            files, mock.MagicMock(side_effect=["1", "2"])
        ))
        self.assertEqual(
            [("/file1.txt", 1, "1"), ("/file2.txt", 2, "2")],
            r
        )

    def test_get_path_from_url(self):
        self.assertEqual(
            "/a/f.txt",
            utils.get_path_from_url("/a/f.txt")
        )

        self.assertEqual(
            "/a/f.txt",
            utils.get_path_from_url("file:///a/f.txt?size=1")
        )

        with self.assertRaises(ValueError):
            utils.get_path_from_url("http:///a/f.txt")

        self.assertEqual(
            "/f.txt",
            utils.get_path_from_url("http://host/f.txt", False)
        )

    @mock.patch("packetary.library.utils.os")
    def test_ensure_dir_exist(self, os):
        os.makedirs.side_effect = [
            True,
            OSError(utils.errno.EEXIST, ""),
            OSError(utils.errno.EACCES, ""),
            ValueError()
        ]
        utils.ensure_dir_exist("/nonexisted")
        os.makedirs.assert_called_with("/nonexisted")
        utils.ensure_dir_exist("/existed")
        os.makedirs.assert_called_with("/existed")
        with self.assertRaises(OSError):
            utils.ensure_dir_exist("/private")
        with self.assertRaises(ValueError):
            utils.ensure_dir_exist(1)
