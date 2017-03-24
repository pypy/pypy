#!/usr/bin/env python

import sys
import os
import py

TAR_OPTIONS = '-x -v --strip-components=2'
TAR = 'tar {options} -f {tarfile} {files}'

def untar(tarfile, files):
    cmd = TAR.format(options=TAR_OPTIONS, tarfile=tarfile, files=files)
    os.system(cmd)

if sys.platform.startswith('linux'):
    arch = 'linux'
    cmd = 'wget "%s"'
    TAR_OPTIONS += ' --wildcards'
    binfiles = "'*/bin/pypy' '*/bin/libpypy-c.so'"
    if os.uname()[-1].startswith('arm'):
        arch += '-armhf-raspbian'
elif sys.platform.startswith('darwin'):
    arch = 'osx'
    cmd = 'curl -O "%s"'
    binfiles = "'*/bin/pypy'"
else:
    print 'Cannot determine the platform, please update this script'
    sys.exit(1)

if sys.maxint == 2**63 - 1:
    arch += '64'

hg = py.path.local.sysfind('hg')
branch = hg.sysexec('branch').strip()
if branch == 'default':
    branch = 'trunk'

if '--nojit' in sys.argv:
    kind = 'nojit'
else:
    kind = 'jit'

filename = 'pypy-c-%s-latest-%s.tar.bz2' % (kind, arch)
url = 'http://buildbot.pypy.org/nightly/%s/%s' % (branch, filename)
tmp = py.path.local.mkdtemp()
pypy_latest = tmp.join(filename)
mydir = tmp.chdir()
print 'Downloading pypy to', tmp
if os.system(cmd % url) != 0:
    sys.exit(1)

print 'Extracting pypy binary'
mydir.chdir()
untar(pypy_latest, binfiles)
include_dir = py.path.local('../../include')
if include_dir.check(dir=True):
    include_dir.chdir()
    untar(pypy_latest, '*/include/*')
else:
    print 'WARNING: could not find the include/ dir'
