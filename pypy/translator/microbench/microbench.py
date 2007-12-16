#!/usr/bin/env python

"""This script computes the relative performance between python
implementations on a set of microbenchmarks. The script usally is started
with "./microbench.py python ./pypy" where pypy is a symlink to you pypy exectable."""

import os, time, sys, gc

microbenches = []
for fname in os.listdir('.'):
    if not fname.startswith('test_') or not fname.endswith('.py'):
        continue
    microbench = fname[:-3]
    exec 'import ' + microbench
    microbenches.append(microbench)

def run(test_cases):
    MINIMUM_MICROBENCH_TIME = 1.0

    for microbench in microbenches:
        for k in [s for s in globals()[microbench].__dict__ if s.startswith('test_')] :
            if test_cases:
                for tc in test_cases:
                    if k.startswith(tc):
                        break
                else:
                    continue
            testcase_name = microbench + '.' + k + '()'
            testcase = getattr(globals()[microbench], k)
            gc.collect()
            start = time.clock()
            n = 0
            duration = 0.0
            while duration < MINIMUM_MICROBENCH_TIME:
                testcase()
                n += 1
                duration = time.clock() - start
            print '%s took %.2f seconds' % (testcase_name, duration / float(n))

if __name__ == '__main__':
    args = sys.argv[1:]
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
        data = [s for s in os.popen(exe + ' microbench.py %s 2>&1' % limit).readlines() if not s.startswith('debug:')]
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
        run(test_cases)
