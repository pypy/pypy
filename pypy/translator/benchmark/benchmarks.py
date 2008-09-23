import os, sys, time, pickle, re, py

class BenchmarkFailed(Exception):
    pass

PYSTONE_CMD = 'from test import pystone;pystone.main(%s)'
PYSTONE_PATTERN = 'This machine benchmarks at'
PYSTONE_ASCENDING_GOOD = True

RICHARDS_CMD = 'from richards import *;main(iterations=%d)'
RICHARDS_PATTERN = 'Average time per iteration:'
RICHARDS_ASCENDING_GOOD = False

def get_result(txt, pattern):
    for line in txt.split('\n'):
        if line.startswith(pattern):
            break
    else:
        raise BenchmarkFailed
    return float(line.split()[len(pattern.split())])

class Benchmark(object):
    def __init__(self, name, runner, asc_good, units, check=lambda:True):
        self.name = name
        self._run = runner
        self.asc_good = asc_good
        self.units = units
        self.check = check
    def run(self, exe):
        try:
            return self._run(exe)
        except BenchmarkFailed:
            return '-FAILED-'

def external_dependency(dirname, svnurl, revision):
    """Check out (if necessary) a given fixed revision of a svn url."""
    dirpath = py.magic.autopath().dirpath().join(dirname)
    revtag = dirpath.join('-svn-rev-')
    if dirpath.check():
        if not revtag.check() or int(revtag.read()) != revision:
            print >> sys.stderr, ("Out-of-date benchmark checkout!"
                                  " I won't update it automatically.")
            print >> sys.stderr, ("To continue, move away or remove the "
                                  "%r directory." % (dirname,))
            sys.exit(1)
        return True
    CMD = "svn co -r%d %s@%d %s" % (revision, svnurl, revision, dirpath)
    print >> sys.stderr, CMD
    err = os.system(CMD)
    if err != 0:
        print >> sys.stderr, "* checkout failed, skipping this benchmark"
        return False
    revtag.write(str(revision))
    return True

def run_cmd(cmd):
    #print "running", cmd
    pipe = os.popen(cmd + ' 2>&1')
    r = pipe.read()
    status = pipe.close()
    if status:
        raise BenchmarkFailed(status)
    return r

def run_pystone(executable='/usr/local/bin/python', n=''):
    distdir = py.magic.autopath().dirpath().dirpath().dirpath().dirpath()
    pystone = distdir.join('lib-python').join('2.4.1').join('test').join('pystone.py')
    txt = run_cmd('"%s" "%s" %s' % (executable, pystone, n))
    return get_result(txt, PYSTONE_PATTERN)

def run_richards(executable='/usr/local/bin/python', n=5):
    richards = py.magic.autopath().dirpath().dirpath().join('goal').join('richards.py')
    txt = run_cmd('"%s" %s %s' % (executable, richards, n))
    return get_result(txt, RICHARDS_PATTERN)

def run_translate(executable='/usr/local/bin/python'):
    translate = py.magic.autopath().dirpath().dirpath().join('goal').join('translate.py')
    target = py.magic.autopath().dirpath().dirpath().join('goal').join('targetrpystonedalone.py')
    argstr = '%s %s --batch --backendopt --no-compile %s > /dev/null 2> /dev/null'
    T = time.time()
    status = os.system(argstr%(executable, translate, target))
    r = time.time() - T
    if status:
        raise BenchmarkFailed(status)
    return r

def run_docutils(executable='/usr/local/bin/python'):
    docutilssvnpath = 'docutils'    # subdir of the local dir
    translatetxt = py.magic.autopath().dirpath().dirpath().dirpath().join('doc').join('translation.txt')
    command = """import sys
sys.modules['unicodedata'] = sys # docutils need 'import unicodedata' to work, but no more...
sys.path[0:0] = ['%s', '%s/extras']
from docutils.core import publish_cmdline
publish_cmdline(writer_name='html')
"""%(docutilssvnpath, docutilssvnpath)
    T = time.time()
    pid = os.fork()
    if not pid:
        davenull = os.open('/dev/null', os.O_RDWR)
        os.dup2(davenull, 0)
        os.dup2(davenull, 1)
        os.dup2(davenull, 2)
        status = os.spawnv(os.P_WAIT, executable, [executable, '-c', command, str(translatetxt)])
        os._exit(status)
    else:
        status = os.waitpid(pid, 0)[1]
    r = time.time() - T
    if status:
        raise BenchmarkFailed(status)
    return r

def check_docutils():
    return False     # useless benchmark - I've seen 15% of difference
                     # between two successive runs on the same machine!
    #return external_dependency('docutils',
    #                           'svn://svn.berlios.de/docutils/trunk/docutils',
    #                           4821)

def run_templess(executable='/usr/local/bin/python'):
    """ run some script in the templess package

        templess is some simple templating language, to check out use
        'svn co -r100 http://johnnydebris.net/templess/trunk templess'
    """
    here = py.magic.autopath().dirpath()
    pypath = os.path.dirname(os.path.dirname(py.__file__))
    templessdir = here.join('templess')
    testscript = templessdir.join('test/oneshot.py')
    command = 'PYTHONPATH="%s:%s" "%s" "%s" 100' % (here, pypath,
                                                    executable, testscript)
    txt = run_cmd(command)
    try:
        result = float([line for line in txt.split('\n') if line.strip()][-1])
    except ValueError:
        raise BenchmarkFailed
    return result

def check_templess():
    return external_dependency('templess',
                               'http://johnnydebris.net/templess/trunk',
                               100)

def run_gadfly(executable='/usr/local/bin/python'):
    """ run some tests in the gadfly pure Python database """
    here = py.magic.autopath().dirpath()
    gadfly = here.join('gadfly')
    testscript = gadfly.join('test', 'testsubset.py')
    command = 'PYTHONPATH="%s" "%s" "%s"' % (gadfly, executable, testscript)
    txt = run_cmd(command)
    lines = [line for line in txt.split('\n') if line.strip()]
    if lines[-1].strip() != 'OK':
        raise BenchmarkFailed
    lastword = lines[-2].split()[-1]
    if not lastword.endswith('s'):
        raise BenchmarkFailed
    try:
        result = float(lastword[:-1])
    except ValueError:
        raise BenchmarkFailed
    return result

def check_gadfly():
    return external_dependency('gadfly',
              'http://codespeak.net/svn/user/arigo/hack/pypy-hack/gadflyZip',
              54470)

def run_mako(executable='/usr/local/bin/python'):
    """ run some tests in the mako templating system """
    here = py.magic.autopath().dirpath()
    mako = here.join('mako')
    testscript = mako.join('examples', 'bench', 'basic.py')
    command = 'PYTHONPATH="%s" "%s" "%s" mako' % (mako.join('lib'),
                                                  executable, testscript)
    txt = run_cmd(command)
    lines = [line for line in txt.split('\n') if line.strip()]
    words = lines[-1].split()
    if words[0] != 'Mako:':
        raise BenchmarkFailed
    try:
        result = float(words[1])
    except ValueError:
        raise BenchmarkFailed
    return result

def check_mako():
    return external_dependency('mako',
              'http://codespeak.net/svn/user/arigo/hack/pypy-hack/mako',
              40235)

def check_translate():
    return False   # XXX what should we do about the dependency on ctypes?

BENCHMARKS = [Benchmark('richards', run_richards, RICHARDS_ASCENDING_GOOD, 'ms'),
              Benchmark('pystone', run_pystone, PYSTONE_ASCENDING_GOOD, ''),
              Benchmark('translate', run_translate, RICHARDS_ASCENDING_GOOD, 'ms', check_translate),
              Benchmark('docutils', run_docutils, RICHARDS_ASCENDING_GOOD,
                        's', check_docutils),
              Benchmark('templess', run_templess, RICHARDS_ASCENDING_GOOD,
                        's', check_templess),
              Benchmark('gadfly2', run_gadfly, RICHARDS_ASCENDING_GOOD,
                        's', check_gadfly),
              Benchmark('mako', run_mako, RICHARDS_ASCENDING_GOOD,
                        's', check_mako),
             ]

BENCHMARKS_BY_NAME = {}
for _b in BENCHMARKS:
    BENCHMARKS_BY_NAME[_b.name] = _b
