import sys, os

dirname = os.path.dirname

testdir   = dirname(os.path.abspath(__file__))
parentdir = dirname(testdir)
rootdir   = dirname(parentdir)

del dirname

sys.path.insert(0, rootdir)

# rootdir should probably be one level up, since then you
# could really import pypy.appsapce... and not just from
# appspace... 
