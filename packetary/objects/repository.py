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


class Repository(object):
    """Structure to describe repository object."""

    def __init__(self, name, url, architecture, origin):
        """Initialises.

        :param name: the repository`s name, may be tuple of strings
        :param url: the repository`s URL
        :param architecture: the repository`s architecture
        :param origin: the repository`s origin
        """
        self.name = name
        self.url = url
        self.architecture = architecture
        self.origin = origin

    def __str__(self):
        if isinstance(self.name, tuple):
            return ".".join(self.name)
        return self.name or self.url

    def __unicode__(self):
        if isinstance(self.name, tuple):
            return u".".join(self.name)
        return self.name or self.url

    def __copy__(self):
        """Creates shallow copy of package."""
        return Repository(**self.__dict__)
