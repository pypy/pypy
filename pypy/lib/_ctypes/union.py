

import _rawffi
from _ctypes.basics import _CData, _CDataMeta
from _ctypes.structure import round_up, names_and_fields, struct_getattr
import inspect

class UnionMeta(_CDataMeta):
    def __new__(self, name, cls, typedict):
        res = type.__new__(self, name, cls, typedict)
        if '_fields_' in typedict:
            res._names, rawfields, res._fieldtypes = names_and_fields(
                typedict['_fields_'], cls[0], True)
            res._ffishape = (res._sizeofinstances(),
                             res._alignmentofinstances())
            # we need to create an array of size one for each
            # of our elements
            res._ffiarrays = {}
            for name, field in res._fieldtypes.iteritems():
                res._ffiarrays[name] = _rawffi.Array(field.ctype._ffishape)
            def __init__(self): # don't allow arguments by now
                # malloc size
                size = self.__class__._sizeofinstances()
                self.__dict__['_buffer'] = _rawffi.Array('c')(size)
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

class Union(_CData):
    __metaclass__ = UnionMeta
    _ffiletter = 'P'

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
        value = fieldtype._CData_input(value)
        buf = self._ffiarrays[name].fromaddress(self._buffer.buffer, 1)
        buf[0] = value[0]
