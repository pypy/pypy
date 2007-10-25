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

def test_empty_class():
    w_class = build_smalltalk_class("Empty", 0x2)
    classshadow = w_class.as_class_get_shadow()
    assert classshadow.instance_kind == shadow.POINTERS
    assert not classshadow.isvariable()
    assert classshadow.instsize() == 0
    assert classshadow.name == "Empty"
    assert classshadow.s_superclass is w_Object.as_class_get_shadow()
