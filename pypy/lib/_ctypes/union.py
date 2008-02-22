

import _rawffi
from _ctypes.basics import _CData, _CDataMeta
from _ctypes.structure import round_up, names_and_fields, struct_getattr,\
     struct_setattr
import inspect

class UnionMeta(_CDataMeta):
    def __new__(self, name, cls, typedict):
        res = type.__new__(self, name, cls, typedict)
        if '_fields_' in typedict:
            res._names, rawfields, res._fieldtypes = names_and_fields(
                typedict['_fields_'], cls[0], True,
                typedict.get('_anonymous_', None))
            res._ffishape = (res._sizeofinstances(),
                             res._alignmentofinstances())
            res._ffiargshape = res._ffishape
            # we need to create an array of size one for each
            # of our elements
            res._ffiarrays = {}
            for name, field in res._fieldtypes.iteritems():
                res._ffiarrays[name] = _rawffi.Array(field.ctype._ffishape)
        def __init__(self): # don't allow arguments by now
            if not hasattr(self, '_ffiarrays'):
                raise TypeError("Cannot instantiate union, has no type")
            # malloc size
            size = self.__class__._sizeofinstances()
            self.__dict__['_buffer'] = _rawffi.Array('c')(size)
            self.__dict__['_needs_free'] = True
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
            self._ffiarrays = {}
            for name, field in self._fieldtypes.iteritems():
                self._ffiarrays[name] = _rawffi.Array(field.ctype._ffishape)
            _CDataMeta.__setattr__(self, '_fields_', value)
            self._ffiargshape = self._ffishape = (self._sizeofinstances(),
                                                  self._alignmentofinstances())
            return
        _CDataMeta.__setattr__(self, name, value)

class Union(_CData):
    __metaclass__ = UnionMeta
    _needs_free = False

    def __getattr__(self, name):
        try:
            fieldtype = self._fieldtypes[name].ctype
        except KeyError:
            raise AttributeError(name)
        val = self._ffiarrays[name].fromaddress(self._buffer.buffer, 1)
        return fieldtype._CData_output(val)

    def __setattr__(self, name, value):
        try:
            fieldtype = self._fieldtypes[name].ctype
        except KeyError:
            raise AttributeError(name)
        buf = self._ffiarrays[name].fromaddress(self._buffer.buffer, 1)
        buf[0] = fieldtype._CData_value(value)

    def __del__(self):
        if self._needs_free:
            self._buffer.free()
            self.__dict__['_buffer'] = None
            self.__dict__['_needs_free'] = False
