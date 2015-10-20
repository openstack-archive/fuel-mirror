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

from packetary.library import utils
from packetary.tests import base


class TestLibraryUtils(base.TestCase):
    def test_append_token_to_string(self):
        self.assertEqual(
            "v1 v2 v3",
            utils.append_token_to_string("v2 v3", "v1", sep=' ')
        )
        self.assertEqual(
            "v1",
            utils.append_token_to_string("", "v1")
        )
        self.assertEqual(
            "v1,v2,v3",
            utils.append_token_to_string("v1,v2,v3", "v1", sep=',')
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
