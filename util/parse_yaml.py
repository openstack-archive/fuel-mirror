#!/usr/bin/python
# Enumerate YAML from stdin and produce prefixed output

import re
import sys
import yaml

prefix = sys.argv[1]


def serialize(value, name):
    if value is None:
        print('{0}=""'.format(name))
    elif hasattr(value, 'items'):
        for key, subvalue in value.items():
            key = re.sub(r'[\W]', '_', key)
            serialize(subvalue, name + '_' + key)
    elif hasattr(value, '__iter__'):
        print("{0}_len={1}".format(name, len(value)))
        for i, v in enumerate(value):
            serialize(v, name + '_' + str(i))
    else:
        print('{0}="{1}"'.format(name, value))

with sys.stdin as yaml_file:
    data = yaml.load(yaml_file)
    serialize(data, prefix)
