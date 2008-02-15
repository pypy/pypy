
import _rawffi

from _ctypes.basics import _CData, cdata_from_address, _CDataMeta, sizeof,\
     keepalive_key

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
                res._ffishape = ffiarray.gettypecode(typedict['_length_'])
        else:
            res._ffiarray = None
        return res

    from_address = cdata_from_address

    def _sizeofinstances(self):
        size, alignment = self._ffiarray.gettypecode(self._length_)
        return size

    def _alignmentofinstances(self):
        return self._type_._alignmentofinstances()

    def from_param(self, value):
        # check for iterable
        try:
            iter(value)
        except ValueError:
            return _CDataMeta.from_param(self, value)
        else:
            if len(value) > self._length_:
                raise ValueError("%s too long" % (value,))
            return self(*value)

def array_get_slice_params(self, index):
    if index.step is not None:
        raise TypeError("3 arg slices not supported (for no reason)")
    start = index.start or 0
    stop = index.stop or self._length_
    return start, stop

def array_slice_setitem(self, index, value):
    start, stop = self._get_slice_params(index)
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
    _ffiletter = 'P'
    _needs_free = False

    def __init__(self, *args):
        self._buffer = self._ffiarray(self._length_)
        self._needs_free = True
        self._objects = {}
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
        if getattr(value, '_objects', None):
            self._objects[keepalive_key(index)] = value._objects
        value = self._type_._CData_input(value)
        if not isinstance(self._type_._ffishape, tuple):
            self._buffer[index] = value[0]
            # something more sophisticated, cannot set field directly
        else:
            from ctypes import memmove
            dest = self._buffer.itemaddress(index)
            source = value[0]
            memmove(dest, source, self._type_._ffishape[0])

    def __getitem__(self, index):
        if isinstance(index, slice):
            return self._slice_getitem(index)
        index = self._fix_index(index)
        return self._type_._CData_output(self._subarray(index), self,
                                         self._ffiarray.gettypecode(index)[0])

    def __len__(self):
        return self._length_

    def _get_buffer_for_param(self):
        return self._buffer.byptr()

    def __del__(self):
        if self._needs_free:
            self._buffer.free()
            self._buffer = None
            self._needs_free = False

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
