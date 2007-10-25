from pypy.lang.smalltalk import model, shadow, classtable, constants, objtable

w_Object = classtable.classtable['w_Object']
w_Metaclass  = classtable.classtable['w_Metaclass']

def build_smalltalk_class(name, format, w_superclass=w_Object,
                          w_classofclass=None):
    if w_classofclass is None:
        w_classofclass = build_smalltalk_class(None, 0x94,
                                               w_superclass.w_class,
                                               w_Metaclass)
    size = constants.CLASS_NAME_INDEX + 1
    w_class = model.W_PointersObject(w_classofclass, size)
    w_class.store(constants.CLASS_SUPERCLASS_INDEX, w_superclass)
    #w_class.store(constants.CLASS_METHODDICT_INDEX, ...)
    w_class.store(constants.CLASS_FORMAT_INDEX, objtable.wrap_int(format))
    if name is not None:
        w_class.store(constants.CLASS_NAME_INDEX, objtable.wrap_string(name))
    return w_class

def basicshape(name, format, kind, varsized, instsize):
    w_class = build_smalltalk_class(name, format)
    classshadow = w_class.as_class_get_shadow()
    assert classshadow.instance_kind == kind
    assert classshadow.isvariable() == varsized
    assert classshadow.instsize() == instsize
    assert classshadow.name == name
    assert classshadow.s_superclass is w_Object.as_class_get_shadow()

def test_basic_shape():
    yield basicshape, "Empty",        0x02,    shadow.POINTERS, False, 0
    yield basicshape, "Seven",        0x90,    shadow.POINTERS, False, 7
    yield basicshape, "Seventyseven", 0x1009C, shadow.POINTERS, False, 77
    yield basicshape, "EmptyVar",     0x102,   shadow.POINTERS, True,  0
    yield basicshape, "VarSeven",     0x190,   shadow.POINTERS, True,  7
    yield basicshape, "Bytes",        0x402,   shadow.BYTES,    True,  0
    yield basicshape, "Words",        0x302,   shadow.WORDS,    True,  0
    yield basicshape, "CompiledMeth", 0xE02,   shadow.COMPILED_METHOD, True, 0
