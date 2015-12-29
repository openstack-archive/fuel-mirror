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

from packetary import objects


def gen_repository(name="test", url="file:///test",
                   architecture="x86_64", origin="Test"):
    """Helper to create Repository object with default attributes."""
    return objects.Repository(name, url, architecture, origin)


def gen_relation(name="test", version=None, alternative=None):
    """Helper to create PackageRelation object with default attributes."""
    return objects.PackageRelation(
        name=name,
        version=objects.VersionRange(*(version or [])),
        alternative=alternative
    )


def gen_package(idx=1, **kwargs):
    """Helper to create Package object with default attributes."""
    repository = gen_repository()
    name = kwargs.setdefault("name", "package{0}".format(idx))
    kwargs.setdefault("repository", repository)
    kwargs.setdefault("version", 1)
    kwargs.setdefault("checksum", objects.FileChecksum("1", "2", "3"))
    kwargs.setdefault("filename", "{0}.pkg".format(name))
    kwargs.setdefault("filesize", 1)
    for relation in ("requires", "provides", "obsoletes"):
        if relation not in kwargs:
            kwargs[relation] = [gen_relation(
                "{0}{1}".format(relation, idx), ["le", idx + 1]
            )]

    return objects.Package(**kwargs)
