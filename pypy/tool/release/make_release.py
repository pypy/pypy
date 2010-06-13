#!/usr/bin/env python

""" A tool to download correct pypy-c's from nightly build run and package them
into release packages. Note: you must run apropriate buildbots first and
make sure there are no failures. Use force-builds.py from the same directory.

Usage: make_release.py release/<release name>
"""

import sys
import urllib2
from xml.dom import minidom
import re

def browse_nightly(branch,
                   baseurl='http://buildbot.pypy.org/nightly/'):
    url = baseurl + branch + '/'
    dom = minidom.parseString(urllib2.urlopen(url).read())
    refs = [node.getAttribute('href') for node in dom.getElementsByTagName('a')]
    # all refs are of form: pypy-{type}-{revision}-{platform}.tar.bz2
    r = re.compile('pypy-c-([\w\d]+)-(\d+)-([\w\d]+).tar.bz2$')
    d = {}
    for ref in refs:
        kind, rev, platform = r.match(ref).groups()
        rev = int(rev)
        try:
            lastrev, _ = d[(kind, platform)]
        except KeyError:
            lastrev = -1
        if rev > lastrev:
            d[(kind, platform)] = rev, ref
    return d

def main(branch):
    to_download = browse_nightly(branch)
    xxx # finish me

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print __doc__
        sys.exit(1)
    main(sys.argv[1])
    
