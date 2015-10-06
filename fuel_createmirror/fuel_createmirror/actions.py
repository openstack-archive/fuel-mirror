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

from collections import defaultdict
import functools
import logging
import os
import Queue
import six
import threading
import traceback

from fuel_createmirror import repositories


logger = logging.getLogger(__package__)


class ThreadExecutor(object):
    """Executor based on thread-pool."""

    _stopper = object()

    def __init__(self, threads_num=4, qsize=100):
        errors = []
        queue = Queue.Queue(qsize)
        threads = []
        while threads_num > 0:
            t = threading.Thread(
                target=ThreadExecutor.worker, args=(queue, errors)
            )
            t.start()
            threads.append(t)
            threads_num -= 1

        self.threads = threads
        self.queue = queue
        self.errors = errors

    def execute(self, func, *args, **kwargs):
        """Puts new task to queue."""
        self.queue.put(functools.partial(func, *args, **kwargs))

    def wait(self):
        """Waits until all active tasks completed."""
        try:
            self.queue.join()
            if len(self.errors) > 0:
                raise RuntimeError("\n".join(self.errors))
        finally:
            self.errors[:] = []

    def stop(self):
        """Stops thread pool."""
        for _ in six.moves.range(len(self.threads)):
            self.queue.put(self._stopper)

        while self.threads:
            self.threads.pop().join()

    @staticmethod
    def worker(queue, errors):
        """Processes tasks."""
        while True:
            task = queue.get()
            if task is ThreadExecutor._stopper:
                break

            try:
                task()
            except Exception:
                errors.append(traceback.format_exc())
            finally:
                queue.task_done()


class Filters(object):
    """Aggregates all repository filters."""

    def __init__(self, filters):
        if "os" in filters:
            self.osnames = set(filters.os)
        else:
            self.osnames = None
        if "repo" in filters:
            self.repos = set(filters.repo)
        else:
            self.repos = None

        if filters.noupdates:
            self.sub_repos = set(("main",))
        else:
            self.sub_repos = set(("main", "updates", "security"))

    def match_os(self, osname):
        """Matches osname."""
        return self._match(osname, self.osnames)

    def match_repo(self, reponame):
        """Matches repository name."""
        return self._match(reponame, self.repos)

    def match_updates(self, name):
        """Matches updates repo name."""
        return self._match(name, self.sub_repos)

    @staticmethod
    def _match(value, filters):
        """Matches value according to filters."""
        return filters is None or value in filters


class Loader(object):
    """Repositories loaders."""

    def __init__(self, config, filters):
        self.releases = config.releases
        self.mirrors = config.mirrors
        self.arch = config.arch
        self.filters = Filters(filters)
        self.sources = self.get_sources(config)
        self.rdepends = self.reverse_depends(config.depends)

    def format_url(self, url):
        """Formats repository url."""
        return url.format(mirrors=self.mirrors, releases=self.releases)

    @staticmethod
    def reverse_depends(depends):
        """Builds the repository requirements tree."""
        requirements = defaultdict(list)
        for name, deps in depends.items():
            for d in deps:
                requirements[d].append(name)
        return requirements

    def get_sources(self, config):
        """Gets the filtered sources list."""
        result = defaultdict(list)
        for osname, repos in config.sources.items():
            if not self.filters.match_os(osname):
                continue
            for repo_name, sub_repos in repos.items():
                for name, url in sub_repos.items():
                    if not self.filters.match_updates(name):
                        continue
                    result[(osname, repo_name)].append(self.format_url(url))

        return result

    def load_repository(self, key, cache, counter=None):
        """Loads the repositories with depends."""
        if key in cache:
            return cache[key]

        repo = repositories.open_repository(
            key[0],
            self.sources[key],
            self.arch,
            counter
        )

        if key[1] in self.rdepends:
            unresolved = set()
            for dep in self.rdepends[key[1]]:
                repositories.get_external_depends(
                    self.load_repository((key[0], dep), cache, counter),
                    unresolved
                )

            repo = repositories.filter_by_depends(repo, unresolved)
            if len(unresolved) > 0:
                logger.warning(
                    "the following packages is not found: %s",
                    ",".join(x.package for x in unresolved)
                )

        cache[key] = repo
        return repo

    def load(self, counter=None):
        """Load repositories."""
        repos = []
        cache = dict()

        for k, urls in six.iteritems(self.sources):
            if not self.filters.match_repo(k[1]):
                continue
            repos.append((k[0], self.load_repository(k, cache, counter)))

        return repos


class CallCounter(object):
    """Count the number of calls and show as progress."""
    def __init__(self, progress, message):
        self.progress = progress
        self.message = message
        self.counter = 0

    def reset(self, msg):
        self.message = msg
        self.counter = 0

    def __call__(self):
        self.counter += 1
        self.progress(self.message, self.counter)


def copy_package(index, package, path, counter):
    """Copies packages."""
    package.copy_to(path)
    index.add(package)
    counter()


def load_repositories(config, filters, counter=None):
    """Load the repositories."""
    return Loader(config, filters).load(counter)


def create_mirror(options, progress_observer=None):
    """Creates mirror according to options."""
    counter = CallCounter(progress_observer, "packages loaded")

    repos = load_repositories(
        options.repositories,
        options.filters,
        counter
    )

    localpath = os.path.abspath(options.repositories.localpath)
    counter.reset("packages copied")

    executor = ThreadExecutor(options.tp.threads_count, options.tp.queue_size)
    try:
        for osname, repo in repos:
            repo.clone(
                os.path.join(localpath, osname),
                executor,
                counter
            )
    finally:
        executor.stop()
