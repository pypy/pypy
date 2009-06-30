#! /usr/bin/env python

import os
homedir = os.getenv('HOME')
os.environ['PATH'] += ':'+homedir+'/bin'

import autopath
import py
import time, os, sys, stat

os.umask(022)      # allow everyone to read/execute the produced pypy-c's


tmpdir  = py.std.tempfile.gettempdir() + '/usession-' + os.environ['USER'] + '/'
cflags  = "-O3"
lflags  = "-lgc -lm -lpthread"

dry_run = False

def run(cmd):
    print 'RUN:', cmd
    sys.stdout.flush()
    result = 0  #OK
    if not dry_run:
        result = os.system(cmd) #note: result is system dependent but works on Linux the way we want
    return result

def update_pypy():
    os.chdir(homedir + '/projects/pypy-trunk')
    run('/usr/local/bin/svn up 2>&1')

def compile(backend):
    try:
        backend, features = backend.split('--', 1)
        featureoptions = ''.join([" --" + f     for f in features.split('--') if f[0] != '_'])
        targetoptions  = ''.join([" --" + f[1:] for f in features.split('--') if f[0] == '_'])
    except:
        features       = ''
        featureoptions = ''
        targetoptions  = ''

    translateoptions = ''

    def normalize(f):
        if f.startswith('_'):
            f = f[1:]
        if f.startswith('profopt'):
            f = 'prof'
        return f
    features = '--'.join([normalize(f) for f in features.split('--')])

    os.chdir(homedir + '/projects/pypy-trunk/pypy/translator/goal')
    run('/usr/local/bin/python translate.py --backend=%(backend)s%(featureoptions)s%(translateoptions)s --batch targetpypystandalone.py %(targetoptions)s 2>&1' % locals())

    os.chdir(homedir + '/projects/pypy-trunk')
    try:
        revision = '%d' % (py.path.svnwc('.').info().rev,)
    except:
        revision = 'unknown'
    basename = homedir + '/projects/pypy-trunk/pypy/translator/goal/' + 'pypy-' + backend
    realname = basename + '-' + revision
    if features:
        realname += "-" + features

    if os.path.exists(basename):                   #copy executable
        run("mv %s %s" % (basename, realname))
        if backend == 'cli':
            basename_dir = basename + '-data'
            realname_dir = realname + '-data'
            run("mv %s %s" % (basename_dir, realname_dir))
        elif backend == 'jvm':
            basename_jar = basename + '.jar'
            realname_jar = realname + '.jar'
            run("mv %s %s" % (basename_jar, realname_jar))
        #pypy = open(basename, 'rb').read()
        #if len(pypy) > 0:
        #    open(realname, 'wb').write(pypy)
        #os.chmod(realname, stat.S_IRWXU)
        #os.unlink(basename)

def get_load():
    g = os.popen('uptime', 'r')
    buf = g.read().strip()
    g.close()
    return buf

def benchmark():
    os.chdir(homedir + '/projects/pypy-trunk/pypy/translator/goal')
    uname = os.popen('uname -a', 'r').read()
    startload = get_load()
#    result = run('/usr/local/bin/withlock /tmp/cpu_cycles_lock /usr/local/bin/python bench-unix.py 2>&1 | tee benchmark.txt' % locals())
    result = run('/usr/local/bin/python bench-unix.py 2>&1 | tee benchmark.txt' % locals())
    endload = get_load()
    if not dry_run and result == 0:
        f = open('benchmark.html', 'w')
        print >> f, "<html><body>"
        print >> f, "<pre>"
        print >> f, "uname -a:", uname
        print >> f, "Benchmark started:", startload
        print >> f, "            ended:", endload
        print >> f
        f.write(open('benchmark.txt').read())
        print >> f, "</pre>"
        print >> f, "</body></html>"
        f.close()

def main(backends=[]):
    if backends == []:  #_ prefix means target specific option, # prefix to outcomment
        backends = [backend.strip() for backend in """
            c--opt=0--_no-allworkingmodules
            c--stackless--gc=boehm--opt=3--_no-allworkingmodules
            c--gc=boehm--opt=3
            c--thread--gc=hybrid--opt=3--_no-allworkingmodules
            c--gc=semispace--opt=3--_no-allworkingmodules
            c--gc=generation--opt=3--_no-allworkingmodules
            c--gc=hybrid--opt=3--_no-allworkingmodules
            cli--opt=3--_no-allworkingmodules
            jvm--opt=3--_no-allworkingmodules
            jvm--inline-threshold=0--opt=3--_no-allworkingmodules
            """.split('\n') if backend.strip() and not backend.strip().startswith('#')]
    print time.ctime()
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
    args = sys.argv[1:]
    if args and args[0] == '--benchmark-only':
        benchmark()
    else:
        if args and args[0] == '--dry-run':
            del args[0]
            dry_run = True
        main(args)
