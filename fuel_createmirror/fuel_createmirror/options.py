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


import multiprocessing
import six
import yaml


class Options(object):
    def __setattr__(self, key, value):
        self.__setitem__(key, value)

    def __setitem__(self, key, value):
        head, tail = self._split_key(key)
        if tail:
            self.__dict__.setdefault(head, Options()).__setitem__(tail, value)
        else:
            self.__dict__[head] = value

    def __getitem__(self, key):
        head, tail = self._split_key(key)
        if tail:
            return self.__dict__[head][tail]
        else:
            return self.__dict__[head]

    def __getattr__(self, item):
        try:
            return self.__getitem__(item)
        except KeyError as e:
            raise AttributeError(str(e))

    def __nonzero__(self):
        return bool(self.__dict__)

    def __bool__(self):
        return bool(self.__dict__)

    def __contains__(self, key):
        head, tail = self._split_key(key)
        if not self.__dict__.__contains__(head):
            return False

        if tail:
            return self.__dict__[head].__contains__(tail)
        return True

    def append(self, key, value):
        head, tail = self._split_key(key)
        if tail:
            self.__dict__.setdefault(head, Options()).append(tail, value)
        else:
            self.__dict__.setdefault(head, list()).append(value)

    def get(self, key, default=None):
        try:
            return self.__getitem__(key)
        except KeyError:
            return default

    def sef_default(self, key, value):
        head, tail = self._split_key(key)
        if tail:
            self.__dict__.setdefault(head, Options()).sef_default(tail, value)
        else:
            self.__dict__.setdefault(head, value)

    def items(self):
        return six.iteritems(self.__dict__)

    def load_from_dict(self, d):
        for k, v in six.iteritems(d):
            if isinstance(v, dict):
                self.__dict__.setdefault(k, Options()).load_from_dict(v)
            else:
                self.sef_default(k, v)

    def load_from_file(self, filename):
        with open(filename, 'r') as stream:
            d = yaml.load(stream)

        if not isinstance(d, dict):
            raise ValueError("malformed config: <type 'dict'> expected.")
        self.load_from_dict(d)

    @staticmethod
    def _split_key(key):
        head, _, tail = key.partition('.')
        return head, tail

    def clear(self):
        self.__dict__.clear()

    def set_defaults(self):
        """Set default settings."""
        self.sef_default('globals.dry_run', False)
        self.sef_default('globals.no_progress', False)
        self.sef_default('globals.retries', 1)
        self.sef_default('globals.retry_delay', 1)
        self.sef_default('globals.proxy.server', "")
        self.sef_default('globals.proxy.username', "")
        self.sef_default('globals.proxy.password', "")
        self.sef_default('logging.filename', "")
        self.sef_default('logging.level', "info")
        self.sef_default('tp.threads_count', multiprocessing.cpu_count())
        self.sef_default('tp.queue_size', 100)
        self.sef_default('filters.noupdates', False)
        self.sef_default('repositories.localpath', "/var/www/")
        self.sef_default('repositories.arch', "x86_64")
        self.sef_default('repositories.depends', Options())
        self.sef_default('repositories.releases', Options())
        self.sef_default('repositories.mirrors', Options())
        self.sef_default('repositories.sources', Options())


options = Options()
options.set_defaults()
