import os, sys
from pypy.lang.smalltalk import model, interpreter, primitives, shadow, constants
from pypy.lang.smalltalk.tool.analyseimage import create_squeakimage

# This loads the whole mini.image in advance.  At run-time,
# it executes the tinyBenchmark.  In this way we get an RPython
# "image" frozen into the executable, mmap'ed by the OS from
# there and loaded lazily when needed :-)


# XXX this only compiles if sys.recursionlimit is high enough!
# On non-Linux platforms I don't know if there is enough stack to
# compile...
sys.setrecursionlimit(100000)


def tinyBenchmarks():
    from pypy.lang.smalltalk import objspace
    space = objspace.ObjSpace()
    image = create_squeakimage(space)
    interp = interpreter.Interpreter(space)

    w_object = model.W_SmallInteger(0)

    # Should get this from w_object
    w_smallint_class = image.special(constants.SO_SMALLINTEGER_CLASS)
    s_class = w_object.shadow_of_my_class(space)
    w_method = s_class.lookup("tinyBenchmarks")

    assert w_method
    w_frame = w_method.create_frame(space, w_object, [])
    interp.store_w_active_context(w_frame)

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
