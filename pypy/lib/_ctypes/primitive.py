import _rawffi
import weakref

SIMPLE_TYPE_CHARS = "cbBhHiIlLdfuzZqQPXOv"

from _ctypes.basics import _CData, _CDataMeta, cdata_from_address,\
     CArgObject
from _ctypes.builtin import ConvMode

class NULL(object):
    pass
NULL = NULL()

TP_TO_DEFAULT = {
        'c': 0,
        'u': 0,
        'b': 0,
        'B': 0,
        'h': 0,
        'H': 0,
        'i': 0,
        'I': 0,
        'l': 0,
        'L': 0,
        'q': 0,
        'Q': 0,
        'f': 0.0,
        'd': 0.0,
        'P': None,
        # not part of struct
        'O': NULL,
        'z': None,
        'Z': None,
}
 
DEFAULT_VALUE = object()

class GlobalPyobjContainer(object):
    def __init__(self):
        self.objs = []

    def add(self, obj):
        num = len(self.objs)
        self.objs.append(weakref.ref(obj))
        return num

    def get(self, num):
        return self.objs[num]()

pyobj_container = GlobalPyobjContainer()

def generic_xxx_p_from_param(self, value):
    from _ctypes import Array, _Pointer
    if value is None:
        return self(None)
    if isinstance(value, basestring):
        return self(value)
    if isinstance(value, _SimpleCData) and \
           type(value)._type_ in 'zZP':
        return value
    return None # eventually raise

class SimpleType(_CDataMeta):
    def __new__(self, name, bases, dct):
        try:
            tp = dct['_type_']
        except KeyError:
            for base in bases:
                if hasattr(base, '_type_'):
                    tp = base._type_
                    break
            else:
                raise AttributeError("cannot find _type_ attribute")
        if (not isinstance(tp, str) or
            not len(tp) == 1 or
            tp not in SIMPLE_TYPE_CHARS):
            raise ValueError('%s is not a type character' % (tp))
        default = TP_TO_DEFAULT[tp]
        ffiarray = _rawffi.Array(tp)
        result = type.__new__(self, name, bases, dct)
        result._ffiargshape = tp
        result._ffishape = tp
        result._fficompositesize = None
        result._ffiarray = ffiarray
        if tp == 'z':
            # c_char_p
            from _ctypes import Array, _Pointer

            def _getvalue(self):
                addr = self._buffer[0]
                if addr == 0:
                    return None
                else:
                    return _rawffi.charp2string(addr)

            def _setvalue(self, value):
                if isinstance(value, basestring):
                    if isinstance(value, unicode):
                        value = value.encode(ConvMode.encoding,
                                             ConvMode.errors)
                    #self._objects = value
                    array = _rawffi.Array('c')(len(value)+1, value)
                    value = array.buffer
                    self._objects = {'0': CArgObject(array)}
                elif value is None:
                    value = 0
                self._buffer[0] = value
            result.value = property(_getvalue, _setvalue)
        elif tp == 'Z':
            # c_wchar_p
            from _ctypes import Array, _Pointer, _wstring_at_addr
            def _getvalue(self):
                addr = self._buffer[0]
                if addr == 0:
                    return None
                else:
                    return _wstring_at_addr(addr, -1)

            def _setvalue(self, value):
                if isinstance(value, basestring):
                    if isinstance(value, str):
                        value = value.decode(ConvMode.encoding,
                                             ConvMode.errors)
                    #self._objects = value
                    array = _rawffi.Array('u')(len(value)+1, value)
                    value = array.buffer
                    self._objects = {'0': CArgObject(array)}
                elif value is None:
                    value = 0
                self._buffer[0] = value
            result.value = property(_getvalue, _setvalue)

        elif tp == 'P':
            # c_void_p

            def _getvalue(self):
                addr = self._buffer[0]
                if addr == 0:
                    return None
                return addr

            def _setvalue(self, value):
                if isinstance(value, str):
                    array = _rawffi.Array('c')(len(value)+1, value)
                    value = array.buffer
                    self._objects = {'0': CArgObject(array)}
                elif value is None:
                    value = 0
                self._buffer[0] = value
            result.value = property(_getvalue, _setvalue)            
        
        if tp in 'zZ':
            from _ctypes import Array, _Pointer
            # c_char_p
            def from_param(self, value):
                res = generic_xxx_p_from_param(self, value)
                if res is not None:
                    return res
                if isinstance(value, (Array, _Pointer)):
                    from ctypes import c_char, c_byte, c_wchar
                    if type(value)._type_ in [c_char, c_byte, c_wchar]:
                        return value
                return SimpleType.from_param(self, value)
            result.from_param = classmethod(from_param)
        elif tp == 'P':
            from _ctypes import Array, _Pointer
            # c_void_p
            def from_param(self, value):
                res = generic_xxx_p_from_param(self, value)
                if res is not None:
                    return res
                if isinstance(value, Array):
                    return value
                if isinstance(value, _Pointer):
                    return self.from_address(value._buffer.buffer)
                return SimpleType.from_param(self, value)
            result.from_param = classmethod(from_param)

        elif tp == 'u':
            def _setvalue(self, val):
                if isinstance(val, str):
                    val = val.decode(ConvMode.encoding, ConvMode.errors)
                # possible if we use 'ignore'
                if val:
                    self._buffer[0] = val
            def _getvalue(self):
                return self._buffer[0]
            result.value = property(_getvalue, _setvalue)

        elif tp == 'c':
            def _setvalue(self, val):
                if isinstance(val, unicode):
                    val = val.encode(ConvMode.encoding, ConvMode.errors)
                if val:
                    self._buffer[0] = val
            def _getvalue(self):
                return self._buffer[0]
            result.value = property(_getvalue, _setvalue)

        elif tp == 'O':
            def _setvalue(self, val):
                num = pyobj_container.add(val)
                self._buffer[0] = num
            def _getvalue(self):
                return pyobj_container.get(self._buffer[0])
            result.value = property(_getvalue, _setvalue)

        return result

    from_address = cdata_from_address

    def from_param(self, value):
        if isinstance(value, self):
            return value
        try:
            return self(value)
        except (TypeError, ValueError):
            return super(SimpleType, self).from_param(value)

    def _sizeofinstances(self):
        return _rawffi.sizeof(self._type_)

    def _alignmentofinstances(self):
        return _rawffi.alignment(self._type_)

    def _is_pointer_like(self):
        return self._type_ in "sPzUZXO"

class _SimpleCData(_CData):
    __metaclass__ = SimpleType
    _type_ = 'i'

    def __init__(self, value=DEFAULT_VALUE):
        self._buffer = self._ffiarray(1, autofree=True)
        if value is not DEFAULT_VALUE:
            self.value = value

    def _ensure_objects(self):
        return None

    def _getvalue(self):
        return self._buffer[0]

    def _setvalue(self, value):
        self._buffer[0] = value
    value = property(_getvalue, _setvalue)
    del _getvalue, _setvalue

    def __ctypes_from_outparam__(self):
        return self.value

    def __repr__(self):
        return "%s(%r)" % (type(self).__name__, self.value)

    def __nonzero__(self):
        return self._buffer[0] not in (0, '\x00')
