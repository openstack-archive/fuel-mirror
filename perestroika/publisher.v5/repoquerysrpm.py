#!/usr/bin/python

from __future__ import print_function
import argparse
import gzip
import os

from lxml import etree as ET


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        '-s', '--srpm', dest='srpm', action='store', type=str,
        help='srpm', required=True, default='none'
    )

    parser.add_argument(
        '-p', '--path', dest='path', action='store', type=str,
        help='path', required=True, default='.'
    )

    params, other_params = parser.parse_known_args()

    repomdpath = os.path.join(params.path, 'repodata', 'repomd.xml')

    tree = ET.parse(repomdpath)
    repomd = tree.getroot()

    xmlpath = {}
    for data in repomd.findall(ET.QName(repomd.nsmap[None], 'data')):
        filetype = data.attrib['type']
        xmlpath[filetype] = data.find(
            ET.QName(repomd.nsmap[None], 'location')).attrib['href']

    primaryfile = os.path.join(params.path, xmlpath['primary'])

    with gzip.open(primaryfile, 'rb') as f:
        primary_content = f.read()

    primary = ET.fromstring(primary_content)

    filtered = primary.xpath('//rpm:sourcerpm[text()="' + params.srpm + '"]',
                             namespaces={'rpm': primary.nsmap['rpm']})

    for item in filtered:
        name = item.getparent().getparent().find(
            ET.QName(primary.nsmap[None], 'name')).text
        arch = item.getparent().getparent().find(
            ET.QName(primary.nsmap[None], 'arch')).text
        epoch = item.getparent().getparent().find(
            ET.QName(primary.nsmap[None], 'version')).attrib['epoch']
        ver = item.getparent().getparent().find(
            ET.QName(primary.nsmap[None], 'version')).attrib['ver']
        rel = item.getparent().getparent().find(
            ET.QName(primary.nsmap[None], 'version')).attrib['rel']
        location = item.getparent().getparent().find(
            ET.QName(primary.nsmap[None], 'location')).attrib['href']
        print('{name} {epoch} {ver} {rel} {arch} {location}'.format(
            name=name, epoch=epoch, ver=ver, rel=rel,
            arch=arch, location=location))


if __name__ == "__main__":
    main()
