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


class Repository(object):
    """Structure to describe repository object."""

    def __init__(self, name, url, architecture, origin):
        """Initialises.

        :param name: the repository`s name, should be unique
        :param url: the repository`s URL
        :param architecture: the repository`s architecture
        :param origin: the repository`s origin
        """
        self.name = name
        self.url = url
        self.architecture = architecture
        self.origin = origin

    def __copy__(self):
        """Creates shallow copy of package."""
        return Repository(**self.__dict__)
