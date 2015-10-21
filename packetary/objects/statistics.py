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
