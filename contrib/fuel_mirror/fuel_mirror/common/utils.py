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
from string import Template

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
        return {}


def load_input_data(input_file, **kwargs):
    """Load yaml file and parse it to dict with replacement by kwargs.

    :param input_file: name of file to parse fuel mirror template
    :param kwargs: arguments to substitute template
    :return: processed from yaml file dict.
    """
    with open(input_file, "r") as fd:
        return yaml.load(Template(fd.read()).safe_substitute(**kwargs))
