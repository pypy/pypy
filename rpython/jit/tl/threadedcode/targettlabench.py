import py
py.path.local(__file__)
from rpython.jit.tl.threadedcode import tla
from rpython.rlib import jit
from time import time

def entry_point(args):
    usage = "Usage: %s filename x [-n <iter>] [-w <warmup iter>] [--jit <jitargs>] [--init (baseline|tracing)]" % (args[0],)

    iteration = 100
    warmup = 0
    init = "baseline"
    interp = tla.run

    for i in range(len(args)):
        if args[i] == "--jit":
            if len(args) == i + 1:
                print "missing argument after --jit"
                return 2
            jitarg = args[i + 1]
            del args[i:i+2]
            jit.set_user_param(None, jitarg)
            break

    for i in range(len(args)):
        if args[i] == "-n":
            if len(args) == i + 1:
                print "missing argument after -n"
                return 2
            iteration = int(args[i + 1])
            del args[i:i+2]
            break

    for i in range(len(args)):
        if args[i] == "-w":
            if len(args) == i + 1:
                print "missing argument after -w"
                return 2
            warmup = int(args[i + 1])
            del args[i:i+2]
            break

    for i in range(len(args)):
        if args[i] == "--init":
            if len(args) == i + 1:
                print "missing argument after --init"
                return 2
            init = args[i + 1]
            del args[i:i+2]
            break

    if len(args) < 3:
        print usage
        return 2

    filename = args[1]
    x = int(args[2])

    w_x = tla.W_IntObject(x)
    bytecode = load_bytecode(filename)
    times = []

    entry = None
    if init == "tracing":
        entry = "tracing"

    for i in range(warmup):
        w_res = interp(bytecode, w_x, entry)

    for i in range(iteration):
        s = time()
        w_res = interp(bytecode, w_x, entry)
        e = time()
        times.append(e - s)

    for t in times:
        print t
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
