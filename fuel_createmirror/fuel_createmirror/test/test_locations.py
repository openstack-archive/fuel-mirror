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


import mock
import pytest

from six.moves.urllib_parse import urlparse

from fuel_createmirror.locations import http


@mock.patch('fuel_createmirror.locations.http.rsync')
def test_open_http_location(rsync):
    rsync.exists.return_value = True
    with http.probe(urlparse('http://mirror.ubuntu.com/trusty')) as loc:
        rsync.exists.called_once_with("mirror.ubuntu.com::trusty/")
        assert isinstance(loc, http.HTTPLocation)
        assert rsync is loc.service
        assert "mirror.ubuntu.com::trusty/" == loc.baseurl

    rsync.exists.return_value = False
    with pytest.raises(NotImplementedError):
        http.probe(urlparse('http://mirror.ubuntu.com/trusty'))


def test_http_location():
    service_stub = mock.Mock()
    with http.HTTPLocation(service_stub, "http://ubuntu.com/p1/") as location:
        location.ls("/p2/", "*.deb")
        service_stub.files.assert_called_with(
            "http://ubuntu.com/p1/p2/", "*.deb"
        )
        location.exists("p3")
        service_stub.exists.assert_called_with(
            "http://ubuntu.com/p1/p3"
        )
        location.fetch("p4", "tmp/1")
        service_stub.copy.assert_called_with(
            "http://ubuntu.com/p1/p4", "tmp/1"
        )
        with location.open("p5", "wb") as s:
            service_stub.copy.assert_called_with(
                "http://ubuntu.com/p1/p5", s.name
            )
