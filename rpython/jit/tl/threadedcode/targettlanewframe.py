import py
py.path.local(__file__)
import time

from rpython.jit.tl.threadedcode import tla_newframe as tla
from rpython.rlib import jit

def entry_point(args):
    usage = "Usage: %s filename x" % (args[0],)

    if len(args) < 3:
        print usage
        return 2

    for i in range(len(args)):
        if args[i] == "--jit":
            if len(args) == i + 1:
                print "missing argument after --jit"
                return 2
            jitarg = args[i + 1]
            del args[i:i+2]
            jit.set_user_param(None, jitarg)
            break

    filename = args[1]
    x = int(args[2])
    w_x = tla.W_IntObject(x)
    bytecode = load_bytecode(filename)
    w_res = tla.run(bytecode, w_x)
    print w_res.getrepr()
    return 0

def load_bytecode(filename):
    from rpython.rlib.streamio import open_file_as_stream
    f = open_file_as_stream(filename)
    bytecode = f.readall()
    f.close()
    return bytecode

def target(driver, args):
    return entry_point

# ____________________________________________________________


if __name__ == '__main__':
    import sys
    sys.exit(entry_point(sys.argv))
