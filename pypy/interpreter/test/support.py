import sys, os

opd = os.path.dirname

testdir   = opd(os.path.abspath(__file__))
parentdir = opd(testdir)
rootdir   = opd(parentdir)

sys.path.insert(0, opd(rootdir))
