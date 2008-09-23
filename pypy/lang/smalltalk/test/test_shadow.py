import random
from pypy.lang.smalltalk import model, shadow, constants
from pypy.lang.smalltalk import objspace

space = objspace.ObjSpace()

w_Object = space.classtable['w_Object']
w_Metaclass  = space.classtable['w_Metaclass']
w_MethodDict = space.classtable['w_MethodDict']
w_Array      = space.classtable['w_Array']

def build_methoddict(methods):
    size = int(len(methods) * 1.5)
    w_methoddict = w_MethodDict.as_class_get_shadow(space).new(size)
    w_array = w_Array.as_class_get_shadow(space).new(size)
    for i in range(size):
        w_array.store(space, i, space.w_nil)
        w_methoddict.store(space, constants.METHODDICT_NAMES_INDEX+i, space.w_nil)
    w_tally = space.wrap_int(len(methods))
    w_methoddict.store(space, constants.METHODDICT_TALLY_INDEX, w_tally)
    w_methoddict.store(space, constants.METHODDICT_VALUES_INDEX, w_array)
    positions = range(size)
    random.shuffle(positions)
    for selector, w_compiledmethod in methods.items():
        pos = positions.pop()
        w_selector = space.wrap_string(selector)
        w_methoddict.store(space, constants.METHODDICT_NAMES_INDEX+pos, w_selector)
        w_array.store(space, pos, w_compiledmethod)
    return w_methoddict

def build_smalltalk_class(name, format, w_superclass=w_Object,
                          w_classofclass=None, methods={}):
    if w_classofclass is None:
        w_classofclass = build_smalltalk_class(None, 0x94,
                                               w_superclass.w_class,
                                               w_Metaclass)
    w_methoddict = build_methoddict(methods)
    size = constants.CLASS_NAME_INDEX + 1
    w_class = model.W_PointersObject(w_classofclass, size)
    w_class.store(space, constants.CLASS_SUPERCLASS_INDEX, w_superclass)
    w_class.store(space, constants.CLASS_METHODDICT_INDEX, w_methoddict)
    w_class.store(space, constants.CLASS_FORMAT_INDEX, space.wrap_int(format))
    if name is not None:
        w_class.store(space, constants.CLASS_NAME_INDEX, space.wrap_string(name))
    return w_class

def basicshape(name, format, kind, varsized, instsize):
    w_class = build_smalltalk_class(name, format)
    classshadow = w_class.as_class_get_shadow(space)
    assert classshadow.instance_kind == kind
    assert classshadow.isvariable() == varsized
    assert classshadow.instsize() == instsize
    assert classshadow.name == name
    assert classshadow.s_superclass() is w_Object.as_class_get_shadow(space)

def test_basic_shape():
    yield basicshape, "Empty",        0x02,    shadow.POINTERS, False, 0
    yield basicshape, "Seven",        0x90,    shadow.POINTERS, False, 7
    yield basicshape, "Seventyseven", 0x1009C, shadow.POINTERS, False, 77
    yield basicshape, "EmptyVar",     0x102,   shadow.POINTERS, True,  0
    yield basicshape, "VarTwo",       0x3986,  shadow.POINTERS, True,  2
    yield basicshape, "VarSeven",     0x190,   shadow.POINTERS, True,  7
    yield basicshape, "Bytes",        0x402,   shadow.BYTES,    True,  0
    yield basicshape, "Words",        0x302,   shadow.WORDS,    True,  0
    yield basicshape, "CompiledMeth", 0xE02,   shadow.COMPILED_METHOD, True, 0

def test_methoddict():
    methods = {'foo': model.W_CompiledMethod(0),
               'bar': model.W_CompiledMethod(0)}
    w_class = build_smalltalk_class("Demo", 0x90, methods=methods)
    classshadow = w_class.as_class_get_shadow(space)
    assert classshadow.s_methoddict().methoddict == methods

def method(tempsize=3,argsize=2, bytes="abcde"):
    w_m = model.W_CompiledMethod()
    w_m.bytes = bytes
    w_m.tempsize = tempsize
    w_m.argsize = argsize
    w_m.literalsize = 2
    return w_m

def methodcontext(w_sender=space.w_nil, pc=1, stackpointer=0, stacksize=5,
                  method=method()):
    w_object = model.W_PointersObject(space.w_MethodContext, constants.MTHDCTX_TEMP_FRAME_START+method.tempsize+stacksize)
    w_object.store(space, constants.CTXPART_SENDER_INDEX, w_sender)
    w_object.store(space, constants.CTXPART_PC_INDEX, space.wrap_int(pc))
    w_object.store(space, constants.CTXPART_STACKP_INDEX, space.wrap_int(method.tempsize+stackpointer))
    w_object.store(space, constants.MTHDCTX_METHOD, method)
    # XXX
    w_object.store(space, constants.MTHDCTX_RECEIVER_MAP, '???')
    w_object.store(space, constants.MTHDCTX_RECEIVER, 'receiver')

    w_object.store(space, constants.MTHDCTX_TEMP_FRAME_START, 'el')
    return w_object

def blockcontext(w_sender=space.w_nil, pc=1, stackpointer=1, stacksize=5,
                  home=methodcontext()):
    w_object = model.W_PointersObject(space.w_MethodContext, constants.MTHDCTX_TEMP_FRAME_START+stacksize)
    w_object.store(space, constants.CTXPART_SENDER_INDEX, w_sender)
    w_object.store(space, constants.CTXPART_PC_INDEX, space.wrap_int(pc))
    w_object.store(space, constants.CTXPART_STACKP_INDEX, space.wrap_int(stackpointer))
    w_object.store(space, constants.BLKCTX_BLOCK_ARGUMENT_COUNT_INDEX, space.wrap_int(54))
    w_object.store(space, constants.BLKCTX_INITIAL_IP_INDEX, space.wrap_int(17))
    w_object.store(space, constants.BLKCTX_HOME_INDEX, home)
    w_object.store(space, constants.BLKCTX_STACK_START, 'el')
    return w_object

def test_context():
    w_m = method()
    w_object = methodcontext(stackpointer=3, method=w_m)
    w_object2 = methodcontext(w_sender=w_object)
    s_object = w_object.as_methodcontext_get_shadow(space)
    assert len(s_object.stack()) == 3
    s_object2 = w_object2.as_methodcontext_get_shadow(space)
    assert w_object2.fetch(space, constants.CTXPART_SENDER_INDEX) == w_object
    assert s_object.w_self() == w_object
    assert s_object2.w_self() == w_object2
    assert s_object.s_sender() == None
    assert s_object2.s_sender() == s_object
    assert s_object.w_receiver() == 'receiver'
    s_object2.settemp(0, 'a')
    s_object2.settemp(1, 'b')
    assert s_object2.gettemp(1) == 'b'
    assert s_object2.gettemp(0) == 'a'
    assert s_object.w_method() == w_m
    idx = s_object.stackstart()
    w_object.store(space, idx, 'f')
    w_object.store(space, idx + 1, 'g')
    w_object.store(space, idx + 2, 'h')
    assert s_object.stack() == ['f', 'g', 'h' ]
    assert s_object.top() == 'h'
    s_object.push('i')
    assert s_object.top() == 'i'
    assert s_object.peek(1) == 'h'
    assert s_object.pop() == 'i'
    assert s_object.pop_and_return_n(2) == ['g', 'h']
    assert s_object.pop() == 'f'
    assert s_object.external_stackpointer() == s_object.stackstart()

def test_methodcontext():
    w_m = method()
                              # Point over 2 literals of size 4
    w_object = methodcontext(pc=13,method=w_m)
    s_object = w_object.as_methodcontext_get_shadow(space)
    assert s_object.getbytecode() == 97
    assert s_object.getbytecode() == 98
    assert s_object.getbytecode() == 99
    assert s_object.getbytecode() == 100
    assert s_object.getbytecode() == 101
    assert s_object.s_home() == s_object

def test_attach_detach_mc():
    w_m = method()
    w_object = methodcontext(pc=13, method=w_m)
    old_vars = w_object._vars
    s_object = w_object.as_methodcontext_get_shadow(space)
    assert w_object._vars is None
    s_object.detach_shadow()
    assert w_object._vars == old_vars
    assert w_object._vars is not old_vars

def test_attach_detach_bc():
    w_object = blockcontext(pc=13)
    old_vars = w_object._vars
    s_object = w_object.as_blockcontext_get_shadow(space)
    assert w_object._vars is None
    s_object.detach_shadow()
    assert w_object._vars == old_vars
    assert w_object._vars is not old_vars

def test_replace_to_bc():
    w_object = blockcontext(pc=13)
    old_vars = w_object._vars
    s_object = w_object.as_blockcontext_get_shadow(space)
    s_object.detach_shadow()
    s_classshadow = shadow.ClassShadow(space, w_object)
    w_object._shadow = s_classshadow
    s_classshadow.invalid = False
    s_newobject = w_object.as_blockcontext_get_shadow(space)
    assert s_classshadow.invalid
    assert ([s_newobject.fetch(i) for i in range(s_newobject.size())] ==
            [s_object.fetch(i) for i in range(s_newobject.size())])
    assert w_object._shadow is s_newobject
