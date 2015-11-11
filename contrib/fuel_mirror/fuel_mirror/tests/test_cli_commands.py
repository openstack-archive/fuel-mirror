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
import os.path
import subprocess

# The cmd2 does not work with python3.5
# because it tries to get access to the property mswindows,
# that was removed in 3.5
subprocess.mswindows = False

from fuel_mirror.commands import apply
from fuel_mirror.commands import create
from fuel_mirror.tests import base


CONFIG_PATH = os.path.join(os.path.dirname(__file__), "data", "test_config.yaml")

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "test_data.yaml")


@mock.patch.multiple(
    "fuel_mirror.app",
    accessors=mock.DEFAULT,
)
class TestCliCommands(base.TestCase):
    common_argv = [
        "--config", CONFIG_PATH,
        "--fuel-server=10.25.0.10",
        "--fuel-user=test",
        "--fuel-password=test1",
        "--input-file", DATA_PATH
    ]

    def start_cmd(self, cmd, argv):
        cmd.debug(argv + self.common_argv)

    def _setup_fuel_versions(self, fuel_mock):
        fuel_mock.FuelVersion.get_all_data.return_value = {
            "release": "1",
            "openstack_version": "2"
        }

    def _create_fuel_release(self, fuel_mock, osname):
        release = mock.MagicMock(data={
            "name": "test release",
            "operating_system": osname,
            "attributes_metadata": {
                "editable": {"repo_setup": {"repos": {"value": []}}}
            }
        })

        fuel_mock.Release.get_by_ids.return_value = [release]
        fuel_mock.Release.get_all.return_value = [release]
        return release

    def _create_fuel_env(self, fuel_mock):
        env = mock.MagicMock(data={
            "name": "test",
            "release_id": 1
        })
        env.get_settings_data.return_value = {
            "editable": {"repo_setup": {"repos": {"value": []}}}
        }
        fuel_mock.Environment.get_by_ids.return_value = [env]
        fuel_mock.Environment.get_all.return_value = [env]
        return env

    def test_create_mos_ubuntu(self, accessors):
        self._setup_fuel_versions(accessors.get_fuel_api_accessor())
        packetary = accessors.get_packetary_accessor()

        self.start_cmd(create, ["--group", "mos"])
        accessors.get_packetary_accessor.assert_called_with(
            threads_num=1,
            ignore_errors_num=2,
            retries_num=3,
            http_proxy="http://localhost",
            https_proxy="https://localhost",
        )
        packetary.assert_called_with("deb", "x86_64")
        api = packetary()
        api.clone_repositories.assert_called_once_with(
            ['http://localhost/mos mos1 main restricted'],
            '/var/www/',
            None, None
        )

    def test_create_partial_ubuntu(self, accessors):
        self._setup_fuel_versions(accessors.get_fuel_api_accessor())
        packetary = accessors.get_packetary_accessor()

        self.start_cmd(create, ["--group", "ubuntu"])
        accessors.get_packetary_accessor.assert_called_with(
            threads_num=1,
            ignore_errors_num=2,
            retries_num=3,
            http_proxy="http://localhost",
            https_proxy="https://localhost",
        )
        packetary.assert_called_with("deb", "x86_64")
        api = packetary()
        api.clone_repositories.assert_called_once_with(
            ['http://localhost/ubuntu trusty '
             'main multiverse restricted universe'],
            '/var/www/',
            ['http://localhost/mos mos1 main restricted'],
            ['package1']
        )

    def test_create_mos_centos(self, accessors):
        self._setup_fuel_versions(accessors.get_fuel_api_accessor())
        packetary = accessors.get_packetary_accessor()

        self.start_cmd(create, ["--group", "mos_centos"])
        accessors.get_packetary_accessor.assert_called_with(
            threads_num=1,
            ignore_errors_num=2,
            retries_num=3,
            http_proxy="http://localhost",
            https_proxy="https://localhost",
        )
        packetary.assert_called_with("rpm", "x86_64")
        api = packetary()
        api.clone_repositories.assert_called_once_with(
            ['http://localhost/mos1'],
            '/var/www/',
            None, None
        )

    def test_create_partial_centos(self, accessors):
        self._setup_fuel_versions(accessors.get_fuel_api_accessor())
        packetary = accessors.get_packetary_accessor()

        self.start_cmd(create, ["--group", "centos"])
        accessors.get_packetary_accessor.assert_called_with(
            threads_num=1,
            ignore_errors_num=2,
            retries_num=3,
            http_proxy="http://localhost",
            https_proxy="https://localhost",
        )
        packetary.assert_called_with("rpm", "x86_64")
        api = packetary()
        api.clone_repositories.assert_called_once_with(
            ['http://localhost/centos/os'],
            '/var/www/',
            ['http://localhost/mos1'],
            None
        )

    def test_apply_for_ubuntu_based_env(self, accessors):
        fuel = accessors.get_fuel_api_accessor()
        self._setup_fuel_versions(fuel)
        env = self._create_fuel_env(fuel)
        self._create_fuel_release(fuel, "Ubuntu")
        self.start_cmd(
            apply, ['--group', 'mos', 'ubuntu', '--env', '1']
        )
        accessors.get_fuel_api_accessor.assert_called_with(
            "10.25.0.10", "test", "test1"
        )
        fuel.FuelVersion.get_all_data.assert_called_once_with()
        env.set_settings_data.assert_called_with(
            {'editable': {'repo_setup': {'repos': {'value': [
                {
                    'priority': 1000,
                    'name': 'mos',
                    'suite': 'mos1',
                    'section': 'main restricted',
                    'type': 'deb',
                    'uri': 'http://10.25.0.10:8080/mos'
                },
                {
                    'priority': 500,
                    'name': 'ubuntu',
                    'suite': 'trusty',
                    'section': 'main multiverse restricted universe',
                    'type': 'deb',
                    'uri': 'http://10.25.0.10:8080/ubuntu'
                }
            ]}}}}
        )

    def test_apply_for_centos_based_env(self, accessors):
        fuel = accessors.get_fuel_api_accessor()
        self._setup_fuel_versions(fuel)
        env = self._create_fuel_env(fuel)
        self._create_fuel_release(fuel, "Centos")
        self.start_cmd(
            apply, ['--group', 'mos_centos', 'centos', '--env', '1']
        )
        accessors.get_fuel_api_accessor.assert_called_with(
            "10.25.0.10", "test", "test1"
        )
        fuel.FuelVersion.get_all_data.assert_called_once_with()
        env.set_settings_data.assert_called_with(
            {'editable': {'repo_setup': {'repos': {'value': [
                {
                    'priority': 5,
                    'name': 'centos',
                    'type': 'rpm',
                    'uri': 'http://10.25.0.10:8080/centos/os/x86_64'
                },
                {
                    'priority': 10,
                    'name': 'mos',
                    'type': 'rpm',
                    'uri': 'http://10.25.0.10:8080/mos1/x86_64'
                }]
            }}}}
        )

    def test_apply_for_ubuntu_release(self, accessors):
        fuel = accessors.get_fuel_api_accessor()
        self._setup_fuel_versions(fuel)
        env = self._create_fuel_env(fuel)
        release = self._create_fuel_release(fuel, "Ubuntu")
        self.start_cmd(
            apply, ['--group', 'mos', 'ubuntu', '--default']
        )
        accessors.get_fuel_api_accessor.assert_called_with(
            "10.25.0.10", "test", "test1"
        )
        fuel.FuelVersion.get_all_data.assert_called_once_with()
        self.assertEqual(1, env.set_settings_data.call_count)
        release.connection.put_request.assert_called_once_with(
            release.instance_api_path.format(),
            {
                'name': "test release",
                'operating_system': 'Ubuntu',
                'attributes_metadata': {
                    'editable': {'repo_setup': {'repos': {'value': [
                        {
                            'name': 'mos',
                            'priority': 1000,
                            'suite': 'mos1',
                            'section': 'main restricted',
                            'type': 'deb',
                            'uri': 'http://10.25.0.10:8080/mos'
                        },
                        {
                            'name': 'ubuntu',
                            'priority': 500,
                            'suite': 'trusty',
                            'section': 'main multiverse restricted universe',
                            'type': 'deb',
                            'uri': 'http://10.25.0.10:8080/ubuntu'
                        }
                    ]}}}
                }
            }
        )

    def test_apply_for_centos_release(self, accessors):
        fuel = accessors.get_fuel_api_accessor()
        self._setup_fuel_versions(fuel)
        env = self._create_fuel_env(fuel)
        release = self._create_fuel_release(fuel, "Centos")
        self.start_cmd(
            apply, ['--group', 'mos_centos', 'centos', '--default']
        )
        accessors.get_fuel_api_accessor.assert_called_with(
            "10.25.0.10", "test", "test1"
        )
        fuel.FuelVersion.get_all_data.assert_called_once_with()
        self.assertEqual(1, env.set_settings_data.call_count)
        release.connection.put_request.assert_called_once_with(
            release.instance_api_path.format(),
            {
                'name': "test release",
                'operating_system': 'Centos',
                'attributes_metadata': {
                    'editable': {'repo_setup': {'repos': {'value': [
                        {
                            'name': 'centos',
                            'priority': 5,
                            'type': 'rpm',
                            'uri': 'http://10.25.0.10:8080/centos/os/x86_64'
                        },
                        {
                            'name': 'mos',
                            'priority': 10,
                            'type': 'rpm',
                            'uri': 'http://10.25.0.10:8080/mos1/x86_64'
                        },
                    ]}}}
                }
            }
        )
