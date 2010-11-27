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
import os
import shutil

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
    alltars = []
    try:
        os.chdir(str(tmpdir))
        for (kind, platform), (rev, name) in to_download.iteritems():
            if platform == 'win32':
                print 'Ignoring %s, windows unsupported' % name
            else:
                print "Downloading %s at rev %d" % (name, rev)
                url = BASEURL + branch + "/" + name
                data = urllib2.urlopen(url).read()
                tmpdir.join(name).write(data, mode="wb")
                t = tarfile.open(str(tmpdir.join(name)))
                dirname = t.getmembers()[0].name
                t.extractall(path=str(tmpdir))
                os.system('mv %s %s' % (str(tmpdir.join(dirname)),
                                        str(tmpdir.join('pypy-%s' % release))))
                if kind == 'jit':
                    kind = ''
                else:
                    kind = '-' + kind
                olddir = os.getcwd()
                name = 'pypy-%s-%s%s.tar.bz2' % (release, platform, kind)
                print "Building %s" % name
                t = tarfile.open(name, 'w:bz2')
                t.add('pypy-%s' % release)
                alltars.append(name)
                t.close()
                shutil.rmtree(str(tmpdir.join('pypy-1.3')))
        for name in alltars:
            print "Uploading %s" % name
            os.system('scp %s codespeak.net:/www/pypy.org/htdocs/download' % name)
    finally:
        os.chdir(olddir)

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print __doc__
        sys.exit(1)
    main(sys.argv[1], release='1.3')
    
