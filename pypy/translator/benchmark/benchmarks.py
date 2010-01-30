import os, sys, time, pickle, re, py
import yaml

class BenchmarkFailed(Exception):
    pass

PYSTONE_CMD = 'from test import pystone;pystone.main(%s)'
PYSTONE_PATTERN = 'This machine benchmarks at'

RICHARDS_CMD = 'from richards import *;main(iterations=%d)'
RICHARDS_PATTERN = 'Average time per iteration:'

TIME_FMT = 'max mem used: %Mk\nelapsed time: %e\nsystem time:  %S\nuser time:    %U\nCPU use:      %P'

def get_result(txt, pattern):
    for line in txt.split('\n'):
        if line.startswith(pattern):
            break
    else:
        raise BenchmarkFailed
    return float(line.split()[len(pattern.split())])

class Benchmark(object):
    def __init__(self, name, runner, asc_good, units,
                 check=lambda:True, sizefactor=1):
        if sizefactor > 1:
            self.name = name + '*%d' % sizefactor
        else:
            self.name = name
        self._basename = name
        self._run = runner
        self.asc_good = asc_good
        self.units = units
        self.check = check
        self.sizefactor = sizefactor
    def __mul__(self, n):
        return Benchmark(self._basename, self._run, self.asc_good, self.units,
                         self.check, self.sizefactor * n)
    def run(self, exe):
        self.latest_output = ''
        try:
            result, latest_output = self._run(exe, self.sizefactor)
            self.latest_output = latest_output
        except BenchmarkFailed, e:
            result = '-FAILED-'
        return result

def external_dependency(dirname, svnurl, revision=None):
    directory = py.path.local(__file__).dirpath().join(dirname)
    wc = py.path.svnwc(directory)
    wc.checkout(svnurl, rev=revision)
    return True

def run_cmd(cmd):
    pipe = os.popen(cmd + ' 2>&1')
    r = pipe.read()
    status = pipe.close()
    if status:
        raise BenchmarkFailed(status)
    return r

def run_pystone(executable, sizefactor=1):
    from pypy.tool import autopath
    distdir = py.path.local(autopath.pypydir).dirpath()
    pystone = py.path.local(autopath.libpythondir).join('test', 'pystone.py')
    txt = run_cmd('"%s" "%s" %d' % (executable, pystone, 50000 * sizefactor))
    return get_result(txt, PYSTONE_PATTERN), txt

def run_richards(executable, sizefactor=1):
    richards = py.path.local(__file__).dirpath().dirpath().join('goal').join('richards.py')
    txt = run_cmd('"%s" %s %d' % (executable, richards, 5 * sizefactor))
    return get_result(txt, RICHARDS_PATTERN), txt

def run_translate(executable):
    translate = py.path.local(__file__).dirpath().dirpath().join('goal').join('translate.py')
    target = py.path.local(__file__).dirpath().dirpath().join('goal').join('targetrpystonedalone.py')
    argstr = '%s %s --batch --backendopt --no-compile %s > /dev/null 2> /dev/null'
    T = time.time()
    status = os.system(argstr%(executable, translate, target))
    r = time.time() - T
    if status:
        raise BenchmarkFailed(status)
    return r

def run_templess(executable, sizefactor=1):
    """ run some script in the templess package

        templess is some simple templating language, to check out use
        'svn co -r100 http://johnnydebris.net/templess/trunk templess'
    """
    here = py.path.local(__file__).dirpath()
    pypath = os.path.dirname(os.path.dirname(py.__file__))
    templessdir = here.join('templess')
    testscript = templessdir.join('test/oneshot.py')
    command = 'PYTHONPATH="%s:%s" "%s" "%s" %d' % (here, pypath,
                                                   executable, testscript,
                                                   100 * sizefactor)
    txt = run_cmd(command)
    for line in txt.split('\n'):
        if '.' in line:
            try:
                return float(line) / sizefactor, txt
            except ValueError:
                pass
    else:
        raise BenchmarkFailed

def check_templess():
    return external_dependency('templess',
                               'http://johnnydebris.net/templess/trunk',
                               100)

def run_gadfly(executable, sizefactor=1):
    """ run some tests in the gadfly pure Python database """
    here = py.path.local(__file__).dirpath()
    gadfly = here.join('gadfly')
    testscript = gadfly.join('test', 'testsubset.py')
    command = 'PYTHONPATH="%s" "%s" "%s" %d' % (gadfly, executable, testscript,
                                                sizefactor)
    txt = run_cmd(command)
    return get_result(txt, 'Total running time:') / sizefactor, txt

def check_gadfly():
    return external_dependency('gadfly',
              'http://codespeak.net/svn/user/arigo/hack/pypy-hack/gadflyZip',
              70117)

def run_mako(executable, sizefactor=1):
    """ run some tests in the mako templating system """
    here = py.path.local(__file__).dirpath()
    mako = here.join('mako')
    testscript = mako.join('examples', 'bench', 'basic.py')
    command = 'PYTHONPATH="%s" "%s" "%s" -n%d mako' % (mako.join('lib'),
                                                       executable, testscript,
                                                       2000 * sizefactor)
    txt = run_cmd(command)
    return get_result(txt, 'Mako:'), txt

def check_mako():
    return external_dependency('mako',
              'http://codespeak.net/svn/user/arigo/hack/pypy-hack/mako',
              70118)    

def check_translate():
    return False   # XXX what should we do about the dependency on ctypes?

class LanguageShootoutBenchmark(Benchmark):
    def __init__(self, name, sizefactor=1, test=False):
        self.test = test
        self.basename = name
        Benchmark.__init__(self, name, self.runner, False, 'ms',
                           self.check, sizefactor)

    def __mul__(self, i):
        return LanguageShootoutBenchmark(self.name, self.sizefactor * i,
                                         self.test)

    def runner(self, executable, sizefactor=1):
        shootout = py.path.local(__file__).dirpath().join(
            'shootout_benchmarks')
        argsfile = shootout.join('tests.yml')
        if self.test:
            kind = 'test'
        else:
            kind = 'run'
        args = yaml.load(argsfile.read())[self.basename][kind]['args']
        progname = str(shootout.join(self.basename)) + '.py'
        cmd = 'time -f "%s" %s %s %s %d' % (TIME_FMT, executable, progname,
                                         " ".join(args), sizefactor)
        txt = run_cmd(cmd)
        return get_result(txt, 'elapsed time:'), txt

    def check(self):
        return external_dependency('shootout_benchmarks',
              'http://codespeak.net/svn/pypy/benchmarks/shootout')

BENCHMARKS = [Benchmark('richards', run_richards, False, 'ms'),
              Benchmark('pystone', run_pystone, True, ''),
              Benchmark('translate', run_translate, False, 'ms',
                        check_translate),
              Benchmark('templess', run_templess, False,
                        's', check_templess),
              Benchmark('gadfly2', run_gadfly, False,
                        's', check_gadfly),
              Benchmark('mako', run_mako, False,
                        's', check_mako),
             ]

SHOOTOUT_NAMES = ['binary-trees', 'fannkuch', 'fasta', 'float',
                  'meteor-contest', 'nbody', 'spectral-norm']

#for name in SHOOTOUT_NAMES:
#    BENCHMARKS.append(LanguageShootoutBenchmark(name))

BENCHMARKS_BY_NAME = {}
for _b in BENCHMARKS:
    BENCHMARKS_BY_NAME[_b.name] = _b
