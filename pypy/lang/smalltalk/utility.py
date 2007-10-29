from pypy.lang.smalltalk.error import UnwrappingError, WrappingError
from pypy.lang.smalltalk import model


# ____________________________________________________________ 
# unwrapping utilities

def unwrap_int(w_value):
    if isinstance(w_value, model.W_SmallInteger):
        return w_value.value
    raise UnwrappingError("expected a W_SmallInteger, got %s" % (w_value,))

def unwrap_char(w_char):
    from pypy.lang.smalltalk import classtable, objtable, constants
    w_class = w_char.getclass()
    if w_class is not classtable.w_Character:
        raise UnwrappingError("expected character, got %s" % (w_class, ))
    w_ord = w_char.fetch(constants.CHARACTER_VALUE_INDEX)
    w_class = w_ord.getclass()
    if w_class is not classtable.w_SmallInteger:
        raise UnwrappingError("expected smallint from character, got %s" % (w_class, ))

    assert isinstance(w_ord, model.W_SmallInteger)
    return chr(w_ord.value)

# ____________________________________________________________ 
# wrapping utilities

def wrap_int(i):
    from pypy.lang.smalltalk import constants
    if i <= constants.TAGGED_MAXINT and i >= constants.TAGGED_MININT:
        return model.W_SmallInteger(i)
    raise WrappingError("integer too large to fit into a tagged pointer")

def wrap_float(i):
    return model.W_Float(i)

def wrap_string(string):
    from pypy.lang.smalltalk import classtable
    w_inst = classtable.w_String.as_class_get_shadow().new(len(string))
    for i in range(len(string)):
        w_inst.setchar(i, string[i])
    return w_inst

def wrap_char(c):
    from pypy.lang.smalltalk.objtable import CharacterTable
    return CharacterTable[ord(c)]

def wrap_bool(bool):
    from pypy.lang.smalltalk import objtable
    if bool:
        return objtable.w_true
    else:
        return objtable.w_false

def wrap_list(lst_w_obj):
    from pypy.lang.smalltalk import classtable
    """
    Converts a Python list of wrapper objects into
    a wrapped smalltalk array
    """
    lstlen = len(lit)
    res = classtable.w_Array.as_class_get_shadow().new(lstlen)
    for i in range(lstlen):
        res.storevarpointer(i, fakeliteral(lit[i]))
    return res


