import pypy.lang.smalltalk.classtable as ct
from pypy.lang.smalltalk.constants import CHARACTER_VALUE_INDEX
from pypy.lang.smalltalk import model

# ___________________________________________________________________________
# Utility Methods

def wrap_int(i):
    if i <= 0x3FFFFFFF and i >= -0x40000000:
        return model.W_SmallInteger(ct.w_SmallInteger, i)
    raise NotImplementedError

def wrap_float(i):
    return model.W_Float(ct.w_Float,i)

def wrap_string(str):
    w_inst = ct.w_ByteString.new(len(str))
    for i in range(len(str)):
        w_inst.setbyte(i, ord(str[i]))
    return w_inst

def wrap_char(c):
    return CharacterTable[ord(c)]

def ord_w_char(w_c):
    assert w_c.w_class is ct.w_Character
    w_ord = w_c.fetch(CHARACTER_VALUE_INDEX)
    assert w_ord.w_class is ct.w_SmallInteger
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
        w_cinst = ct.w_Character.new()
        w_cinst.store(CHARACTER_VALUE_INDEX, wrap_int(i))
        return w_cinst
    CharacterTable = [bld_char(i) for i in range(256)]
wrap_char_table()

w_true  = ct.w_True.new()
w_false = ct.w_False.new()
w_nil = ct.w_UndefinedObject.new()
w_mone = wrap_int(-1)
w_zero = wrap_int(0)
w_one = wrap_int(1)
w_two = wrap_int(2)
