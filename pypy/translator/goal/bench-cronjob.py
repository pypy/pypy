#! /usr/bin/env python

import autopath
import py
import time, os, sys, stat
from pypy.translator.llvm.buildllvm import optimizations

homedir = os.getenv('HOME')
tmpdir  = py.std.tempfile.gettempdir() + '/usession-' + os.environ['USER'] + '/'

def update_pypy():
    os.chdir(homedir + '/projects/pypy-dist')
    os.system('svn up 2>&1')

def update_llvm():
    os.chdir(homedir + '/projects/llvm')
    os.system('cvs -q up 2>&1')
    os.system('make -k -j3 tools-only 2>&1')

def compile_llvm_variants(revision):
    ll2bc(revision)
    bc2x86_exe(revision, 'x86A', '-enable-x86-fastcc -relocation-model=static -join-liveintervals')
    bc2x86_exe(revision, 'x86B', '-relocation-model=static')
    bc2x86_exe(revision, 'x86C', '')
    bc2c_exe(revision)


def ll2bc(revision):
    cmd = 'cp %spypy.ll pypy/translator/goal/archive/pypy-%s.ll' % (tmpdir, revision)
    print cmd
    os.system(cmd)

    opts = optimizations(simple=False, use_gcc=False)
    cmd  = '~/bin/llvm-as < %spypy.ll | ~/bin/opt %s -f -o %spypy.bc' % (
        tmpdir, opts, tmpdir)
    print cmd
    os.system(cmd)

    cmd = 'cp %spypy.bc pypy/translator/goal/archive/pypy-%s.bc' % (tmpdir, revision)
    print cmd
    os.system(cmd)


def bc2c_exe(revision):
    b   = "%spypy-llvm-%s-c" % (tmpdir, revision)
    cmd = "~/bin/llc %spypy.bc -march=c -f -o %s.c" % (tmpdir, b)
    print cmd
    os.system(cmd)

    cmd = "cp %s.c pypy/translator/goal/archive" % b
    print cmd
    os.system(cmd)

    cmd = "gcc %s.c -S -O3 -fomit-frame-pointer -o %s.s" % (b, b)
    print cmd
    os.system(cmd)

    cmd = "cp %s.s pypy/translator/goal/archive" % b
    print cmd
    os.system(cmd)

    cmd = "gcc %s.s -lgc -lm -lpthread -pipe -o %s" % (b, b) #XXX -static
    print cmd
    os.system(cmd)

    cmd = "cp %s pypy/translator/goal" % b
    print cmd
    os.system(cmd)


def bc2x86_exe(revision, name_extra, llc_extra_options):
    b   = "%spypy-llvm-%s-%s" % (tmpdir, revision, name_extra)
    cmd = "~/bin/llc %spypy.bc %s -f -o %s.s" % (tmpdir, llc_extra_options, b)
    print cmd
    os.system(cmd)

    cmd = 'cp %s.s pypy/translator/goal/archive' % b
    print cmd
    os.system(cmd)

    cmd = "gcc %s.s -lgc -lm -lpthread -pipe -o %s" % (b, b) #XXX -static
    print cmd
    os.system(cmd)

    cmd = "cp %s pypy/translator/goal" % b
    print cmd
    os.system(cmd)


def compile(backend):
    try:
        backend, features = backend.split('--', 1)
        featureoptions = ''.join([" --" + f     for f in features.split('--') if f[0] != '_'])
        targetoptions  = ''.join([" --" + f[1:] for f in features.split('--') if f[0] == '_'])
    except:
        features       = ''
        featureoptions = ''
        targetoptions  = ''

    if backend == 'llvm':
        translateoptions = ' --source'
    else:
        translateoptions = ''

    os.chdir(homedir + '/projects/pypy-dist/pypy/translator/goal')
    os.system('/usr/local/bin/python translate.py --backend=%(backend)s%(featureoptions)s%(translateoptions)s --text --batch targetpypystandalone.py %(targetoptions)s 2>&1' % locals())
    os.system('mv %s/entry_point.ll %s/pypy.ll' % (tmpdir, tmpdir))

    os.chdir(homedir + '/projects/pypy-dist')
    try:
        revision = os.popen('svn info 2>&1').readlines()[3].split()[1]
    except:
        revision = 'unknown'
    basename = homedir + '/projects/pypy-dist/pypy/translator/goal/' + 'pypy-' + backend
    realname = basename + '-' + revision
    if features:
        realname += "-" + features

    if backend == 'llvm':   #create llvm exectutable from the current source
        compile_llvm_variants(revision)
    else:                   #copy executable
        pypy = open(basename, 'rb').read()
        if len(pypy) > 0:
            open(realname, 'wb').write(pypy)
        os.chmod(realname, stat.S_IRWXU)
        os.unlink(basename)

def benchmark():
    #os.system('cat /proc/cpuinfo')
    #os.system('free')
    os.chdir(homedir + '/projects/pypy-dist/pypy/translator/goal')
    os.system('/usr/local/bin/python bench-unix.py 2>&1 | tee benchmark.txt' % locals())
    os.system('echo "<html><body><pre>"    >  benchmark.html')
    os.system('cat benchmark.txt           >> benchmark.html')
    os.system('echo "</pre></body></html>" >> benchmark.html')
    os.system('scp benchmark.html ericvrp@codespeak.net:public_html/benchmark/index.html')

def main(backends=[]):
    if backends == []:  #_ prefix means target specific option
        backends = 'llvm c c--gc=framework c--stackless c--_thread c--stackless--_thread'.split()
        #backends = 'llvm c c--stackless c--_thread c--stackless--_thread'.split()
        #backends = 'llvm c c--stackless c--gc=ref c--gc=ref--stackless c--_thread c--gc=ref--_thread'.split()
    print time.ctime()
    if 'llvm' in backends:
        update_llvm()
    update_pypy()
    for backend in backends:
        try:
            compile(backend)
        except:
            raise
            pass
    benchmark()
    print time.ctime()
    print 80*'-'

if __name__ == '__main__':
    main(sys.argv[1:])
