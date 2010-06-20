#!/usr/bin/env python

""" A tool to download correct pypy-c's from nightly build run and package them
into release packages. Note: you must run apropriate buildbots first and
make sure there are no failures. Use force-builds.py from the same directory.

Usage: make_release.py release/<release name>
"""

import autopath
import sys
import urllib2
from xml.dom import minidom
import re
import py
from pypy.tool.udir import udir
from pypy.tool.release.package import package
import tarfile

BASEURL = 'http://buildbot.pypy.org/nightly/'

def browse_nightly(branch,
                   baseurl=BASEURL,
                   override_xml=None):
    if override_xml is None:
        url = baseurl + branch + '/'
        xml = urllib2.urlopen(url).read()
    else:
        xml = override_xml
    dom = minidom.parseString(xml)
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

def main(branch, release):
    to_download = browse_nightly(branch)
    tmpdir = udir.join('download')
    tmpdir.ensure(dir=True)
    for (kind, platform), (rev, name) in to_download.iteritems():
        if platform == 'win32':
            print 'Ignoring %s, windows unsupported' % name
        else:
            print "Downloading %s at rev %d" % (name, rev)
            url = BASEURL + branch + "/" + name
            data = urllib2.urlopen(url).read()
            tmpdir.join(name).write(data, mode="wb")
            t = tarfile.open(str(tmpdir.join(name)))
            data = t.extractfile('pypy-c').read()
            pypy_c = tmpdir.join('pypy-c')
            pypy_c.write(data, mode="wb")
            if kind == 'jit':
                kind = ''
            else:
                kind = '-' + kind
            name = 'pypy-%s%s-%s' % (release, kind, platform)
            builddir = package(py.path.local(autopath.pypydir).join('..'),
                               name=name,
                               override_pypy_c=pypy_c)
            print "Build %s/%s.tar.bz2" % (builddir, name)
    print "\nLook into %s for packages" % builddir

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print __doc__
        sys.exit(1)
    main(sys.argv[1], release='1.3')
    
