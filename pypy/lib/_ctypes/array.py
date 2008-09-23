
import _rawffi

from _ctypes.basics import _CData, cdata_from_address, _CDataMeta, sizeof
from _ctypes.basics import keepalive_key, store_reference, ensure_objects
from _ctypes.basics import CArgObject
from _ctypes.builtin import _string_at_addr, _wstring_at_addr

def _create_unicode(buffer, maxlength):
    res = []
    for i in range(maxlength):
        if buffer[i] == '\x00':
            break
        res.append(buffer[i])
    return u''.join(res)

class ArrayMeta(_CDataMeta):
    def __new__(self, name, cls, typedict):
        res = type.__new__(self, name, cls, typedict)
        if '_type_' in typedict:
            ffiarray = _rawffi.Array(typedict['_type_']._ffishape)
            res._ffiarray = ffiarray
            subletter = getattr(typedict['_type_'], '_type_', None)
            if subletter == 'c':
                def getvalue(self):
                    return _rawffi.charp2string(self._buffer.buffer,
                                                self._length_)
                def setvalue(self, val):
                    # we don't want to have buffers here
                    if len(val) > self._length_:
                        raise ValueError("%r too long" % (val,))
                    for i in range(len(val)):
                        self[i] = val[i]
                    if len(val) < self._length_:
                        self[len(val)] = '\x00'
                res.value = property(getvalue, setvalue)

                def getraw(self):
                    return "".join([self[i] for i in range(self._length_)])

                def setraw(self, buffer):
                    for i in range(len(buffer)):
                        self[i] = buffer[i]
                res.raw = property(getraw, setraw)
            elif subletter == 'u':
                def getvalue(self):
                    # rawffi support anyone?
                    return _create_unicode(self._buffer, self._length_)

                def setvalue(self, val):
                    # we don't want to have buffers here
                    if len(val) > self._length_:
                        raise ValueError("%r too long" % (val,))
                    for i in range(len(val)):
                        self[i] = val[i]
                    if len(val) < self._length_:
                        self[len(val)] = '\x00'
                res.value = property(getvalue, setvalue)
                
            if '_length_' in typedict:
                res._ffishape = (ffiarray, typedict['_length_'])
                res._fficompositesize = res._sizeofinstances()
        else:
            res._ffiarray = None
        return res

    from_address = cdata_from_address

    def _sizeofinstances(self):
        size, alignment = self._ffiarray.size_alignment(self._length_)
        return size

    def _alignmentofinstances(self):
        return self._type_._alignmentofinstances()

    def _CData_output(self, resarray, base=None, index=-1):
        # this seems to be a string if we're array of char, surprise!
        from ctypes import c_char, c_wchar, c_char_p, c_wchar_p
        if self._type_ is c_char:
            return _rawffi.charp2string(resarray.buffer, self._length_)
        if self._type_ is c_wchar:
            xxx
        res = self.__new__(self)
        ffiarray = self._ffiarray.fromaddress(resarray.buffer, self._length_)
        res._buffer = ffiarray
        res._base = base
        res._index = index
        return res.__ctypes_from_outparam__()

    def _CData_retval(self, resbuffer):
        raise NotImplementedError

    def _CData_value(self, value):
        # array accepts very strange parameters as part of structure
        # or function argument...
        from ctypes import c_char, c_wchar
        if issubclass(self._type_, (c_char, c_wchar)):
            if isinstance(value, basestring):
                if len(value) > self._length_:
                    raise ValueError("Invalid length")
                value = self(*value)
        else:
            if isinstance(value, tuple):
                if len(value) > self._length_:
                    raise RuntimeError("Invalid length")
                value = self(*value)
        return _CDataMeta._CData_value(self, value)

def array_get_slice_params(self, index):
    if index.step is not None:
        raise TypeError("3 arg slices not supported (for no reason)")
    start = index.start or 0
    stop = index.stop or self._length_
    return start, stop

def array_slice_setitem(self, index, value):
    start, stop = self._get_slice_params(index)
    if stop - start != len(value):
        raise ValueError("Can only assign slices of the same length")
    for i in range(start, stop):
        self[i] = value[i - start]

def array_slice_getitem(self, index):
    start, stop = self._get_slice_params(index)
    l = [self[i] for i in range(start, stop)]
    letter = getattr(self._type_, '_type_', None)
    if letter == 'c':
        return "".join(l)
    if letter == 'u':
        return u"".join(l)
    return l

class Array(_CData):
    __metaclass__ = ArrayMeta
    _ffiargshape = 'P'

    def __init__(self, *args):
        self._buffer = self._ffiarray(self._length_, autofree=True)
        for i, arg in enumerate(args):
            self[i] = arg

    def _fix_index(self, index):
        if index < 0:
            index += self._length_
        if 0 <= index < self._length_:
            return index
        else:
            raise IndexError

    _get_slice_params = array_get_slice_params
    _slice_getitem = array_slice_getitem
    _slice_setitem = array_slice_setitem

    def _subarray(self, index):
        """Return a _rawffi array of length 1 whose address is the same as
        the index'th item of self."""
        address = self._buffer.itemaddress(index)
        return self._ffiarray.fromaddress(address, 1)

    def __setitem__(self, index, value):
        if isinstance(index, slice):
            self._slice_setitem(index, value)
            return
        index = self._fix_index(index)
        if ensure_objects(value) is not None:
            store_reference(self, index, value._objects)
        arg = self._type_._CData_value(value)
        if self._type_._fficompositesize is None:
            self._buffer[index] = arg
            # something more sophisticated, cannot set field directly
        else:
            from ctypes import memmove
            dest = self._buffer.itemaddress(index)
            memmove(dest, arg, self._type_._fficompositesize)

    def __getitem__(self, index):
        if isinstance(index, slice):
            return self._slice_getitem(index)
        index = self._fix_index(index)
        return self._type_._CData_output(self._subarray(index), self, index)

    def __len__(self):
        return self._length_

    def _get_buffer_for_param(self):
        return CArgObject(self._buffer.byptr())

    def _get_buffer_value(self):
        return self._buffer.buffer

ARRAY_CACHE = {}

def create_array_type(base, length):
    if not isinstance(length, (int, long)):
        raise TypeError("Can't multiply a ctypes type by a non-integer")
    if length < 0:
        raise ValueError("Array length must be >= 0")
    key = (base, length)
    try:
        return ARRAY_CACHE[key]
    except KeyError:
        name = "%s_Array_%d" % (base.__name__, length)
        tpdict = dict(
            _length_ = length,
            _type_ = base
        )
        cls = ArrayMeta(name, (Array,), tpdict)
        ARRAY_CACHE[key] = cls
        return cls
