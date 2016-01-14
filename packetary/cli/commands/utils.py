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
