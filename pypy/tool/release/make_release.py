#!/usr/bin/env python

""" A tool to download correct pypy-c's from nightly build run and package them
into release packages. Note: you must run apropriate buildbots first and
make sure there are no failures. Use force-builds.py from the same directory.

Usage: make_release.py  <branchname>  <version>
 e.g.: make_release.py  release-1.4.1  1.4.1
"""

import autopath
import sys
import urllib2
from xml.dom import minidom
import re
import py
from rpython.tool.udir import udir
from pypy.tool.release.package import package
import tarfile
import os
import shutil

BASEURL = 'http://buildbot.pypy.org/nightly/'
PAUSE = False

def browse_nightly(branch,
                   baseurl=BASEURL,
                   override_xml=None):
    if override_xml is None:
        url = baseurl + branch + '/'
        xml = urllib2.urlopen(url).read()
    else:
        xml = override_xml
    dom = minidom.parseString(xml)
    refs = [node.getAttribute('href') for node in dom.getElementsByTagName('a')
            if 'pypy' in node.getAttribute('href')]
    # all refs are of form: pypy-c-{type}-{revnum}-{hghash}-{platform}.tar.bz2
    r = re.compile('pypy-c-([\w\d]+)-(\d+)-([0-9a-f]+)-([\w\d]+).tar.bz2$')
    d = {}
    for ref in refs:
        kind, revnum, hghash, platform = r.match(ref).groups()
        rev = int(revnum)
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
    olddir = os.getcwd()
    try:
        os.chdir(str(tmpdir))
        print 'Using tmpdir', str(tmpdir)
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
                if kind == 'jit':
                    kind = ''
                else:
                    kind = '-' + kind
                topdirname = 'pypy-%s-%s%s' % (release, platform, kind)
                os.system('mv %s %s' % (str(tmpdir.join(dirname)),
                                        str(tmpdir.join(topdirname))))
                if PAUSE:
                    print 'Pausing, press Enter...'
                    raw_input()
                name = '%s.tar.bz2' % topdirname
                print "Building %s" % name
                t = tarfile.open(name, 'w:bz2')
                t.add(topdirname)
                alltars.append(name)
                t.close()
                shutil.rmtree(str(tmpdir.join(topdirname)))
        for name in alltars:
            print "Uploading %s" % name
            os.system('scp %s codespeak.net:/www/pypy.org/htdocs/download' % name)
    finally:
        os.chdir(olddir)

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print __doc__
        sys.exit(1)
    main(sys.argv[1], release=sys.argv[2])
    
