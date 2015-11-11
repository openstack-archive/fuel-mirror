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

import abc
import six


def get_url_builder(repotype):
    """Gets the instance of RepoUrlBuilder."""
    return {
        "deb": AptRepoUrlBuilder,
        "rpm": YumRepoUrlBuilder
    }[repotype]()


@six.add_metaclass(abc.ABCMeta)
class RepoUrlBuilder(object):
    @abc.abstractmethod
    def join(self, baseurl, uri):
        """Joins the base URL and repository`s URI.

        :param baseurl: the base repository`s URL
        :param uri: the repository`s URI
        :return: the full repository`s URL
        """

    @abc.abstractmethod
    def get_repo_config(self, name, url):
        """Gets the config for repo in FUEL compatible format.

        :param name: the main repository`s name
        :param url: the repository`s full-URL
        :return: the config for repository in FUEL format.
        """

    def format_url(self, baseurl, uri, **kwargs):
        """Get the url with replaced variable holders.

        :param baseurl: the repositories`s base url
        :param uri: the repository`s uri
        :param kwargs: the keyword arguments to string format.
        :return: the full repository`s url
        """
        return self.join(baseurl, uri).format(**kwargs)

    def get_urls(self, baseurl, uris, **kwargs):
        """Same as format_url, but for sequence.

        :param baseurl: the repositories`s base url
        :param uris: the sequence of repository`s uri
        :param kwargs: the keyword arguments to string format.
        :return: the list of full repository`s url
        """

        return [
            self.format_url(baseurl, x, **kwargs) for x in uris
        ]


class AptRepoUrlBuilder(RepoUrlBuilder):
    """URL builder for apt-repository(es)."""

    @staticmethod
    def get_name(name, suite):
        """Gets the full repository`s name.

        :param name: the main repository`s name
        :param suite: the suite name
        :return: the repository`s full-name
        """
        suite = suite.rsplit("-", 1)
        if len(suite) > 1:
            return "-".join((name, suite[-1]))
        return name

    def join(self, baseurl, uri):
        """Overrides base method."""
        baseurl = baseurl.rstrip()
        return " ".join((baseurl, uri))

    def get_repo_config(self, name, url):
        """Overrides base method."""
        baseurl, suite, section = url.split(" ", 2)
        name = self.get_name(name, suite)
        return {
            "name": name,
            "section": section,
            "suite": suite,
            "type": "deb",
            "uri": baseurl,
        }


class YumRepoUrlBuilder(RepoUrlBuilder):
    """URL builder for Yum repository(es)."""

    def join(self, baseurl, uri):
        """Overrides base method."""
        baseurl = baseurl.rstrip("/")
        return "/".join((baseurl, uri))

    def get_repo_config(self, name, url):
        """Overrides base method."""
        comp = url.rsplit("/", 1)[-1]
        if comp != "os":
            name = "-".join((name, comp))

        return {
            "name": name,
            "type": "rpm",
            "uri": url,
        }
