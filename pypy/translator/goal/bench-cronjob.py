#! /usr/bin/env python

import time, os, sys, stat

homedir = os.environ['HOME']

def update_pypy():
    os.chdir(homedir + '/projects/pypy-dist')
    os.system('svn up 2>&1')

def update_llvm():
    os.chdir(homedir + '/projects/llvm')
    os.system('cvs -q up 2>&1')
    os.system('make tools-only 2>&1')

def get_names():
    os.chdir(homedir + '/projects/pypy-dist')
    try:
        revision = os.popen('svn info 2>&1').readlines()[3].split()[1]
    except:
        revision = 'unknown'
    basename = homedir + '/projects/pypy-dist/pypy/translator/goal/' + 'pypy-' + backend
    realname = basename+'-'+revision()
    return basename, realname
    
def compile(backend):
    os.chdir(homedir + '/projects/pypy-dist/pypy/translator/goal')
    os.system('python translate_pypy_new.py targetpypystandalone --backend=%(backend)s --pygame --batch -r 2>&1' % locals())
    basename, realname = get_names()
    os.open(realname, 'wb').write( open(basename).read() )
    os.chmod(realname, stat.S_IRWXU)
    os.unlink(basename)

def benchmark():
    os.chdir(homedir + '/projects/pypy-dist/pypy/translator/goal')
    os.system('python bench-unix.py 2>&1' % locals())

def main():
    print time.ctime()
    update_pypy()
    update_llvm()
    for backend in 'c llvm'.split():
        compile(backend)
    print time.ctime()
    print 80*'-'

if __name__ == '__main__':
    main()
