import autopath
import sys
import os
from pypy.lang.smalltalk import model, interpreter, primitives, shadow
from pypy.lang.smalltalk import objtable
from pypy.lang.smalltalk import classtable
# from pypy.lang.smalltalk.test.test_interpreter import *
from pypy.lang.smalltalk import squeakimage
from pypy.lang.smalltalk import constants

mockclass = classtable.bootstrap_class

def tinyBenchmarks(image):
    interp = interpreter.Interpreter()

    w_object = model.W_SmallInteger(0)

    # Should get this from w_object
    s_class = w_object.shadow_of_my_class()
    w_method = s_class.lookup("tinyBenchmarks")

    assert w_method
    w_frame = w_method.create_frame(w_object, [])
    interp.store_w_active_context(w_frame)

    counter = 0

    from pypy.lang.smalltalk.interpreter import BYTECODE_TABLE
    return interp


def run_benchmarks(interp):
    counter = 0
    try:
        while True:
            counter += 1
            interp.step()
            if counter == 100000:
                counter = 0
                os.write(2, '#')
    except interpreter.ReturnFromTopLevel, e:
        w_result = e.object

    assert isinstance(w_result, model.W_BytesObject)
    print w_result.as_string()
    return 0

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
    interp = tinyBenchmarks(image)
    run_benchmarks(interp)
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
