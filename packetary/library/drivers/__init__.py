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

supported_drivers = ["deb", "yum"]

__all__ = supported_drivers


def _lazy_loader(name):
    """Loads driver on demand."""

    mod_name = ".".join((__name__, name + "_driver"))

    def loader(context, arch):
        try:
            module = __import__(mod_name, fromlist=["Driver"])
        except ImportError:
            raise AttributeError(name)
        return getattr(module, "Driver")(context, arch)
    return loader


for d in supported_drivers:
    locals()[d] = _lazy_loader(d)
