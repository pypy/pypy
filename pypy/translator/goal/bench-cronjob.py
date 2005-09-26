#! /usr/bin/env python

import time, os, sys, stat

homedir = os.getenv('HOME')
os.putenv('PATH','~/bin:/usr/local/bin:/usr/bin:/bin:/opt/bin:/usr/i686-pc-linux-gnu/gcc-bin/3.3.6')

def update_pypy():
    os.chdir(homedir + '/projects/pypy-dist')
    os.system('svn up 2>&1')

def update_llvm():
    os.chdir(homedir + '/projects/llvm')
    os.system('cvs -q up 2>&1')
    os.system('make tools-only 2>&1')

def compile(backend):
    os.chdir(homedir + '/projects/pypy-dist/pypy/translator/goal')
    os.system('python translate_pypy_new.py targetpypystandalone --backend=%(backend)s --pygame --batch -r 2>&1' % locals())

    os.chdir(homedir + '/projects/pypy-dist')
    try:
        revision = os.popen('svn info 2>&1').readlines()[3].split()[1]
    except:
        revision = 'unknown'
    basename = homedir + '/projects/pypy-dist/pypy/translator/goal/' + 'pypy-' + backend
    realname = basename + '-' + revision

    pypy = open(basename, 'rb').read()
    if len(pypy) > 0:
        open(realname, 'wb').write(pypy)
    os.chmod(realname, stat.S_IRWXU)
    os.unlink(basename)

def benchmark():
    os.system('cat /proc/cpuinfo')
    os.system('free')
    os.chdir(homedir + '/projects/pypy-dist/pypy/translator/goal')
    os.system('python bench-unix.py 2>&1' % locals())

def main(backends=[]):
    if backends == []:
        backends = 'llvm c'.split()
    print time.ctime()
    update_pypy()
    update_llvm()
    for backend in backends:
        compile(backend)
    benchmark()
    print time.ctime()
    print 80*'-'

if __name__ == '__main__':
    main(sys.argv[1:])
