#! /usr/bin/env python

import autopath
import py
import time, os, sys, stat

homedir = os.getenv('HOME')

def update_pypy():
    os.chdir(homedir + '/projects/pypy-dist')
    os.system('svn up 2>&1')

def update_llvm():
    os.chdir(homedir + '/projects/llvm')
    os.system('cvs -q up 2>&1')
    os.system('make clean 2>&1')
    os.system('make -j3 tools-only 2>&1')

def compile_llvm_variants(revision):
    tmpdir = py.std.tempfile.gettempdir() + '/usession-' + os.environ['USER'] + '/'

    cmd = 'cp %sentry_point.ll pypy/translator/goal/entry_point-%s.ll' % (tmpdir, revision)
    print cmd
    os.system(cmd)

    #this assumes entry_point.bc is created with llvm 1.6 and pypy-llvm-<revision> is already created with the llvm c backend
    b = "pypy/translator/goal/pypy-llvm-%s" % revision
    cmd = "mv %s %s-llvm1_6_c" % (b, b)
    print cmd
    os.system(cmd)

    #
    b = "%spypy-llvm-%s-llvm1_6_x86" % (tmpdir, revision)

    cmd = "llc %sentry_point.bc -f -o %s.s" % (tmpdir, b)
    print cmd
    os.system(cmd)

    cmd = "as %s.s -o %s.o" % (b, b)
    print cmd
    os.system(cmd)

    cmd = "gcc %s.o -static -lgc -lm -lpthread -pipe -o %s" % (b, b)
    print cmd
    os.system(cmd)

    cmd = "cp %s pypy/translator/goal" % b
    print cmd
    os.system(cmd)
   

    #
    b = "%spypy-llvm-%s-llvm1_7_c" % (tmpdir, revision)

    cmd = '~/bin/llvm-as < %sentry_point.ll | ~/bin/opt -verify -lowersetjmp -funcresolve -raiseallocs -simplifycfg -mem2reg -globalopt -globaldce -ipconstprop -deadargelim -instcombine -simplifycfg -basiccg -prune-eh -inline -simplify-libcalls -basiccg -argpromotion -raise -tailduplicate -simplifycfg -scalarrepl -instcombine -break-crit-edges -condprop -tailcallelim -simplifycfg -reassociate -loopsimplify -licm -instcombine -indvars -loop-unroll -instcombine -load-vn -gcse -sccp -instcombine -break-crit-edges -condprop -dse -mergereturn -adce -simplifycfg -deadtypeelim -constmerge -verify -globalopt -constmerge -ipsccp -deadargelim -inline -instcombine -scalarrepl -globalsmodref-aa -licm -load-vn -gcse -instcombine -simplifycfg -globaldce -f -o %sentry_point_llvm1_7.bc' % (tmpdir, tmpdir)
    print cmd
    os.system(cmd)

    cmd = "~/bin/llc %sentry_point_llvm1_7.bc -march=c -f -o %s.c" % (tmpdir, b)
    print cmd
    os.system(cmd)

    cmd = "gcc %s.c -O2 -fomit-frame-pointer -static -lgc -lm -lpthread -pipe -o %s" % (b, b)
    print cmd
    os.system(cmd)

    cmd = "cp %s pypy/translator/goal" % b
    print cmd
    os.system(cmd)


    #
    b = "%spypy-llvm-%s-llvm1_7_x86" % (tmpdir, revision)
    os.system('~/bin/llc -version 2>&1')

    cmd = "~/bin/llc %sentry_point_llvm1_7.bc -f -o %s.s" % (tmpdir, b)
    print cmd
    os.system(cmd)

    cmd = "as %s.s -o %s.o" % (b, b)
    print cmd
    os.system(cmd)

    cmd = "gcc %s.o -static -lgc -lm -lpthread -pipe -o %s" % (b, b)
    print cmd
    os.system(cmd)

    cmd = "cp %s pypy/translator/goal" % b
    print cmd
    os.system(cmd)


def compile(backend):
    os.chdir(homedir + '/projects/pypy-dist/pypy/translator/goal')
    os.system('/usr/local/bin/python translate_pypy.py --backend=%(backend)s --text --batch targetpypystandalone.py 2>&1' % locals())

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

    if backend == 'llvm':
        compile_llvm_variants(revision)

def benchmark():
    os.system('cat /proc/cpuinfo')
    os.system('free')
    os.chdir(homedir + '/projects/pypy-dist/pypy/translator/goal')
    os.system('/usr/local/bin/python bench-unix.py 2>&1 | tee benchmark.txt' % locals())
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
