

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

        return res

    def _sizeofinstances(self):
        return max([field.size for field in self._fieldtypes.values()]
                   + [0])

    def _alignmentofinstances(self):
        return max([field.alignment for field in self._fieldtypes.values()]
                   + [1])

    __getattr__ = struct_getattr

class Union(_CData):
    __metaclass__ = UnionMeta
    _ffiletter = 'P'
