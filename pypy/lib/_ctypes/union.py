

import _rawffi
from _ctypes.basics import _CData, _CDataMeta, store_reference, keepalive_key
from _ctypes.basics import ensure_objects
from _ctypes.structure import round_up, names_and_fields, struct_getattr,\
     struct_setattr
import inspect


def _set_shape(tp):
    size = tp._sizeofinstances()
    alignment = tp._alignmentofinstances()
    tp._ffiopaque = _rawffi.Structure((size, alignment)) # opaque
    tp._ffiargshape = tp._ffishape = (tp._ffiopaque, 1)
    tp._fficompositesize = tp._ffiopaque.size
    # we need to create an array of size one for each
    # of our elements
    tp._ffiarrays = {}
    for name, field in tp._fieldtypes.iteritems():
        tp._ffiarrays[name] = _rawffi.Array(field.ctype._ffishape)
        
class UnionMeta(_CDataMeta):
    def __new__(self, name, cls, typedict):
        res = type.__new__(self, name, cls, typedict)
        if '_fields_' in typedict:
            res._names, rawfields, res._fieldtypes = names_and_fields(
                typedict['_fields_'], cls[0], True,
                typedict.get('_anonymous_', None))
            _set_shape(res)

        def __init__(self): # don't allow arguments by now
            if not hasattr(self, '_ffiarrays'):
                raise TypeError("Cannot instantiate union, has no type")
            # malloc size
            size = self.__class__._sizeofinstances()
            self.__dict__['_objects'] = {}
            self.__dict__['_buffer'] = self._ffiopaque(autofree=True)
        res.__init__ = __init__
        return res

    def _sizeofinstances(self):
        if not hasattr(self, '_size_'):
            self._size_ = max([field.size for field in
                               self._fieldtypes.values()] + [0])
        return self._size_

    def _alignmentofinstances(self):
        from ctypes import alignment
        if not hasattr(self, '_alignment_'):
            self._alignment_ = max([alignment(field.ctype) for field in
                                    self._fieldtypes.values()] + [1])
        return self._alignment_
    
    __getattr__ = struct_getattr

    def __setattr__(self, name, value):
        if name == '_fields_':
            if self.__dict__.get('_fields_', None):
                raise AttributeError("_fields_ is final")
            if self in [v for k, v in value]:
                raise AttributeError("Union cannot contain itself")
            self._names, rawfields, self._fieldtypes = names_and_fields(
                value, self.__bases__[0], True,
                self.__dict__.get('_anonymous_', None))
            _CDataMeta.__setattr__(self, '_fields_', value)
            _set_shape(self)
        _CDataMeta.__setattr__(self, name, value)

    def _CData_output(self, resarray, base=None, index=-1):
        res = self.__new__(self)
        ffiopaque = self._ffiopaque.fromaddress(resarray.buffer)
        res.__dict__['_buffer'] = ffiopaque
        res.__dict__['_base'] = base
        res.__dict__['_index'] = index
        return res.__ctypes_from_outparam__()
    
    def _CData_retval(self, resbuffer):
        res = self.__new__(self)
        res.__dict__['_buffer'] = resbuffer
        res.__dict__['_base'] = None
        res.__dict__['_index'] = -1
        return res.__ctypes_from_outparam__()


class Union(_CData):
    __metaclass__ = UnionMeta

    def __getattr__(self, name):
        try:
            fieldtype = self._fieldtypes[name].ctype
        except KeyError:
            raise AttributeError(name)
        val = self._ffiarrays[name].fromaddress(self._buffer.buffer, 1)
        offset = self.__class__._fieldtypes[name].num        
        return fieldtype._CData_output(val, self, offset)

    def __setattr__(self, name, value):
        try:
            fieldtype = self._fieldtypes[name].ctype
        except KeyError:
            raise AttributeError(name)
        if ensure_objects(value) is not None:
            key = keepalive_key(getattr(self.__class__, name).num)
            store_reference(self, key, value._objects)
        arg = fieldtype._CData_value(value)
        if fieldtype._fficompositesize is not None:
            from ctypes import memmove
            dest = self._buffer.buffer
            memmove(dest, arg, fieldtype._fficompositesize)
        else:
            buf = self._ffiarrays[name].fromaddress(self._buffer.buffer, 1)
            buf[0] = arg

    def _get_buffer_value(self):
        return self._buffer.buffer
