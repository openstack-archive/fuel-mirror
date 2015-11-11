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
import subprocess

# The cmd2 does not work with python3.5
# because it tries to get access to the property mswindows,
# that was removed in 3.5
subprocess.mswindows = False

from fuel_mirror.commands import apply
from fuel_mirror.commands import create
from fuel_mirror.commands import update
from fuel_mirror.tests import base


@mock.patch.multiple(
    "fuel_mirror.app",
    accessors=mock.DEFAULT,
    yaml=mock.DEFAULT,
    open=mock.DEFAULT
)
class TestCliCommands(base.TestCase):
    common_argv = [
        "--config=/etc/fuel-mirror/config.yaml",
        "--fuel-server=10.25.0.10",
        "--fuel-user=test",
        "--fuel-password=test1"
    ]

    apply_argv_with_env = [
        "--env", "1"
    ]

    create_argv = [
        "--no-apply", "--default", "-U"
    ]

    update_argv = [
        "-C", "--full"
    ]

    def start_cmd(self, cmd, argv):
        cmd.debug(argv + self.common_argv)

    def test_create_cmd(self, accessors, yaml, open):
        yaml.load.return_value = _DEFAULT_CONFIG
        fuel = accessors.get_fuel_api_accessor()
        fuel.Release.get_all.return_value = [
            mock.MagicMock(data={
                "operating_system": "Ubuntu",
                "attributes_metadata": {
                    "editable": {"repo_setup": {"repos": {"value": []}}}
                }
            })
        ]
        packetary = accessors.get_packetary_accessor()

        self.start_cmd(create, self.create_argv)
        open.assert_called_once_with(
            "/etc/fuel-mirror/config.yaml", "r"
        )
        yaml.load.assert_called_once_with(open().__enter__())
        accessors.get_packetary_accessor.assert_called_with(
            threads_num=1,
            ignore_errors_num=2,
            retries_num=3,
            http_proxy="http://localhost",
            https_proxy="https://localhost",
        )
        packetary.assert_called_with("deb", "x86_64")
        self.assertEqual(2, packetary.call_count)
        api = packetary()
        api.clone_repositories.assert_any_call(
            ['http://localhost/mos/2 mos main'],
            '/var/www/nailgun/mirror/mos/ubuntu',
            None,
            None
        )
        api.clone_repositories.assert_any_call(
            ['http://localhost/ubuntu/2 trusty main'],
            '/var/www/nailgun/mirror/ubuntu',
            ['file:///var/www/nailgun/mirror/mos/ubuntu mos main'],
            ['ubuntu-minimal']
        )
        accessors.get_fuel_api_accessor.assert_called_with(
            "10.25.0.10", "test", "test1"
        )
        fuel.FuelVersion.get_all_data.assert_called_once_with()
        fuel.Release.get_all.assert_called_once_with()
        release = fuel.Release.get_all.return_value[0]
        release.connection.put_request.assert_called_once_with(
            release.instance_api_path.format(),
            {
                'operating_system': 'Ubuntu',
                'attributes_metadata': {
                    'editable': {
                        'repo_setup': {
                            'repos': {
                                'value': [
                                    {
                                        'suite': 'mos',
                                        'section': 'main',
                                        'type': 'deb',
                                        'name': 'mos',
                                        'uri': 'http://10.25.0.10:8080'
                                               '/mirror/mos/ubuntu'
                                    },
                                    {
                                        'suite': 'trusty',
                                        'section': 'main',
                                        'type': 'deb',
                                        'name': 'ubuntu',
                                        'uri': 'http://10.25.0.10:8080'
                                               '/mirror/ubuntu'
                                    }
                                ]
                            }
                        }
                    }
                }
            }
        )

    def test_update_cmd(self, accessors, yaml, open):
        yaml.load.return_value = _DEFAULT_CONFIG
        packetary = accessors.get_packetary_accessor()
        self.start_cmd(update, self.update_argv)
        open.assert_called_once_with(
            "/etc/fuel-mirror/config.yaml", "r"
        )
        yaml.load.assert_called_once_with(open().__enter__())
        accessors.get_packetary_accessor.assert_called_with(
            threads_num=1,
            ignore_errors_num=2,
            retries_num=3,
            http_proxy="http://localhost",
            https_proxy="https://localhost",
        )
        packetary.assert_called_with("yum", "x86_64")
        self.assertEqual(2, packetary.call_count)
        api = packetary()
        api.clone_repositories.assert_any_call(
            ['http://localhost/centos/1/os'],
            '/var/www/nailgun/mirror/centos',
            None,
            None
        )
        api.clone_repositories.assert_any_call(
            ['http://localhost/mos/1/os'],
            '/var/www/nailgun/mirror/mos/centos',
            None,
            None
        )

    def test_apply_cmd_for_env(self, accessors, yaml, open):
        yaml.load.return_value = _DEFAULT_CONFIG
        fuel = accessors.get_fuel_api_accessor()
        env = mock.MagicMock(data={"release_id": 1})
        env.get_settings_data.return_value = {
            "editable": {"repo_setup": {"repos": {"value": []}}}
        }
        fuel.Environment.get_by_ids.return_value = [env]
        fuel.Release.get_by_ids.return_value = [
            mock.MagicMock(data={
                "operating_system": "Ubuntu",
                "attributes_metadata": {
                    "editable": {"repo_setup": {"repos": {"value": []}}}
                }
            })
        ]

        self.start_cmd(apply, self.apply_argv_with_env)
        open.assert_called_once_with(
            "/etc/fuel-mirror/config.yaml", "r"
        )
        yaml.load.assert_called_once_with(open().__enter__())
        accessors.get_fuel_api_accessor.assert_called_with(
            "10.25.0.10", "test", "test1"
        )
        fuel.FuelVersion.get_all_data.assert_called_once_with()
        env.set_settings_data.assert_called_with(
            {
                "editable": {
                    'repo_setup': {
                        'repos': {
                            'value': [
                                {
                                    'suite': 'mos',
                                    'section': 'main',
                                    'type': 'deb',
                                    'name': 'mos',
                                    'uri': 'http://10.25.0.10:8080'
                                           '/mirror/mos/ubuntu'
                                },
                                {
                                    'suite': 'trusty',
                                    'section': 'main',
                                    'type': 'deb',
                                    'name': 'ubuntu',
                                    'uri': 'http://10.25.0.10:8080'
                                           '/mirror/ubuntu'
                                }
                            ]
                        }
                    }
                }
            }
        )

    def test_apply_cmd_for_all(self, accessors, yaml, open):
        yaml.load.return_value = _DEFAULT_CONFIG
        fuel = accessors.get_fuel_api_accessor()
        env = mock.MagicMock(data={"release_id": 1})
        env.get_settings_data.return_value = {
            "editable": {"repo_setup": {"repos": {"value": []}}}
        }
        fuel.Environment.get_all.return_value = [env]
        fuel.Release.get_by_ids.return_value = [
            mock.MagicMock(data={
                "operating_system": "Ubuntu",
                "attributes_metadata": {
                    "editable": {"repo_setup": {"repos": {"value": []}}}
                }
            })
        ]

        self.start_cmd(apply, [])
        open.assert_called_once_with(
            "/etc/fuel-mirror/config.yaml", "r"
        )
        yaml.load.assert_called_once_with(open().__enter__())
        accessors.get_fuel_api_accessor.assert_called_with(
            "10.25.0.10", "test", "test1"
        )
        fuel.FuelVersion.get_all_data.assert_called_once_with()
        env.set_settings_data.assert_called_with(
            {
                "editable": {
                    'repo_setup': {
                        'repos': {
                            'value': [
                                {
                                    'suite': 'mos',
                                    'section': 'main',
                                    'type': 'deb',
                                    'name': 'mos',
                                    'uri': 'http://10.25.0.10:8080'
                                           '/mirror/mos/ubuntu'
                                },
                                {
                                    'suite': 'trusty',
                                    'section': 'main',
                                    'type': 'deb',
                                    'name': 'ubuntu',
                                    'uri': 'http://10.25.0.10:8080'
                                           '/mirror/ubuntu'
                                }
                            ]
                        }
                    }
                }
            }
        )


_DEFAULT_CONFIG = {
    "common": {
        "threads_num": 1,
        "ignore_errors_num": 2,
        "retries_num": 3,
        "http_proxy": "http://localhost",
        "https_proxy": "https://localhost",
        "target_dir": "/var/www/nailgun"
    },
    "versions": {
        "centos_version": "1",
        "ubuntu_version": "2"
    },

    "sources": [
        {
            "name": "mos",
            "osname": "ubuntu",
            "type": "deb",
            "baseurl": "http://localhost/mos/{ubuntu_version}",
            "repositories": [
                "mos main",
            ],
        },
        {
            "name": "mos",
            "osname": "centos",
            "type": "yum",
            "baseurl": "http://localhost/mos/{centos_version}",
            "repositories": [
                "os"
            ],
        },
        {
            "name": "ubuntu",
            "osname": "ubuntu",
            "type": "deb",
            "master": "mos",
            "baseurl": "http://localhost/ubuntu/{ubuntu_version}",
            "repositories": [
                "trusty main"
            ],
            "bootstrap": [
                "ubuntu-minimal"
            ]
        },
        {
            "name": "centos",
            "osname": "centos",
            "type": "yum",
            "master": "mos",
            "baseurl": "http://localhost/centos/{centos_version}",
            "repositories": [
                "os"
            ]
        }
    ]
}
