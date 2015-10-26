#!/usr/bin/python

import argparse
import re
from pkg_resources import parse_version

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
            '-t', '--tag', dest='tag', action='store', type=str,
            help='PyPi version tag', required=True, default='0'
    )

    params, other_params = parser.parse_known_args()

    pip_ver = params.tag
    # drop dashed part from version string because
    # it represents a patch level of given version
    pip_ver = pip_ver.split('-')[0]

    # add leading 1 if tag starts from letter
    if re.match(r"^[a-zA-Z]",pip_ver):
        pip_ver = '1' + pip_ver

    pip_ver_parts = parse_version(pip_ver)
    _ver = True
    pkg_ver_part = ""
    pkg_alpha = ""
    pkg_rev_part = ""
    for part in pip_ver_parts:
       if part == "*final":
           continue
       if re.match(r"[*a-z]",part):
           _ver = False
           pkg_alpha = re.sub(r"^\*", "~", part)
           continue
       if _ver:
           pkg_ver_part += "." + re.sub(r"^0+", "", part)
       else:
           pkg_rev_part += "." + re.sub(r"^0+", "", part)

    # remove leadind period from pkg_ver_part and pkg_rev_part
    pkg_ver_part = re.sub(r"^\.+", "", pkg_ver_part)
    pkg_rev_part = re.sub(r"^\.+", "", pkg_rev_part)
    # replace 'c' and '@' with 'rc' and 'dev' at pkg_alpha
    pkg_alpha = pkg_alpha.replace('c','rc')
    pkg_alpha = pkg_alpha.replace('@','dev')

    # expand version to three items
    while (pkg_ver_part.count(".") < 2):
        pkg_ver_part += ".0"

    print pkg_ver_part + pkg_alpha + pkg_rev_part

if __name__ == "__main__":
        main()
