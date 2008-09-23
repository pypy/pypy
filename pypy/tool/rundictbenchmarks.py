import sys, os

# this file runs some benchmarks with a pypy-c that is assumed to be
# built using the MeasuringDictImplementation.

# it should be run with pypy/translator/goal as the cwd, and you'll
# need to hack a copy of rst2html for yourself (svn docutils
# required).

try:
    os.unlink("dictinfo.txt")
except os.error:
    pass

progs = [('pystone', ['-c', 'from test import pystone; pystone.main()']),
         ('richards', ['richards.py']),
         ('docutils', ['rst2html.py', '../../doc/coding-guide.txt', 'foo.html']),
         ('translate', ['translate.py', '--backendopt', '--no-compile', '--batch',
                        'targetrpystonedalone.py'])
         ]

EXE = sys.argv[1]

for suffix, args in progs:
    os.spawnv(os.P_WAIT, EXE, [EXE] + args)
    os.rename('dictinfo.txt', 'dictinfo-%s.txt'%suffix)
