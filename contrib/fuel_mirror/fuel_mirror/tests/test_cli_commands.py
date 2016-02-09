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
import os.path
import subprocess

from jsonschema import ValidationError

# The cmd2 does not work with python3.5
# because it tries to get access to the property mswindows,
# that was removed in 3.5
subprocess.mswindows = False

from fuel_mirror.commands import apply
from fuel_mirror.commands import create
from fuel_mirror.common.utils import load_input_data
from fuel_mirror.tests import base


CONFIG_PATH = os.path.join(
    os.path.dirname(__file__), "data", "test_config.yaml"
)

UBUNTU_PATH = os.path.join(
    os.path.dirname(__file__), "data", "test_ubuntu.yaml"
)

CENTOS_PATH = os.path.join(
    os.path.dirname(__file__), "data", "test_centos.yaml"
)

INVALID_DATA_PATH = os.path.join(
    os.path.dirname(__file__), "data", "test_invalid_ubuntu.yaml"
)


# TODO(akostrikov) lists_merge we are using is not stable so we have to use
# different local repos in cases with merge and without it.
# We pass sorted by priority list, but in lists_merge we sort it by key.
# As we are aiming to use existing repos as primary source - it is not issue.
def local_repos(mirror_host='10.25.0.10:8080', name_postfix='', reverse=True):
    mirror_lists = load_input_data(UBUNTU_PATH, mos_version=1)
    sorted_repos = reduce(lambda x, y: x + y, mirror_lists['groups'].values())
    sorted_repos.sort(key=lambda x: x['priority'], reverse=reverse)
    for repo in sorted_repos:
        repo.pop('main', None)
        repo['name'] = repo['name'] + name_postfix
        repo['uri'] = repo['uri'].replace('localhost', mirror_host)
    return sorted_repos


def mirror_repos():
    return local_repos(mirror_host='mirror.com:8080', name_postfix='-mirror')


@mock.patch.multiple(
    "fuel_mirror.app",
    accessors=mock.DEFAULT
)
class TestCliCommands(base.TestCase):
    common_argv = [
        "--config", CONFIG_PATH,
        "--fuel-server=10.25.0.10",
        "--fuel-user=test",
        "--fuel-password=test1"
    ]

    def start_cmd(self, cmd, argv, data_file):
        cmd.debug(
            argv + self.common_argv + ["--input-file", data_file]
        )

    def _setup_fuel_versions(self, fuel_mock):
        fuel_mock.FuelVersion.get_all_data.return_value = {
            "release": "1",
            "openstack_version": "2"
        }

    def _create_fuel_release(self, fuel_mock, osname, repos=None):
        if repos is None:
            repos = []
        release = mock.MagicMock(data={
            "name": "test release",
            "operating_system": osname,
            "attributes_metadata": {
                "editable": {"repo_setup": {"repos": {"value": repos}}}
            }
        })

        fuel_mock.Release.get_by_ids.return_value = [release]
        fuel_mock.Release.get_all.return_value = [release]
        return release

    def _create_fuel_env(self, fuel_mock, repos=None):
        if repos is None:
            repos = []
        env = mock.MagicMock(data={
            "name": "test",
            "release_id": 1
        })
        env.get_settings_data.return_value = {
            "editable": {"repo_setup": {"repos": {"value": repos}}}
        }
        fuel_mock.Environment.get_by_ids.return_value = [env]
        fuel_mock.Environment.get_all.return_value = [env]
        return env

    def test_create_mos_ubuntu(self, accessors):
        self._setup_fuel_versions(accessors.get_fuel_api_accessor())
        packetary = accessors.get_packetary_accessor()

        self.start_cmd(create, ["--group", "mos"], UBUNTU_PATH)
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

        self.start_cmd(create, ["--group", "ubuntu"], UBUNTU_PATH)
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
            ['package_deb']
        )

    def test_create_mos_centos(self, accessors):
        self._setup_fuel_versions(accessors.get_fuel_api_accessor())
        packetary = accessors.get_packetary_accessor()

        self.start_cmd(create, ["--group", "mos"], CENTOS_PATH)
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
            ['http://localhost/mos1/x86_64'],
            '/var/www/',
            None, None
        )

    def test_create_partial_centos(self, accessors):
        self._setup_fuel_versions(accessors.get_fuel_api_accessor())
        packetary = accessors.get_packetary_accessor()

        self.start_cmd(create, ["--group", "centos"], CENTOS_PATH)
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
            ['http://localhost/centos/os/x86_64'],
            '/var/www/',
            ['http://localhost/mos1/x86_64'],
            ["package_rpm"]
        )

    def test_apply_for_ubuntu_based_env(self, accessors):
        fuel = accessors.get_fuel_api_accessor()
        self._setup_fuel_versions(fuel)
        env = self._create_fuel_env(fuel)
        self._create_fuel_release(fuel, "Ubuntu")
        self.start_cmd(
            apply, ['--group', 'mos', 'ubuntu', '--env', '1'],
            UBUNTU_PATH
        )
        accessors.get_fuel_api_accessor.assert_called_with(
            "10.25.0.10", "test", "test1"
        )
        fuel.FuelVersion.get_all_data.assert_called_once_with()
        env.set_settings_data.assert_called_with(
            {
                'editable': {
                    'repo_setup': {
                        'repos': {'value': local_repos()}
                    }
                }
            }
        )

    def test_with_existing_mirrors(self, accessors):
        fuel = accessors.get_fuel_api_accessor()
        self._setup_fuel_versions(fuel)
        env = self._create_fuel_env(fuel, repos=mirror_repos())
        self._create_fuel_release(fuel, "Ubuntu", repos=mirror_repos())
        self.start_cmd(
            apply, ['--group', 'mos', 'ubuntu', '--env', '1'],
            UBUNTU_PATH
        )
        accessors.get_fuel_api_accessor.assert_called_with(
            "10.25.0.10", "test", "test1"
        )
        fuel.FuelVersion.get_all_data.assert_called_once_with()
        env.set_settings_data.assert_called_with(
            {
                'editable': {
                    'repo_setup': {
                        'repos': {'value': mirror_repos() + local_repos()}
                    }
                }
            }
        )

    def test_replace_existing_mirrors_with_local(self, accessors):
        fuel = accessors.get_fuel_api_accessor()
        self._setup_fuel_versions(fuel)
        env = self._create_fuel_env(fuel, repos=mirror_repos())
        self._create_fuel_release(fuel, "Ubuntu", repos=mirror_repos())
        self.start_cmd(
            apply, ['--group', 'mos', 'ubuntu', '--env', '1', '--replace'],
            UBUNTU_PATH
        )
        accessors.get_fuel_api_accessor.assert_called_with(
            "10.25.0.10", "test", "test1"
        )
        fuel.FuelVersion.get_all_data.assert_called_once_with()
        env.set_settings_data.assert_called_with(
            {
                'editable': {
                    'repo_setup': {
                        'repos': {'value': local_repos(reverse=False)}
                    }
                }
            }
        )

    def test_apply_for_centos_based_env(self, accessors):
        fuel = accessors.get_fuel_api_accessor()
        self._setup_fuel_versions(fuel)
        env = self._create_fuel_env(fuel)
        self._create_fuel_release(fuel, "CentOS")
        self.start_cmd(
            apply, ['--group', 'mos', 'centos', '--env', '1'],
            CENTOS_PATH
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
            apply, ['--group', 'mos', 'ubuntu', '--default'],
            UBUNTU_PATH
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

    def test_update_release_and_cluster_repositories(self, accessors):
        fuel = accessors.get_fuel_api_accessor()
        self._setup_fuel_versions(fuel)
        env = self._create_fuel_env(fuel, repos=mirror_repos())
        release = \
            self._create_fuel_release(fuel, "Ubuntu", repos=mirror_repos())
        self.start_cmd(
            apply, ['--group', 'mos', 'ubuntu', '--default'],
            UBUNTU_PATH
        )
        accessors.get_fuel_api_accessor.assert_called_with(
            "10.25.0.10", "test", "test1"
        )
        fuel.FuelVersion.get_all_data.assert_called_once_with()
        expected_repos = mirror_repos() + local_repos()
        env.set_settings_data.assert_called_with(
            {
                'editable': {
                    'repo_setup': {
                        'repos': {'value': expected_repos}
                    }
                }
            }
        )
        release.connection.put_request.assert_called_once_with(
            release.instance_api_path.format(),
            {
                'name': "test release",
                'operating_system': 'Ubuntu',
                'attributes_metadata': {
                    'editable': {'repo_setup': {'repos': {
                        'value': expected_repos
                    }}}
                }
            }
        )

    def test_replace_release_and_cluster_repositories(self, accessors):
        fuel = accessors.get_fuel_api_accessor()
        self._setup_fuel_versions(fuel)
        env = self._create_fuel_env(fuel, repos=mirror_repos())
        release = \
            self._create_fuel_release(fuel, "Ubuntu", repos=mirror_repos())
        self.start_cmd(
            apply, ['--group', 'mos', 'ubuntu', '--default', '--replace'],
            UBUNTU_PATH
        )
        accessors.get_fuel_api_accessor.assert_called_with(
            "10.25.0.10", "test", "test1"
        )
        fuel.FuelVersion.get_all_data.assert_called_once_with()
        expected_repos = local_repos(reverse=False)
        env.set_settings_data.assert_called_with(
            {
                'editable': {
                    'repo_setup': {
                        'repos': {'value': expected_repos}
                    }
                }
            }
        )
        release.connection.put_request.assert_called_once_with(
            release.instance_api_path.format(),
            {
                'name': "test release",
                'operating_system': 'Ubuntu',
                'attributes_metadata': {
                    'editable': {'repo_setup': {'repos': {
                        'value': expected_repos
                    }}}
                }
            }
        )

    def test_apply_for_centos_release(self, accessors):
        fuel = accessors.get_fuel_api_accessor()
        self._setup_fuel_versions(fuel)
        env = self._create_fuel_env(fuel)
        release = self._create_fuel_release(fuel, "CentOS")
        self.start_cmd(
            apply, ['--group', 'mos', 'centos', '--default'],
            CENTOS_PATH
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
                'operating_system': 'CentOS',
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

    @mock.patch("fuel_mirror.app.utils.get_fuel_settings")
    def test_apply_fail_if_no_fuel_address(self, m_get_settings, accessors):
        m_get_settings.return_value = {}
        with self.assertRaisesRegexp(
                ValueError, "Please specify the fuel-server option"):
            apply.debug(
                ["--config", CONFIG_PATH, "-G", "mos", "-I", UBUNTU_PATH]
            )
        self.assertFalse(accessors.get_fuel_api_accessor.called)

    @mock.patch("fuel_mirror.app.utils.get_fuel_settings")
    def test_create_without_fuel_address(self, m_get_settings, accessors):
        m_get_settings.return_value = {}
        packetary = accessors.get_packetary_accessor()
        create.debug(
            ["--config", CONFIG_PATH, "-G", "mos", "-I", UBUNTU_PATH]
        )
        self.assertFalse(accessors.get_fuel_api_accessor.called)
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
            ['http://localhost/mos mos main restricted'],
            '/var/www/',
            None,
            None
        )

    @mock.patch("fuel_mirror.app.utils.get_fuel_settings")
    def test_create_with_invalid_data(self, m_get_settings, accessors):
        self.assertRaises(
            ValidationError, create.debug, ["--config", CONFIG_PATH, "-G",
                                            "mos", "-I", INVALID_DATA_PATH]
        )
