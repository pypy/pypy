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
    os.system('make clean 2>&1')
    os.system('make -j3 tools-only 2>&1')

def compile(backend):
    os.chdir(homedir + '/projects/pypy-dist')
    os.system('rm `find . -name *.pyc`')

    os.chdir(homedir + '/projects/pypy-dist/pypy/_cache')
    os.system('rm *')

    os.chdir(homedir + '/projects/pypy-dist/pypy/translator/goal')
    os.system('python translate_pypy.py --backend=%(backend)s --text --batch targetpypystandalone 2>&1' % locals())

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
    os.system('python bench-unix.py 2>&1 | tee benchmark.txt' % locals())
    os.system('echo "<html><body><pre>"    >  benchmark.html')
    os.system('cat benchmark.txt           >> benchmark.html')
    os.system('echo "</pre></body></html>" >> benchmark.html')
    os.system('scp benchmark.html ericvrp@codespeak.net:public_html/benchmark/index.html')

def main(backends=[]):
    if backends == []:
        backends = 'llvm c'.split()
    print time.ctime()
    #if 'llvm' in backends:
    #    update_llvm()
    update_pypy()
    for backend in backends:
        try:
            compile(backend)
        except:
            pass
    benchmark()
    print time.ctime()
    print 80*'-'

if __name__ == '__main__':
    main(sys.argv[1:])
