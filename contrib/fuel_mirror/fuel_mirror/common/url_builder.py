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


def get_url_builder(repotype):
    """Gets the instance of RepoUrlBuilder.

    :param repotype: the type of repository: rpm|deb
    :return: the RepoBuilder implementation
    """
    return {
        "deb": AptRepoUrlBuilder,
        "rpm": YumRepoUrlBuilder
    }[repotype]


class RepoUrlBuilder(object):
    @classmethod
    def join_url(cls, baseurl, uri):
        """Joins the base URL and repository`s URI.

        :param baseurl: the base repository`s URL
        :param uri: the repository`s URI
        :return: the full repository`s URL
        """
        raise NotImplementedError

    @classmethod
    def get_repo_url(cls, baseurl, uri, **kwargs):
        """Get the url with replaced variable holders.

        :param baseurl: the repositories`s base url
        :param uri: the repository`s uri
        :param kwargs: the keyword arguments to string format.
        :return: the full repository`s url
        """
        return cls.join_url(baseurl, uri).format(**kwargs)

    @classmethod
    def get_repo_config(cls, name, baseurl, uri, **kwargs):
        """Gets the config for repo in FUEL compatible format.

        :param name: the main repository`s name
        :param baseurl: the repositories`s base url
        :param uri: the repository`s uri
        :param kwargs: the keyword arguments to string format
        :return: the config for repository in FUEL format
        """
        raise NotImplementedError

    @classmethod
    def get_urls(cls, baseurl, uris, **kwargs):
        """Same as format_url, but for sequence.

        :param baseurl: the repositories`s base url
        :param uris: the sequence of repository`s uri
        :param kwargs: the keyword arguments to string format.
        :return: the list of full repository`s url
        """

        return [
            cls.get_repo_url(baseurl, x, **kwargs) for x in uris
        ]


class AptRepoUrlBuilder(RepoUrlBuilder):
    """URL builder for apt-repository(es)."""

    @classmethod
    def get_name(cls, name, suite):
        """Gets the full repository`s name.

        :param name: the main repository`s name
        :param suite: the suite name
        :return: the repository`s full-name
        """
        suite = suite.rsplit("-", 1)
        if len(suite) > 1:
            return "-".join((name, suite[-1]))
        return name

    @classmethod
    def join_url(cls, baseurl, uri):
        baseurl = baseurl.rstrip()
        return " ".join((baseurl, uri))

    @classmethod
    def get_repo_config(cls, name, baseurl, uri, **kwargs):
        suite, section = uri.format(**kwargs).split(None, 1)
        name = cls.get_name(name, suite)
        return {
            "name": name,
            "section": section,
            "suite": suite,
            "type": "deb",
            "uri": baseurl.format(**kwargs),
        }


class YumRepoUrlBuilder(RepoUrlBuilder):
    """URL builder for Yum repository(es)."""

    @classmethod
    def join_url(cls, baseurl, uri):
        baseurl = baseurl.rstrip("/")
        return "/".join((baseurl, uri))

    @classmethod
    def get_repo_config(cls, name, baseurl, uri, **kwargs):
        baseurl = cls.get_repo_url(baseurl, uri, **kwargs)
        url = "/".join((baseurl, "$basearch"))
        if uri != "os":
            name = "-".join((name, uri))

        return {
            "name": name,
            "type": "rpm",
            "uri": url,
        }
