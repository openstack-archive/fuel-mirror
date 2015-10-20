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
