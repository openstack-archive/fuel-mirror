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


__all__ = [
    "filter_by_depends",
    "find_package",
    "get_external_depends",
]


def queue_iterator(queue):
    """Iterates over mutable queue, with uniqueness guarantee."""
    seen = set()
    while queue:
        i = queue.pop()
        if i not in seen:
            yield i
            seen.add(i)


def find_package(repo, name, search):
    """Filters versions according to condition."""
    if name in repo:
        versions = repo[name]
        p = search(versions)
        if p is not None:
            return p


def get_external_depends(repo, unresolved):
    """Gets all unresolved depends for packages."""
    for package in repo:
        for d in package.get_depends():
            if d in unresolved:
                break

            alt = d
            while alt is not None:
                if find_package(repo, alt.name, alt.condition):
                    break
                alt = alt.alt

            if alt is None:
                unresolved.add(d)


def filter_by_depends(repo, depends):
    """Gets minimal required slice of repository."""
    unresolved = set()
    new_repo = type(repo)()

    for dep in queue_iterator(depends):
        package = find_package(repo, dep.name, dep.condition)
        if package is not None:
            new_repo.add(package)
            depends.update(package.get_depends())
        else:
            unresolved.add(dep)

    depends.update(unresolved)
    return new_repo
