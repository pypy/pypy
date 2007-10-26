import pypy.lang.smalltalk.classtable as ct
from pypy.lang.smalltalk import constants
from pypy.lang.smalltalk import model

# ___________________________________________________________________________
# Utility Methods

def wrap_int(i):
    if i <= 0x3FFFFFFF and i >= -0x40000000:
        return model.W_SmallInteger(i)
    raise NotImplementedError

def wrap_float(i):
    return model.W_Float(i)

def wrap_string(str):
    w_inst = ct.w_String.as_class_get_shadow().new(len(str))
    for i in range(len(str)):
        w_inst.setbyte(i, ord(str[i]))
    return w_inst

def wrap_char(c):
    return CharacterTable[ord(c)]

def ord_w_char(w_c):
    assert w_c.getclass() is ct.w_Character
    w_ord = w_c.fetch(constants.CHARACTER_VALUE_INDEX)
    assert w_ord.getclass() is ct.w_SmallInteger
    assert isinstance(w_ord, model.W_SmallInteger)
    return w_ord.value

def wrap_bool(bool):
    if bool:
        return w_true
    else:
        return w_false

# ___________________________________________________________________________
# Global Data

def wrap_char_table():
    global CharacterTable
    def bld_char(i):
        w_cinst = ct.w_Character.as_class_get_shadow().new()
        w_cinst.store(constants.CHARACTER_VALUE_INDEX, wrap_int(i))
        return w_cinst
    CharacterTable = [bld_char(i) for i in range(256)]
wrap_char_table()

w_true  = ct.classtable['w_True'].as_class_get_shadow().new()
w_false = ct.classtable['w_False'].as_class_get_shadow().new()
w_mone = wrap_int(-1)
w_zero = wrap_int(0)
w_one = wrap_int(1)
w_two = wrap_int(2)

# Very special nil hack: in order to allow W_PointersObject's to
# initialize their fields to nil, we have to create it in the model
# package, and then patch up its fields here:
w_nil = model.w_nil
w_nil.w_class = ct.classtable['w_UndefinedObject']

objtable = {}

for name in constants.objects_in_special_object_table:
    objtable["w_" + name] = globals()["w_" + name]
