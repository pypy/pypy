#!/usr/bin/env python

import sys
import os
import py

if sys.platform.startswith('linux'):
    arch = 'linux'
else:
    print 'Cannot determine the platform, please update this scrip'
    sys.exit(1)

if sys.maxint == 2**63 - 1:
    arch += '64'

hg = py.path.local.sysfind('hg')
branch = hg.sysexec('branch').strip()
if branch == 'default':
    branch = 'trunk'

filename = 'pypy-c-jit-latest-%s.tar.bz2' % arch
url = 'http://buildbot.pypy.org/nightly/%s/%s' % (branch, filename)
tmp = py.path.local.mkdtemp()
mydir = tmp.chdir()
print 'Downloading pypy to', tmp
if os.system('wget "%s"' % url) != 0:
    sys.exit(1)

print 'Extracting pypy binary'
mydir.chdir()
os.system("tar -x -v --wildcards --strip-components=2 -f %s '*/bin/pypy'" % tmp.join(filename))

