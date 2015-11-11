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

import functools
import os


def get_packetary_accessor(**kwargs):
    """Gets the configured repository manager.

    :param kwargs: The packetary configuration parameters.
    """

    import packetary

    return functools.partial(
        packetary.RepositoryApi.create,
        packetary.Context(packetary.Configuration(**kwargs))
    )


def get_fuel_api_accessor(address=None, user=None, password=None):
    """Gets the fuel client api accessor.

    :param address: The address of Fuel Master node.
    :param user: The username to access to the Fuel Master node.
    :param user: The password to access to the Fuel Master node.
    """
    if address:
        host_and_port = address.split(":")
        os.environ["SERVER_ADDRESS"] = host_and_port[0]
        if len(host_and_port) > 1:
            os.environ["LISTEN_PORT"] = host_and_port[1]

    if user is not None:
        os.environ["KEYSTONE_USER"] = user
    if password is not None:
        os.environ["KEYSTONE_PASS"] = password

    # import fuelclient.ClientAPI after configuring
    # environment variables
    from fuelclient import objects
    return objects
