import pypy.lang.smalltalk.classtable as ct
from pypy.lang.smalltalk import model

def small_int(i):
    return model.W_SmallInteger(ct.w_SmallInteger, i)

def wrap_float(i):
    return model.W_Float(ct.w_Float,i)

def make_char_table():
    global CharacterTable
    def make_char(i):
        w_cinst = ct.w_Character.new()
        w_cinst.setnamedvar(0, small_int(i))
    CharacterTable = [make_char(i) for i in range(256)]
make_char_table()

def make_string(str):
    w_inst = ct.w_ByteString.new(len(str))
    for i in range(len(str)):
        w_inst.setbyte(i, ord(str[i]))
    return w_inst

def make_char(c):
    return CharacterTable[ord(c)]

def wrap_bool(bool):
    if bool:
        return w_true
    else:
        return w_false

w_true  = ct.w_True.new()
w_false = ct.w_False.new()
w_nil = ct.w_UndefinedObject.new()
w_mone = small_int(-1)
w_zero = small_int(0)
w_one = small_int(1)
w_two = small_int(2)
