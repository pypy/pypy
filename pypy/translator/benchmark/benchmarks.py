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

def run_cmd(cmd):
    #print "running", cmd
    pipe = os.popen(cmd + ' 2>&1')
    r = pipe.read()
    status = pipe.close()
    if status:
        print "warning: %r had exit status %s"%(cmd, status)
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
    argstr = '%s %s --text --batch --backendopt --no-compile %s > /dev/null 2> /dev/null'
    T = time.time()
    status = os.system(argstr%(executable, translate, target))
    r = time.time() - T
    if status:
        raise BenchmarkFailed(status)
    return r

def run_docutils(executable='/usr/local/bin/python'):
    docutilssvnpathfile = py.magic.autopath().dirpath().join("docutilssvnpath")
    docutilssvnpath = docutilssvnpathfile.read().strip()
    translatetxt = py.magic.autopath().dirpath().dirpath().dirpath().join('doc').join('translation.txt')
    command = """import sys
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
    docutilssvnpathfile = py.magic.autopath().dirpath().join("docutilssvnpath")
    return docutilssvnpathfile.check()

def run_templess(executable='/usr/local/bin/python'):
    """ run some script in the templess package

        templess is some simple templating language, to check out use
        'svn co http://johnnydebris.net/templess/trunk templess'
    """
    here = py.magic.autopath().dirpath()
    pypath = py.__package__.getpath().dirpath()
    templessdir = here.join('templess')
    testscript = templessdir.join('test/oneshot.py')
    command = 'PYTHONPATH="%s:%s" "%s" "%s" 100' % (here, pypath,
                                                    executable, testscript)
    txt = run_cmd(command)
    try:
        result = float([line for line in txt.split('\n') if line.strip()][-1])
    except ValueError:
        raise IOError(txt)
    return result

def check_templess():
    templessdir = py.magic.autopath().dirpath().join('templess')
    return templessdir.check()
    

BENCHMARKS = [Benchmark('richards', run_richards, RICHARDS_ASCENDING_GOOD, 'ms'),
              Benchmark('pystone', run_pystone, PYSTONE_ASCENDING_GOOD, ''),
              Benchmark('translate', run_translate, RICHARDS_ASCENDING_GOOD, 'ms'),
              Benchmark('docutils', run_docutils, RICHARDS_ASCENDING_GOOD,
                        'ms', check_docutils),
              Benchmark('templess', run_templess, RICHARDS_ASCENDING_GOOD,
                        'ms', check_templess),
             ]

BENCHMARKS_BY_NAME = {}
for _b in BENCHMARKS:
    BENCHMARKS_BY_NAME[_b.name] = _b
