"""
simple scrpt for junitxml file merging
"""

from lxml.etree import parse, Element
from collections import defaultdict
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--out')
parser.add_argument('path', nargs='...')


TEST_ITEMS = 'test', 'errors', 'skips'


def merge(files):
    accum = defaultdict(int)
    children = []

    for item in files:
        root = item.getroot()
        for key, value in root.attrib.items():
            if not value:
                continue
            value = float(value) if '.' in value else int(value)
            accum[key] += value
        children.extend(root)

    assert len(children) == sum(accum[x] for x in TEST_ITEMS)

    children.sort(key=lambda x:(x.attrib['classname'], x.attrib['name']))
    new = Element(
        'testsuite',
        dict((k, str(v)) for k, v in accum.items()))
    new.extend(children)

    return new

def run(paths, out):

    files = map(parse, paths)
    merged = merge(files)

    with open(out, 'wb') as fp:
        merged.getroottree().write(fp)


if __name__ == '__main__':
    opts = parser.parse_args()
    run(opts.path, opts.out)

