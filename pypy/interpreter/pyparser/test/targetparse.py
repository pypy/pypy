import sys
import os
ROOT =  os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
print ROOT
sys.path.insert(0, str(ROOT))
import time
from pypy.interpreter.pyparser import pyparse



with file("../../../rpython/rlib/unicodedata/unicodedb_5_2_0.py") as f:
    s = f.read()

class FakeSpace(object):
    pass

fakespace = FakeSpace()

def bench(title):
    a = time.clock()
    info = pyparse.CompileInfo("<string>", "exec")
    parser = pyparse.PythonParser(fakespace)
    tree = parser._parse(s, info)
    b = time.clock()
    print title, (b-a)


def entry_point(argv):
    bench("foo")

    return 0

# _____ Define and setup target ___

def target(*args):
    return entry_point, None

if __name__ == '__main__':
    entry_point(sys.argv)
