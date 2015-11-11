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
import subprocess
import yaml


if not hasattr(subprocess, 'check_output'):
    # checkoutput does not available in python 2.6

    def __check_output(*popenargs, **kwargs):
        if 'stdout' in kwargs:
            raise ValueError(
                'stdout argument not allowed, it will be overridden.'
            )
        p = subprocess.Popen(stdout=subprocess.PIPE, *popenargs, **kwargs)
        output, unused_err = p.communicate()
        retcode = p.poll()
        if retcode:
            cmd = kwargs.get("args")
            if cmd is None:
                cmd = popenargs[0]
            raise subprocess.CalledProcessError(retcode, cmd)
        return output

    subprocess.check_output = __check_output


def filter_from_choices(choices, iterable, key=None, attr=None):
    """Filters by next(data)[field] in choices.

    >>> list(filter_from_choices([1], [{"k": 1}, {"k":3}], key="k"))
    [{'k': 1}]

    :param choices: the sequence of possible values
    :param iterable: the sequence of dicts or objects
    :param key: the key to compare
    :param attr: the attribute name to compare
    """

    if not isinstance(choices, set):
        choices = set(choices)

    if key is not None and attr is not None:
        raise ValueError("'key' and 'attr' cannot be specified"
                         "simultaneously.")

    if key is not None:
        def function(x):
            return x[key] in choices
    else:
        def function(x):
            return getattr(x, attr) in choices

    return six.moves.filter(function, iterable)


def find_by_criteria(iterable, **criteria):
    """Finds first dict that has specified keywords.

    >>> find_by_criteria([{"a": 1, "c": 2}, {"a": 2, "c": 3}], a=1)
    {'a': 1, 'c': 2}

    :param iterable: the sequence of dicts
    :param criteria: the key=value pairs for compare
    :return: first element that meets criteria or None if not found.
    """
    for i in iterable:
        for k, v in six.iteritems(criteria):
            if i.get(k) != v:
                break
        else:
            return i


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

    _DEFAULT_SETTINGS = {
        "server": "10.20.0.2",
        "user": None,
        "password": None,
    }

    try:
        settings = yaml.load(subprocess.check_output(
            ["dockerctl", "shell", "astute", "cat", "/etc/fuel/astute.yaml"]
        ))
        return {
            "server": settings.get("ADMIN_NETWORK", {}).get("ipaddress"),
            "user": settings.get("FUEL_ACCESS", {}).get("user"),
            "password": settings.get("FUEL_ACCESS", {}).get("password")
        }
    except (subprocess.CalledProcessError, OSError):
        pass
    return _DEFAULT_SETTINGS
