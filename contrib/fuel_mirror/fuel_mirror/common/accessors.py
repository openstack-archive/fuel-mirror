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
    try:
        from fuelclient import objects
    except ImportError:
        raise RuntimeError(
            "fuelclient module seems not installed. "
            "This action requires it to be available."
        )
    return objects
