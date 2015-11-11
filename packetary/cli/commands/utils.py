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


import operator

import six


def read_lines_from_file(filename):
    """Reads lines from file.

    Note: the line starts with '#' will be skipped.

    :param filename: the path of target file
    :return: the list of lines from file
    """
    with open(filename, 'r') as f:
        return [
            x
            for x in six.moves.map(operator.methodcaller("strip"), f)
            if x and not x.startswith("#")
        ]


def get_object_attrs(obj, attrs):
    """Gets object attributes as list.

    :param obj: the target object
    :param attrs: the list of attributes
    :return: list of values from specified attributes.
    """
    return [getattr(obj, f) for f in attrs]


def get_display_value(value):
    """Get the displayable string for value.

    :param value: the target value
    :return: the displayable string for value
    """
    if value is None:
        return u"-"

    if isinstance(value, list):
        return u", ".join(six.text_type(x) for x in value)
    return six.text_type(value)


def make_display_attr_getter(attrs):
    """Gets formatter to convert attributes of object in displayable format.

    :param attrs: the list of attributes
    :return: the formatter (callable object)
    """
    return lambda x: [
        get_display_value(v) for v in get_object_attrs(x, attrs)
    ]
