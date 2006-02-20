# benchmarks on a unix machine.
# to be executed in the goal folder,
# where a couple of pypy-* files is expected.

import os, sys, time, pickle

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
        try:
            f = open(filename, 'r')
            self.n_results   = pickle.load(f)
            self.best_result = pickle.load(f)
            f.close()
        except:
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
    txt = run_cmd('%s -c "%s"' % (executable, argstr))
    return get_result(txt, PYSTONE_PATTERN)

def run_richards(executable='/usr/local/bin/python', n=10):
    argstr = RICHARDS_CMD % n
    txt = run_cmd('%s -c "%s"' % (executable, argstr))
    return get_result(txt, RICHARDS_PATTERN)

def get_executables():  #sorted by revision number (highest first)
    exes = []
    for exe in [os.path.join('.', name) for name in os.listdir('.') if name.startswith('pypy-')]:
        try:
            exes.append( (exe.split('-',2)[2], exe) )
        except:
            pass    #skip filenames without version number
    exes.sort()
    exes.reverse()
    exes = [s[1] for s in exes]
    return exes

def main():
    benchmark_result = BenchmarkResult('bench-unix.benchmark_result')

    print 'date                       executable                        richards             pystone'
    sys.stdout.flush()

    v = 'python ' + sys.version.split()[0]
    r = v + '_richards'
    if not benchmark_result.is_stable(r):
        benchmark_result.update(r, run_richards(), RICHARDS_ASCENDING_GOOD)
    ref_rich = benchmark_result.get_best_result(r)

    p = v + '_pystone'
    if not benchmark_result.is_stable(p):
        benchmark_result.update(p, run_pystone(), PYSTONE_ASCENDING_GOOD)
    ref_stone = benchmark_result.get_best_result(p)

    fmt = '%-26s %-30s   %6dms (%6.1fx)   %6d (%6.1fx)'
    print fmt % (time.ctime(), v, ref_rich, 1.0, ref_stone, 1.0)
    sys.stdout.flush()

    for exe in get_executables():
        exename = os.path.splitext(exe)[0].lstrip('./')
        ctime   = time.ctime( os.path.getctime(exename) )

        r = exe + '_richards'
        if not benchmark_result.is_stable(r):
            benchmark_result.update(r, run_richards(exe, 1), RICHARDS_ASCENDING_GOOD)
        rich = benchmark_result.get_best_result(r)

        p = exe + '_pystone'
        if not benchmark_result.is_stable(p):
            benchmark_result.update(p, run_pystone(exe), PYSTONE_ASCENDING_GOOD)
        stone = benchmark_result.get_best_result(p)

        print fmt % (ctime, exename, rich, rich / ref_rich, stone, ref_stone / stone)
        sys.stdout.flush()

if __name__ == '__main__':
    main()
