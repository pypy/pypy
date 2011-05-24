import autopath
import package
import subprocess
import py, sys
import shutil

pypydir = py.path.local(autopath.pypydir)
builddir = pypydir.join('translator', 'goal')

VERSION = "1.5.0a0"

def make_pypy(tag, options):
    pypy = 'pypy%s' % (tag,)
    args = [sys.executable,
         str(builddir.join('translate.py')),
         '--output=' + pypy,
         ] + options
    print "Execute", args
    p = subprocess.Popen(args, cwd=str(builddir))
    p.wait()
    zipfile = 'pypy-%s-win32%s' % (VERSION, tag)
    package.package(pypydir.dirpath(), zipfile, pypy, pypydir)

shutil.copy(str(pypydir.join('..', '..', 'expat-2.0.1', 'win32', 'bin', 'release', 'libexpat.dll')), str(builddir))

make_pypy('',            ['-Ojit'])
make_pypy('-nojit',      [])
#make_pypy('-stackless', [--stackless])
#make_pypy('-sandbox',   [--sandbox])
