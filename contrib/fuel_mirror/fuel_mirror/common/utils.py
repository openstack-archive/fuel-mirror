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

import six
import yaml


def lists_merge(main, patch, key):
    """Merges the list of dicts with same keys.

    >>> lists_merge([{"a": 1, "c": 2}], [{"a": 1, "c": 3}], key="a")
    [{'a': 1, 'c': 3}]

    :param main: the main list
    :type main: list
    :param patch: the list of additional elements
    :type patch: list
    :param key: the key for compare
    """
    main_idx = dict(
        (x[key], i) for i, x in enumerate(main)
    )

    patch_idx = dict(
        (x[key], i) for i, x in enumerate(patch)
    )

    for k in sorted(patch_idx):
        if k in main_idx:
            main[main_idx[k]].update(patch[patch_idx[k]])
        else:
            main.append(patch[patch_idx[k]])
    return main


def is_subdict(dict1, dict2):
    """Checks that dict1 is subdict of dict2.

    >>> is_subdict({"a": 1}, {'a': 1, 'b': 1})
    True

    :param dict1: the candidate
    :param dict2: the super dict
    :return: True if all keys from dict1 are present
             and has same value in dict2 otherwise False
    """
    for k, v in six.iteritems(dict1):
        if k not in dict2 or dict2[k] != v:
            return False
    return True


def first(*args):
    """Get first not empty value.

    >>> first(0, 1) == next(iter(filter(None, [0, 1])))
    True

    :param args: the list of arguments
    :return first value that bool(v) is True, None if not found.
    """
    for arg in args:
        if arg:
            return arg


def get_fuel_settings():
    """Gets the fuel settings from astute container, if it is available."""

    try:
        with open("/etc/fuel/astute.yaml", "r") as fd:
            settings = yaml.load(fd)
        return {
            "server": settings.get("ADMIN_NETWORK", {}).get("ipaddress"),
            "user": settings.get("FUEL_ACCESS", {}).get("user"),
            "password": settings.get("FUEL_ACCESS", {}).get("password")
        }
    except (OSError, IOError):
        pass
    return {}
