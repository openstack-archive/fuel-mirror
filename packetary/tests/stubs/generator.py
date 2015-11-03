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
