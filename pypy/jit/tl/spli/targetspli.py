
""" usage: spli-c code_obj_file [i:int_arg s:s_arg ...]
"""

import sys, autopath, os
from pypy.jit.tl.spli import objects, interpreter, serializer
from pypy.rlib.streamio import open_file_as_stream

space = objects.DumbObjSpace()

def entry_point(argv):
    if len(argv) < 2:
        print __doc__
        os._exit(1)
    args = argv[2:]
    stream = open_file_as_stream(argv[1])
    co = serializer.deserialize(stream.readall(), space)
    frame = interpreter.SPLIFrame(co)
    res = frame.run()
    print res.repr()
    return 0

def target(drver, args):
    return entry_point, None

if __name__ == '__main__':
    entry_point(sys.argv)
