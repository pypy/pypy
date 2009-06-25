
""" usage: spli-c code_obj_file [i:int_arg s:s_arg ...]
"""

import sys, autopath, os
from pypy.jit.tl.spli import execution, serializer, objects
from pypy.rlib.streamio import open_file_as_stream


def unwrap_arg(arg):
    if arg.startswith('s:'):
        return objects.Str(arg[2:])
    elif arg.startswith('i:'):
        return objects.Int(int(arg[2:]))
    else:
        raise NotImplementedError

def entry_point(argv):
    if len(argv) < 2:
        print __doc__
        os._exit(1)
    args = argv[2:]
    stream = open_file_as_stream(argv[1])
    co = serializer.deserialize(stream.readall())
    w_args = [unwrap_arg(args[i]) for i in range(len(args))]
    execution.run(co, w_args)
    return 0

def target(drver, args):
    return entry_point, None

def jitpolicy(driver):
    """Returns the JIT policy to use when translating."""
    from pypy.jit.metainterp.policy import JitPolicy
    return JitPolicy()

if __name__ == '__main__':
    entry_point(sys.argv)
