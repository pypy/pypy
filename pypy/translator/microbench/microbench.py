#!/usr/bin/python

"""This script computes the relative performance between python
implementations on a set of microbenchmarks. The script usally is started
with "./microbench.py python ./pypy" where pypy is a symlink to you pypy exectable."""

import os, time, sys

microbenches = []
for fname in os.listdir('.'):
    if not fname.startswith('test_') or not fname.endswith('.py'):
        continue
    microbench = fname[:-3]
    exec 'import ' + microbench
    microbenches.append(microbench)

def run():
    MINIMUM_MICROBENCH_TIME = 1.0

    for microbench in microbenches:
        for k in [s for s in globals()[microbench].__dict__ if s.startswith('test_')] :
            testcase = microbench + '.' + k + '()'
            start = time.clock()
            n = 0
            duration = 0.0
            while duration < MINIMUM_MICROBENCH_TIME:
                exec testcase
                n += 1
                duration = time.clock() - start
            print '%s took %.2f seconds' % (testcase, duration / float(n))

if __name__ == '__main__':
    for n, exe in enumerate(sys.argv[1:]):
        print 'exe:', exe
        data = [s for s in os.popen(exe + ' microbench.py 2>&1').readlines() if not s.startswith('debug:')]
        benchdata = {}
        for d in data:
            testcase, took, duration, seconds = d.split()
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
        
    if len(sys.argv) == 1:
        run()
