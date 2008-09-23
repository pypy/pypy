#!/usr/bin/env python

"""This script computes the relative performance between python
implementations on a set of microbenchmarks. The script usually is started
with "./microbench.py python ./pypy" where pypy is a symlink to your pypy executable."""

import os, time, sys

try:
    import gc
except ImportError:
    if sys.platform.startswith('java'):
        import java.lang
        gccollect = java.lang.System.gc
    else:
        gccollect = lambda: None
else:
    gccollect = gc.collect

try:
    this_dir = os.path.dirname(__file__)
except NameError:
    this_dir = os.path.dirname(sys.argv[0])

microbenches = []
for fname in os.listdir(this_dir):
    if not fname.startswith('test_') or not fname.endswith('.py'):
        continue
    microbench = fname[:-3]
    microbenches.append(microbench)

def run(test_cases, fmt):
    MINIMUM_MICROBENCH_TIME = 1.0

    for microbench in microbenches:
        testmoddict = {}
        execfile(os.path.join(this_dir, microbench + '.py'), testmoddict)
        for k in [s for s in testmoddict if s.startswith('test_')] :
            if test_cases:
                for tc in test_cases:
                    if k.startswith(tc) or microbench.startswith(tc):
                        break
                else:
                    continue
            testcase_name = microbench + '.' + k + '()'
            testcase = testmoddict[k]
            gccollect()
            start = time.clock()
            n = 0
            duration = 0.0
            while duration < MINIMUM_MICROBENCH_TIME:
                testcase()
                n += 1
                duration = time.clock() - start
            print ('%s took ' + fmt +' seconds') % (testcase_name, duration / float(n))

if __name__ == '__main__':
    args = sys.argv[1:]
    if args[0].startswith('-F'):
        fmt = "%" + args[0][2:]
        args.pop(0)
    else:
        fmt = "%.2f"
        
    if '-k' in args:
        i = args.index('-k')
        executables = args[:i]
        test_cases  = args[i+1:]
        limit = '-k ' + ' '.join(test_cases)
    else:
        executables = args
        test_cases  = []
        limit = ''

    for n, exe in enumerate(executables):
        print 'exe:', exe
        data = [s for s in os.popen('%s %s -Fr %s 2>&1' %
            (exe, os.path.join(this_dir, 'microbench.py'), limit)).readlines()
                if not s.startswith('debug:')]
        benchdata = {}
        for d in data:
            try:
                testcase, took, duration, seconds = d.split()
            except ValueError:
                print >> sys.stderr, 'Unexpected output:\n%s' % d
                sys.exit(1)
            benchdata[testcase] = float(duration)
        if n == 0:
            benchdata_ref = benchdata
        else:
            result = []
            for k, v in benchdata.iteritems():
                result.append( (v / benchdata_ref[k], k) )
            result.sort()
            for r in result:
                slowdown, testcase = r
                print '%5.2fx slower on %s' % (slowdown, testcase)
        
    if not executables:
        run(test_cases, fmt)

