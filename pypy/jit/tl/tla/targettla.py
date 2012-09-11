import py
py.path.local(__file__)
from pypy.jit.tl.tla import tla


def entry_point(args):
    """Main entry point of the stand-alone executable:
    takes a list of strings and returns the exit code.
    """
    if len(args) < 3:
        print "Usage: %s filename x" % (args[0],)
        return 2
    filename = args[1]
    x = int(args[2])
    w_x = tla.W_IntObject(x)
    bytecode = load_bytecode(filename)
    w_res = tla.run(bytecode, w_x)
    print w_res.getrepr()
    return 0

def load_bytecode(filename):
    from pypy.rlib.streamio import open_file_as_stream
    f = open_file_as_stream(filename)
    bytecode = f.readall()
    f.close()
    return bytecode

def target(driver, args):
    return entry_point, None

def jitpolicy(driver):
    from pypy.jit.codewriter.policy import JitPolicy
    return JitPolicy()
# ____________________________________________________________


if __name__ == '__main__':
    import sys
    sys.exit(entry_point(sys.argv))
