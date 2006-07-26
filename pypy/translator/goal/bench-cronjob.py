#! /usr/bin/env python

import autopath
import py
import time, os, sys, stat
from pypy.translator.llvm.buildllvm import optimizations

os.umask(022)      # allow everyone to read/execute the produced pypy-c's

homedir = os.getenv('HOME')
tmpdir  = py.std.tempfile.gettempdir() + '/usession-' + os.environ['USER'] + '/'
cflags  = "-march=pentium4 -O3 -fomit-frame-pointer"
lflags  = "-lgc -lm -lpthread"

def run(cmd):
    print 'RUN:', cmd
    os.system(cmd)

def update_pypy():
    os.chdir(homedir + '/projects/pypy-dist')
    run('svn up 2>&1')

def update_llvm():
    os.chdir(homedir + '/projects/llvm')
    run('cvs -q up 2>&1')
    run('make -k -j3 tools-only 2>&1')

def compile_llvm_variants(revision):
    ll2bc(revision)

    bc2c_exe(revision, 'from richards import *;main(iterations=1)')

    bc2x86_exe(revision, 'x86', '-relocation-model=static')
    #bc2x86_exe(revision, 'x86A', '-enable-x86-fastcc -relocation-model=static -join-liveintervals')
    #bc2x86_exe(revision, 'x86B', '-relocation-model=static')
    #bc2x86_exe(revision, 'x86C', '')


def ll2bc(revision):
    cmd = 'cp %spypy.ll pypy/translator/goal/archive/pypy-%s.ll' % (tmpdir, revision)
    run(cmd)

    opts = optimizations(simple=False, use_gcc=False)
    cmd  = '~/bin/llvm-as < %spypy.ll | ~/bin/opt %s -f -o %spypy.bc' % (
        tmpdir, opts, tmpdir)
    run(cmd)

    cmd = 'cp %spypy.bc pypy/translator/goal/archive/pypy-%s.bc' % (tmpdir, revision)
    run(cmd)


def bc2c_exe(revision, profile_command=None):
    filename = "pypy-llvm-%s-c" % revision
    b = tmpdir + filename

    run("~/bin/llc %spypy.bc -march=c -f -o %s.c" % (tmpdir, b))
    run("cp %s.c pypy/translator/goal/archive" % b)
    run("gcc %s.c %s -S -o %s.s" % (b, cflags, b))
    run("cp %s.s pypy/translator/goal/archive" % b)
    run("gcc %s.s %s -o %s" % (b, lflags, b))
    run("cp %s pypy/translator/goal" % b)

    if profile_command:
        run("gcc %s.c -fprofile-generate %s -S -o %s.s" % (b, cflags, b))
        run("gcc %s.s -fprofile-generate %s -o %s" % (b, lflags, b))
        run("%s -c '%s'" % (b, profile_command))
        run("gcc %s.c -fprofile-use %s -S -o %s.s" % (b, cflags, b))
        run("cp %s.s pypy/translator/goal/archive/%s-prof.s" % (b, filename))
        run("gcc %s.s -fprofile-use %s -o %s" % (b, lflags, b))
        run("cp %s pypy/translator/goal/%s-prof" % (b, filename))

def bc2x86_exe(revision, name_extra, llc_extra_options):
    b   = "%spypy-llvm-%s-%s" % (tmpdir, revision, name_extra)
    cmd = "~/bin/llc %spypy.bc %s -f -o %s.s" % (tmpdir, llc_extra_options, b)
    run(cmd)

    cmd = 'cp %s.s pypy/translator/goal/archive' % b
    run(cmd)

    cmd = "gcc %s.s %s -o %s" % (b, lflags, b)
    run(cmd)

    cmd = "cp %s pypy/translator/goal" % b
    run(cmd)


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
        translateoptions = ' --source --raisingop2direct_call'
    else:
        translateoptions = ''

    os.chdir(homedir + '/projects/pypy-dist/pypy/translator/goal')
    run('/usr/local/bin/python translate.py --backend=%(backend)s%(featureoptions)s%(translateoptions)s --text --batch targetpypystandalone.py %(targetoptions)s 2>&1' % locals())
    run('mv %s/entry_point.ll %s/pypy.ll' % (tmpdir, tmpdir))

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
    elif os.path.exists(basename):                   #copy executable
        pypy = open(basename, 'rb').read()
        if len(pypy) > 0:
            open(realname, 'wb').write(pypy)
        os.chmod(realname, stat.S_IRWXU)
        os.unlink(basename)

def benchmark():
    #run('cat /proc/cpuinfo')
    #run('free')
    os.chdir(homedir + '/projects/pypy-dist/pypy/translator/goal')
    run('/usr/local/bin/python bench-unix.py 2>&1 | tee benchmark.txt' % locals())
    run('echo "<html><body><pre>"    >  benchmark.html')
    run('cat benchmark.txt           >> benchmark.html')
    run('echo "</pre></body></html>" >> benchmark.html')
    #run('scp benchmark.html ericvrp@codespeak.net:public_html/benchmark/index.html')

def main(backends=[]):
    if backends == []:  #_ prefix means target specific option
        #backends = """llvm@c@c--gc=framework@c--_thread@c--stackless@c--gc=framework--cc=c++@c--cc=c++""".split('@')
        backends = """llvm@c@c--gc=framework@c--_thread@c--stackless@c--gc=framework--cc=c++@c--cc=c++@c--profopt='-c "from richards import *;main(iterations=1)"'""".split('@')
        #backends = 'llvm c c--gc=framework c--_thread c--stackless'.split()
        #backends = 'llvm c c--gc=framework c--new-stackless c--_thread'.split()
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
