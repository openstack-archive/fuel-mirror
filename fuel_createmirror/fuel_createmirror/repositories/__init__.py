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


from . import deb
from .utility import *


_formats = {
    "ubuntu": deb
}


def open_repository(osname, urls, arch=None, counter=None):
    """Opens repositories by url."""

    if osname in _formats:
        return _formats[osname].open_repository(urls, arch, counter)

    raise NotImplementedError(
        "Cannot recognise the repository kind by osname: {0}"
        .format(osname)
    )
