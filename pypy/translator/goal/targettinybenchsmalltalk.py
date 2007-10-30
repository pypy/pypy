import os
from pypy.lang.smalltalk import model, interpreter, primitives, shadow
from pypy.lang.smalltalk import objtable
from pypy.lang.smalltalk.utility import wrap_int
from pypy.lang.smalltalk import classtable
from pypy.lang.smalltalk.tool.analyseimage import *

# This loads the whole mini.image in advance.  At run-time,
# it executes the tinyBenchmark.  In this way we get an RPython
# "image" frozen into the executable, mmap'ed by the OS from
# there and loaded lazily when needed :-)


# XXX this only compiles if sys.recursionlimit is high enough!
# On non-Linux platforms I don't know if there is enough stack to
# compile...
sys.setrecursionlimit(100000)


def tinyBenchmarks():
    image = create_squeakimage()
    interp = interpreter.Interpreter()

    w_object = model.W_SmallInteger(0)

    # Should get this from w_object
    w_smallint_class = image.special(constants.SO_SMALLINTEGER_CLASS)
    s_class = w_object.shadow_of_my_class()
    w_method = s_class.lookup("tinyBenchmarks")

    assert w_method
    w_frame = w_method.create_frame(w_object, [])
    interp.w_active_context = w_frame

    print w_method
    print "Going to execute %d toplevel bytecodes" % (len(w_method.bytes),)
    counter = 0

    from pypy.lang.smalltalk.interpreter import BYTECODE_TABLE
    return interp


interp = tinyBenchmarks()


def entry_point(argv):
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


# _____ Define and setup target ___

def target(*args):
    return entry_point, None
