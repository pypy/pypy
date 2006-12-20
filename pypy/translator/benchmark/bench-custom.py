# benchmarks on a unix machine.
# to be executed in the goal folder,
# where a couple of pypy-* files is expected.

import os, sys, time, pickle, re

PYSTONE_CMD = 'from test import pystone;pystone.main(%s)'
PYSTONE_PATTERN = 'This machine benchmarks at'
PYSTONE_ASCENDING_GOOD = True

RICHARDS_CMD = 'from richards import *;main(iterations=%d)'
RICHARDS_PATTERN = 'Average time per iteration:'
RICHARDS_ASCENDING_GOOD = False

class BenchmarkResult(object):

    def __init__(self, filename, max_results=10):
        self.filename    = filename
        self.max_results = max_results
        if os.path.exists(filename):
            f = open(filename, 'r')
            self.n_results   = pickle.load(f)
            self.best_result = pickle.load(f)
            f.close()
            # any exception while loading the file is best reported
            # as a crash, instead of as a silent loss of all the
            # data :-/
        else:
            self.n_results   = {}
            self.best_result = {}

    def is_stable(self, name):
        try:
            return self.n_results[name] >= self.max_results
        except:
            return False

    def update(self, name, result, ascending_good):
        try:
            if ascending_good:
                self.best_result[name] = max(self.best_result[name], result)
            else:
                self.best_result[name] = min(self.best_result[name], result)
        except KeyError:
            self.n_results[name] = 0
            self.best_result[name] = result
        self.n_results[name] += 1

        f = open(self.filename, 'w')
        pickle.dump(self.n_results  , f)
        pickle.dump(self.best_result, f)
        f.close()

    def get_best_result(self, name):
        return self.best_result[name]


def get_result(txt, pattern):
    for line in txt.split('\n'):
        if line.startswith(pattern):
            break
    else:
        print 'warning: this is no valid output'
        return 99999.0
    return float(line.split()[len(pattern.split())])

def run_cmd(cmd):
    #print "running", cmd
    pipe = os.popen(cmd + ' 2>&1')
    return pipe.read()

def run_pystone(executable='/usr/local/bin/python', n=0):
    argstr = PYSTONE_CMD % (str(n) and n or '')
    txt = run_cmd('"%s" -c "%s"' % (executable, argstr))
    return get_result(txt, PYSTONE_PATTERN)

def run_richards(executable='/usr/local/bin/python', n=5):
    argstr = RICHARDS_CMD % n
    txt = run_cmd('"%s" -c "%s"' % (executable, argstr))
    return get_result(txt, RICHARDS_PATTERN)

def run_translate(executable='/usr/local/bin/python'):
    argstr = 'sh -c "time %s translate.py --text --batch --backendopt --no-compile targetrpystonedalone.py > /dev/null 2>/dev/null" 2>&1 | grep real'
    txt = run_cmd(argstr%executable)
    m = re.match('real\s+(?P<mins>\\d+)m(?P<secs>\\d+\\.\\d+)s', txt)
    if not m:
       print repr(txt)
       print 'ow'
       return 99999.0
    return 1000*(float(m.group('mins'))*60 + float(m.group('secs')))

BENCHMARKS = [('richards', run_richards, RICHARDS_ASCENDING_GOOD, 'ms'),
              ('pystone', run_pystone, PYSTONE_ASCENDING_GOOD, ''),
              ('translate', run_translate, RICHARDS_ASCENDING_GOOD, 'ms'),
             ]

def get_executables():  #sorted by revision number (highest first)
    return sorted(sys.argv[1:], key=os.path.getmtime)

def main():
    benchmark_result = BenchmarkResult('bench-custom.benchmark_result')

    ref_rich, ref_stone = None, None

    exes = get_executables()
    pythons = 'python2.4 python2.3'.split()
    width = max(map(len, exes+pythons+['executable'])) + 3

    print 'date                           size codesize    %-*s'%(width, 'executable'),
    for name, run, ascgood, units in BENCHMARKS:
        print '    %-*s'%(6+len(units)+2+8+2-4, name),
    print
    sys.stdout.flush()

    refs = {}

    for exe in pythons+exes:
        exe_ = exe
        if exe in pythons:
            size = codesize = '-'
            ctime = time.ctime()
        else:
            size = os.path.getsize(exe)
            codesize = os.popen('size "%s" | tail -n1 | cut -f1'%(exe,)).read().strip()
            ctime = time.ctime(os.path.getmtime(exe))
            if '/' not in exe:
                exe_ = './' + exe
        print '%-26s %8s %8s    %-*s'%(ctime, size, codesize, width, exe),
        sys.stdout.flush()
        for name, run, ascgood, units in BENCHMARKS:
            n = exe + '_' + name
            if not benchmark_result.is_stable(n):
                benchmark_result.update(n, run(exe_), ascgood)
            res = benchmark_result.get_best_result(n)
            if name not in refs:
                refs[name] = res
            factor = res/refs[name]
            if ascgood:
                factor = 1/factor
            print "%6d%s (%6.1fx)"%(res, units, factor),
            sys.stdout.flush()
        print

        sys.stdout.flush()

if __name__ == '__main__':
    main()
