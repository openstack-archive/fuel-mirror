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

from fuel_createmirror.services import rsync


@mock.patch("fuel_createmirror.services.rsync.cmd")
def test_rsync_files(cmd):
    cmd.get_output.return_value = """\
drw-r--r--     1957388 2014/12/03 17:12:26 .
-rw-r--r--      115626 2014/12/03 17:12:22 test2.deb
-rw-r--r--       84588 2014/04/10 13:41:45 test3.tgz
-rw-r--r--     1957388 2014/12/03 17:12:26 test1.deb
"""
    files = rsync.files("host::path")
    cmd.get_output.assert_called_once_with([
        rsync.rsync, '--no-motd', '--list-only', '--relative', '--recursive',
        '--no-implied-dirs', '--perms', '--copy-links', '--times',
        '--hard-links', '--sparse', '--safe-links', "host::path"
    ])
    assert ["test1.deb", "test2.deb", "test3.tgz"] == \
        sorted(files)

    debs = rsync.files("host::path", "*.deb")
    assert ["test1.deb", "test2.deb"] == sorted(debs)


@mock.patch("fuel_createmirror.services.rsync.cmd")
def test_rsync_copy(cmd):

    rsync.copy("host::path", "/tmp/1")
    cmd.check_call.assert_called_once_with([
        rsync.rsync, '--no-motd', '--perms', '--copy-links', '--times',
        '--hard-links', '--sparse', '--safe-links', 'host::path', '/tmp/1'
    ])


@mock.patch("fuel_createmirror.services.rsync.cmd")
def test_rsync_exists(cmd):
    cmd.call.return_value = 0
    assert rsync.exists("host::path")
    cmd.call.assert_called_once_with([
        rsync.rsync, '--no-motd', '--list-only', 'host::path'
    ], dry_run=False)

    cmd.call.return_value = 1
    assert not rsync.exists("host::path2")
