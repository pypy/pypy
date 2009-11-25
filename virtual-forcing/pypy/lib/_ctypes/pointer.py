
import _rawffi
from _ctypes.basics import _CData, _CDataMeta, cdata_from_address
from _ctypes.basics import sizeof, byref, keepalive_key
from _ctypes.array import Array, array_get_slice_params, array_slice_getitem,\
     array_slice_setitem

DEFAULT_VALUE = object()

class PointerType(_CDataMeta):
    def __new__(self, name, cls, typedict):
        d = dict(
            size       = _rawffi.sizeof('P'),
            align      = _rawffi.alignment('P'),
            length     = 1,
            _ffiargshape = 'P',
            _ffishape  = 'P',
            _fficompositesize = None
        )
        # XXX check if typedict['_type_'] is any sane
        # XXX remember about paramfunc
        obj = type.__new__(self, name, cls, typedict)
        for k, v in d.iteritems():
            setattr(obj, k, v)
        if '_type_' in typedict:
            self.set_type(obj, typedict['_type_'])
        else:
            def __init__(self, value=None):
                raise TypeError("%s has no type" % obj)
            obj.__init__ = __init__
        return obj

    def from_param(self, value):
        if value is None:
            return self(None)
        # If we expect POINTER(<type>), but receive a <type> instance, accept
        # it by calling byref(<type>).
        if isinstance(value, self._type_):
            return byref(value)
        # Array instances are also pointers when the item types are the same.
        if isinstance(value, (_Pointer, Array)):
            if issubclass(type(value)._type_, self._type_):
                return value
        return _CDataMeta.from_param(self, value)

    def _sizeofinstances(self):
        return _rawffi.sizeof('P')

    def _alignmentofinstances(self):
        return _rawffi.alignment('P')

    def _is_pointer_like(self):
        return True

    def set_type(self, TP):
        ffiarray = _rawffi.Array('P')
        def __init__(self, value=None):
            self._buffer = ffiarray(1, autofree=True)
            if value is not None:
                self.contents = value
        self._ffiarray = ffiarray
        self.__init__ = __init__
        self._type_ = TP

    from_address = cdata_from_address

class _Pointer(_CData):
    __metaclass__ = PointerType

    def getcontents(self):
        addr = self._buffer[0]
        if addr == 0:
            raise ValueError("NULL pointer access")
        return self._type_.from_address(addr)

    def setcontents(self, value):
        if not isinstance(value, self._type_):
            raise TypeError("expected %s instead of %s" % (
                self._type_.__name__, type(value).__name__))
        self._objects = {keepalive_key(1):value}
        if value._ensure_objects() is not None:
            self._objects[keepalive_key(0)] = value._objects
        value = value._buffer
        self._buffer[0] = value

    _get_slice_params = array_get_slice_params
    _slice_getitem = array_slice_getitem

    def _subarray(self, index=0):
        """Return a _rawffi array of length 1 whose address is the same as
        the index'th item to which self is pointing."""
        address = self._buffer[0]
        address += index * sizeof(self._type_)
        return self._type_.from_address(address)._buffer

    def __getitem__(self, index):
        if isinstance(index, slice):
            return self._slice_getitem(index)
        return self._type_._CData_output(self._subarray(index), self, index)

    def __setitem__(self, index, value):
        self._subarray(index)[0] = self._type_._CData_value(value)

    def __nonzero__(self):
        return self._buffer[0] != 0

    contents = property(getcontents, setcontents)

def _cast_addr(obj, _, tp):
    if not (isinstance(tp, _CDataMeta) and tp._is_pointer_like()):
        raise TypeError("cast() argument 2 must be a pointer type, not %s"
                        % (tp,))
    if isinstance(obj, Array):
        ptr = tp.__new__(tp)
        ptr._buffer = tp._ffiarray(1, autofree=True)
        ptr._buffer[0] = obj._buffer
        return ptr
    if isinstance(obj, (int, long)):
        result = tp()
        result._buffer[0] = obj
        return result
    if obj is None:
        result = tp()
        return result
    if not (isinstance(obj, _CData) and type(obj)._is_pointer_like()):
        raise TypeError("cast() argument 1 must be a pointer, not %s"
                        % (type(obj),))
    result = tp()
    result._buffer[0] = obj._buffer[0]
    return result
