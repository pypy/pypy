import autopath
import sys
from pypy.lang.smalltalk import model, interpreter, primitives, shadow
from pypy.lang.smalltalk import objtable
from pypy.lang.smalltalk.objtable import wrap_int
from pypy.lang.smalltalk import classtable
# from pypy.lang.smalltalk.test.test_interpreter import *
from pypy.lang.smalltalk import squeakimage

mockclass = classtable.bootstrap_class

def new_interpreter(bytes):
    assert isinstance(bytes, str)
    w_method = model.W_CompiledMethod(0, bytes=bytes)
    w_frame = w_method.create_frame(objtable.w_nil, [])
    interp = interpreter.Interpreter()
    interp.w_active_context = w_frame
    return interp

def entry_point(argv):
    if len(argv) > 1:
        filename = argv[1]
    else:
        print "usage:", argv[0], "<image name>"
        return -1
    reader = squeakimage.ImageReader(squeakimage.Stream(DummyFile(filename)))
    reader.initialize()
    image = squeakimage.SqueakImage()
    image.from_reader(reader)
    return 0

# _____ Define and setup target ___

def target(*args):
    return entry_point, None

class DummyFile:
    def __init__(self,filename):
        import os
        fd = os.open(filename, os.O_RDONLY, 0777)
        try:
            content = []
            while 1:
                s = os.read(fd, 4096)
                if not s:
                    break
                content.append(s)
            self.content = "".join(content)
        finally:
            os.close(fd)
    def read(self):
        return self.content
    def close(self):
        pass

if __name__ == "__main__":
    entry_point(sys.argv)
