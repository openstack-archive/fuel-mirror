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

import copy


class CopyStatistics(object):
    """The statistics of packages copying"""
    def __init__(self):
        # the number of copied packages
        self.copied = 0
        # the number of total packages
        self.total = 0

    def on_package_copied(self, bytes_copied):
        """Proceed next copied package."""
        if bytes_copied > 0:
            self.copied += 1
        self.total += 1

    def __iadd__(self, other):
        if not isinstance(other, CopyStatistics):
            raise TypeError

        self.copied += other.copied
        self.total += other.total
        return self

    def __add__(self, other):
        result = copy.copy(self)
        result += other
        return result
