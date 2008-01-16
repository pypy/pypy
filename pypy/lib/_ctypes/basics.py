
import _rawffi
import sys

class _CDataMeta(type):
    def from_param(self, value):
        if isinstance(value, self):
            return value
        try:
            as_parameter = value._as_parameter_
        except AttributeError:
            raise TypeError("expected %s instance instead of %s" % (
                self.__name__, type(value).__name__))
        else:
            return self.from_param(as_parameter)

    def _CData_input(self, value):
        """Used when data enters into ctypes from user code.  'value' is
        some user-specified Python object, which is converted into a _rawffi
        array of length 1 containing the same value according to the
        type 'self'.
        """
        cobj = self.from_param(value)
        return cobj._get_buffer_for_param()

    def _CData_output(self, resarray):
        """Used when data exits ctypes and goes into user code.
        'resarray' is a _rawffi array of length 1 containing the value,
        and this returns a general Python object that corresponds.
        """
        res = self.__new__(self)
        res._buffer = resarray
        return res.__ctypes_from_outparam__()

    def __mul__(self, other):
        from _ctypes.array import create_array_type
        return create_array_type(self, other)

    def _is_pointer_like(self):
        return False

class _CData(object):
    """ The most basic object for all ctypes types
    """
    __metaclass__ = _CDataMeta

    def __init__(self, *args, **kwds):
        raise TypeError("%s has no type" % (type(self),))

    def __ctypes_from_outparam__(self):
        return self

    def _get_buffer_for_param(self):
        return self._buffer

#class CArgObject(object):
#    def __init__(self, letter, raw_value, _type):
#        self.ffiletter = letter
#        self._array = raw_value
#        self._type = _type

#    def __repr__(self):
#        return "<cparam '%s' %r>" % (self.ffiletter, self._array[0])


def sizeof(tp):
    if not isinstance(tp, _CDataMeta):
        if isinstance(tp, _CData):
            tp = type(tp)
        else:
            raise TypeError("ctypes type or instance expected, got %r" % (
                type(tp).__name__,))
    return tp._sizeofinstances()

def alignment(tp):
    ffitp = tp._type_
    return _rawffi.alignment(ffitp)

def byref(cdata):
    from ctypes import pointer
    return pointer(cdata)

def cdata_from_address(self, address):
    # fix the address, in case it's unsigned
    address = address & (sys.maxint * 2 + 1)
    instance = self.__new__(self)
    lgt = getattr(self, '_length_', 1)
    instance._buffer = self._ffiarray.fromaddress(address, lgt)
    return instance

def addressof(tp):
    return tp._buffer.buffer
