# -*- coding: utf-8 -*-

#    Copyright 2015 Mirantis, Inc.
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License along
#    with this program; if not, write to the Free Software Foundation, Inc.,
#    51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.


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
    def get_repo_url(cls, repo_data):
        return repo_data["uri"]
