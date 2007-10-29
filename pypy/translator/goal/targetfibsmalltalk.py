from pypy.lang.smalltalk import model, interpreter, primitives, shadow
from pypy.lang.smalltalk import objtable
from pypy.lang.smalltalk.utility import wrap_int, unwrap_int
from pypy.lang.smalltalk import classtable
from pypy.lang.smalltalk.test.test_interpreter import *

mockclass = classtable.bootstrap_class

def new_interpreter(bytes):
    assert isinstance(bytes, str)
    w_method = model.W_CompiledMethod(0, bytes=bytes)
    w_frame = w_method.create_frame(objtable.w_nil, [])
    interp = interpreter.Interpreter()
    interp.w_active_context = w_frame
    return interp

def build():
    bytecode = ''.join(map(chr, [ 16, 119, 178, 154, 118, 164, 11, 112, 16, 118, 177, 224, 112, 16, 119, 177, 224, 176, 124 ]))
    shadow = mockclass(0).as_class_get_shadow()
    method = model.W_CompiledMethod(1, bytecode, 1)
    method.literals = fakeliterals("fib:")
    shadow.installmethod("fib:", method)
    w_object = shadow.new()
    interp = new_interpreter(sendLiteralSelectorBytecode(16) + returnTopFromMethod)
    interp.w_active_context.w_method().literals = fakeliterals("fib:")
    return interp, w_object

def check_me():
    interp, w_object = build()
    interp.w_active_context.push(w_object)
    interp.w_active_context.push(wrap_int(8))
    result = interp.interpret()
    assert unwrap_int(result) == 34
    print "check_me() ok"
check_me()


interp, w_object = build()

def entry_point(argv):
    if len(argv) > 1:
        n = int(argv[1])
    else:
        n = 8
    interp.w_active_context.push(w_object)
    interp.w_active_context.push(wrap_int(n))
    result = interp.interpret()
    print unwrap_int(result)
    return 0

# _____ Define and setup target ___

def target(*args):
    return entry_point, None
