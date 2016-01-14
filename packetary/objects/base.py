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

import abc
import six


@six.add_metaclass(abc.ABCMeta)
class ComparableObject(object):
    """Superclass for objects, that should be comparable.

    Note: because python3 does not support __cmp__ slot, use
    cmp method to implement all of compare methods.
    """

    @abc.abstractmethod
    def cmp(self, other):
        """Compares with other object.

        :return: value is negative if if self < other, zero if self == other
                 strictly positive if x > y
        """

    def __lt__(self, other):
        return self.cmp(other) < 0

    def __le__(self, other):
        return self.cmp(other) <= 0

    def __gt__(self, other):
        return self.cmp(other) > 0

    def __ge__(self, other):
        return self.cmp(other) >= 0

    def __eq__(self, other):
        if other is self:
            return True
        return isinstance(other, type(self)) and self.cmp(other) == 0

    def __ne__(self, other):
        if other is self:
            return False
        return not isinstance(other, type(self)) or self.cmp(other) != 0

    def __cmp__(self, other):
        return self.cmp(other)
