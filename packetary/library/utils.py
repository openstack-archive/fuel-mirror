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

from __future__ import with_statement

import errno
import os

import six

urlparse = six.moves.urllib.parse.urlparse


def append_token_to_string(tokens, token):
    """Adds new token to space separated list of tokens.

    :param tokens: the 'sep' separated list
    :param token: new item
    """
    values = tokens.split()
    if token not in values:
        values.append(token)
        values.sort()
        return ' '.join(values)
    return tokens


def composite_writer(*args):
    """Makes helper, that writes into several files simultaneously.

    :param args: the list of file objects
    :return: the callable object - writer
    """
    def write(text):
        """Writes simultaneously to all files with utf-8 encoding control.

        :param text: the text, that needs to write
        """
        if isinstance(text, six.text_type):
            text = text.encode("utf-8")
        for arg in args:
            arg.write(text)
    return write


def get_size_and_checksum_for_files(files, checksum_algo):
    """Gets the path, size and checksum for files.

    :param files: the sequence of files
    :param checksum_algo: the checksum calculator
    :return the sequence of tuples(filename, size, checksum)
    """

    for filename in files:
        with open(filename, "rb") as fd:
            size = os.fstat(fd.fileno()).st_size
            checksum = checksum_algo(fd)
        yield filename, size, checksum


def get_path_from_url(url, ensure_file=True):
    """Get the path from the URL.

    :param url: the URL
    :param ensure_file: If True, ensure that scheme is "file"
    :return: the path component from URL
    :raises ValueError
    """

    comps = urlparse(url, scheme="file")
    if ensure_file and comps.scheme != "file":
        raise ValueError(
            "The absolute path is expected, actual have: {0}.".format(url)
        )
    if os.sep != "/":
        return comps.path.replace("/", os.sep)
    return comps.path


def localize_repo_url(localurl, repo_url):
    """Gets local repository url.

    :param localurl: the base local URL
    :param repo_url: the origin URL of repository
    :return: localurl + get_path_from_url(repo_url)
    """
    return localurl.rstrip("/") + urlparse(repo_url).path


def ensure_dir_exist(path):
    """Creates directory if it does not exist.

    :param path: the full path to directory
    """

    try:
        os.makedirs(path)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise
