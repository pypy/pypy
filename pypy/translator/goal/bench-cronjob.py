#! /usr/bin/env python

import time, os, sys, stat

current_result = '''
executable                        richards             pystone
python 2.4.2c1                      855ms (  1.00x)    44642 (  1.00x)
pypy-llvm-17884                   11034ms ( 12.91x)     3362 ( 13.28x)
pypy-llvm-17881                   11702ms ( 13.69x)     3240 ( 13.78x)
pypy-llvm-17870                   12683ms ( 14.83x)     3073 ( 14.53x)
pypy-llvm-17862                   13053ms ( 15.27x)     3017 ( 14.79x)
pypy-llvm-17797                   13497ms ( 15.79x)     2832 ( 15.76x)
pypy-llvm-17792                   13808ms ( 16.15x)     2818 ( 15.84x)
pypy-llvm-17758                   16998ms ( 19.88x)     2237 ( 19.96x)
pypy-c-17853                      22389ms ( 26.19x)     1651 ( 27.04x)
pypy-c-17806                      22328ms ( 26.11x)     1660 ( 26.88x)
pypy-c-17758                      23485ms ( 27.47x)     1598 ( 27.92x)
'''

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
