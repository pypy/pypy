
import _rawffi

from _ctypes.basics import _CData, cdata_from_address, _CDataMeta, sizeof

class ArrayMeta(_CDataMeta):
    def __new__(self, name, cls, typedict):
        res = type.__new__(self, name, cls, typedict)
        if '_type_' in typedict:
            ffiarray = _rawffi.Array(typedict['_type_']._ffiletter)
            res._ffiarray = ffiarray
            if getattr(typedict['_type_'], '_type_', None) == 'c':
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
        else:
            res._ffiarray = None
        return res

    from_address = cdata_from_address

    def _sizeofinstances(self):
        size, alignment = self._ffiarray.gettypecode(self._length_)
        return size

    def _alignmentofinstances(self):
        return self._type_._alignmentofinstances()

class Array(_CData):
    __metaclass__ = ArrayMeta
    _ffiletter = 'P'

    def __init__(self, *args):
        self._buffer = self._ffiarray(self._length_)
        for i, arg in enumerate(args):
            self[i] = arg

    def _fix_index(self, index):
        if index < 0:
            index += self._length_
        if 0 <= index < self._length_:
            return index
        else:
            raise IndexError

    def _get_slice_params(self, index):
        if index.step is not None:
            raise TypeError("3 arg slices not supported (for no reason)")
        start = index.start or 0
        stop = index.stop or self._length_
        return start, stop
    
    def _slice_setitem(self, index, value):
        start, stop = self._get_slice_params(index)
        for i in range(start, stop):
            self[i] = value[i - start]

    def _slice_getitem(self, index):
        start, stop = self._get_slice_params(index)
        return "".join([self[i] for i in range(start, stop)])

    def _subarray(self, index):
        """Return a _rawffi array of length 1 whose address is the same as
        the index'th item of self."""
        address = self._buffer.itemaddress(index)
        return self._ffiarray.fromaddress(address, 1)

    def __setitem__(self, index, value):
        if isinstance(index, slice):
            self._slice_setitem(index, value)
            return
        value = self._type_._CData_input(value)
        index = self._fix_index(index)
        self._buffer[index] = value[0]

    def __getitem__(self, index):
        if isinstance(index, slice):
            return self._slice_getitem(index)
        index = self._fix_index(index)
        return self._type_._CData_output(self._subarray(index))

    def __len__(self):
        return self._length_

    def _get_buffer_for_param(self):
        return self._buffer.byptr()

ARRAY_CACHE = {}

def create_array_type(base, length):
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
