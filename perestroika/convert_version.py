#!/usr/bin/env python

##
# Convert pip style alpha/beta/rc/dev versions to the ones suitable for a
# package manager.
# Does not modify the conventional 3-digit version numbers.
# Examples:
#    1.2.3.0a4 -> 1.2.3~a4
#    1.2.3rc1 -> 1.2.3~rc1
#    1.2.3 -> 1.2.3

import argparse
from pkg_resources import parse_version
import re


def strip_leading_zeros(s):
    return re.sub(r"^0+([0-9]+)", r"\1", s)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-t', '--tag', dest='tag', action='store', type=str,
        help='PyPi version tag', required=True, default='0'
    )

    params, other_params = parser.parse_known_args()

    pip_ver = params.tag

    print(convert_version(pip_ver))


def convert_version(pip_ver):
    # drop dashed part from version string because
    # it represents a patch level of given version
    pip_ver = pip_ver.split('-')[0]

    # add leading 1 if tag is starting from letter
    if re.match(r"^[a-zA-Z]", pip_ver):
        pip_ver = '1' + pip_ver

    # parse_version converts string '12.0.0.0rc1'
    # to touple ('00000012', '*c', '00000001', '*final')
    # details:
    #     http://galaxy-dist.readthedocs.org/en/latest/lib/pkg_resources.html
    pip_ver_parts = parse_version(pip_ver)

    _ver = True
    pkg_ver_part = []
    pkg_alpha = ""
    pkg_rev_part = []
    for part in pip_ver_parts:
        if part == "*final":
            continue
        if re.match(r"[*a-z]", part):
            _ver = False
            pkg_alpha = re.sub(r"^\*", "~", part)
            continue
        if _ver:
            pkg_ver_part.append(strip_leading_zeros(part))
        else:
            pkg_rev_part.append(strip_leading_zeros(part))

    # replace 'c' and '@' with 'rc' and 'dev' at pkg_alpha
    pkg_alpha = pkg_alpha.replace('c', 'rc')
    pkg_alpha = pkg_alpha.replace('@', 'dev')

    # expand version to three items
    while (len(pkg_ver_part) < 3):
        pkg_ver_part.append('0')

    return '.'.join(pkg_ver_part) + pkg_alpha + '.'.join(pkg_rev_part)


if __name__ == "__main__":
    main()
