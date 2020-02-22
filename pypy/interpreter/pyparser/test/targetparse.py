import sys
import os
ROOT =  os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
print ROOT
sys.path.insert(0, str(ROOT))
import time
from pypy.interpreter.pyparser import pyparse



class FakeSpace(object):
    pass

fakespace = FakeSpace()

def bench(fn, s):
    a = time.clock()
    info = pyparse.CompileInfo("<string>", "exec")
    parser = pyparse.PythonParser(fakespace)
    tree = parser._parse(s, info)
    b = time.clock()
    print fn, (b-a)


def entry_point(argv):
    if len(argv) == 2:
        fn = argv[1]
    else:
        fn = "../../../../rpython/rlib/unicodedata/unicodedb_5_2_0.py"
    fd = os.open(fn, os.O_RDONLY, 0777)
    res = []
    while True:
        s = os.read(fd, 4096)
        if not s:
            break
        res.append(s)
    os.close(fd)
    s = "".join(res)
    print len(s)
    bench(fn, s)

    return 0

# _____ Define and setup target ___

def target(*args):
    return entry_point, None

if __name__ == '__main__':
    entry_point(sys.argv)
