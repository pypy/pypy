
class _SimpleCData(object):
    def __init__(self, value):
        self.value = value

class c_ushort(_SimpleCData):
    _type_ = 'H'

class c_double(_SimpleCData):
    _type_ = 'd'

class c_ubyte(_SimpleCData):
    _type_ = 'B'

class c_float(_SimpleCData):
    _type_ = 'f'

class c_ulong(_SimpleCData):
    _type_ = 'L'

class c_short(_SimpleCData):
    _type_ = 'h'

class c_ubyte(_SimpleCData):
    _type_ = 'b'

class c_byte(_SimpleCData):
    _type_ = 'B'

class c_char(_SimpleCData):
    _type_ = 'c'

class c_long(_SimpleCData):
    _type_ = 'l'

class c_ulonglong(_SimpleCData):
    _type_ = 'Q'

class c_longlong(_SimpleCData):
    _type_ = 'q'

class c_int(_SimpleCData):
    _type_ = 'i'

class c_uint(_SimpleCData):
    _type_ = 'I'

class c_double(_SimpleCData):
    _type_ = 'd'

class c_float(_SimpleCData):
    _type_ = 'f'

c_size_t = c_ulong # XXX

class c_void_p(_SimpleCData):
    _type_ = 'P'

class c_char_p(_SimpleCData):
    _type_ = 's'
