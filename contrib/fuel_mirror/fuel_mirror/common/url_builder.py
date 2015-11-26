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
    REPO_FOLDER = "mirror"

    @classmethod
    def get_repo_url(cls, repo_data):
        """Gets the url with replaced variable holders.

        :param repo_data: the repositories`s meta data
        :return: the full repository`s url
        """


class AptRepoUrlBuilder(RepoUrlBuilder):
    """URL builder for apt-repository(es)."""

    @classmethod
    def get_repo_url(cls, repo_data):
        return " ".join(
            repo_data[x] for x in ("uri", "suite", "section")
        )


class YumRepoUrlBuilder(RepoUrlBuilder):
    """URL builder for Yum repository(es)."""

    @classmethod
    def split_url(cls, url, maxsplit=2):
        """Splits url to baseurl, reponame adn architecture.

        :param url: the repository`s URL
        :param maxsplit: the number of expected components
        :return the components of url
        """
        # TODO(need generic url building algorithm)
        # there is used assumption that url has following format
        # $baseurl/$reponame/$repoarch
        return url.rstrip("/").rsplit("/", maxsplit)

    @classmethod
    def get_repo_url(cls, repo_data):
        return cls.split_url(repo_data["uri"], 1)[0]
