
import _rawffi
from _ctypes.basics import _CData, _CDataMeta
import inspect

def names_and_fields(_fields_, superclass):
    all_fields = _fields_[:]
    for cls in inspect.getmro(superclass):
        all_fields += getattr(cls, '_fields_', [])
    names = [name for name, ctype in all_fields]
    rawfields = [(name, ctype._ffishape)
                 for name, ctype in all_fields]
    return names, rawfields, dict(all_fields)

class StructureMeta(_CDataMeta):
    def __new__(self, name, cls, typedict):
        res = type.__new__(self, name, cls, typedict)
        if '_fields_' in typedict:
            res._names, rawfields, res._fieldtypes = names_and_fields(
                typedict['_fields_'], cls[0])
            res._ffistruct = _rawffi.Structure(rawfields)
            res._ffishape = res._ffistruct.gettypecode()

        def __init__(self, *args, **kwds):
            if not hasattr(self, '_ffistruct'):
                raise TypeError("Cannot instantiate structure, has no _fields_")
            self.__dict__['_buffer'] = self._ffistruct()
            if len(args) > len(self._names):
                raise TypeError("too many arguments")
            for name, arg in zip(self._names, args):
                if name in kwds:
                    raise TypeError("duplicate value for argument %r" % (
                        name,))
                self.__setattr__(name, arg)
            for name, arg in kwds.items():
                self.__setattr__(name, arg)
        res.__init__ = __init__


        return res

    def __setattr__(self, name, value):
        if name == '_fields_':
            if self.__dict__.get('_fields_', None):
                raise AttributeError("_fields_ is final")
            self._names, rawfields, self._fieldtypes = names_and_fields(
                value, self.__bases__[0])
            self._ffistruct = _rawffi.Structure(rawfields)
            _CDataMeta.__setattr__(self, '_fields_', value)
            self._ffishape = self._ffistruct.gettypecode()
            return
        _CDataMeta.__setattr__(self, name, value)

    def from_address(self, address):
        instance = self.__new__(self)
        instance.__dict__['_buffer'] = self._ffistruct.fromaddress(address)
        return instance

    def _sizeofinstances(self):
        if not hasattr(self, '_ffistruct'):
            return 0
        return self._ffistruct.size

    def _alignmentofinstances(self):
        return self._ffistruct.alignment

class Structure(_CData):
    __metaclass__ = StructureMeta
    _ffiletter = 'P'

    def _subarray(self, fieldtype, name):
        """Return a _rawffi array of length 1 whose address is the same as
        the address of the field 'name' of self."""
        address = self._buffer.fieldaddress(name)
        A = _rawffi.Array(fieldtype._ffishape)
        return A.fromaddress(address, 1)

    def __setattr__(self, name, value):
        try:
            fieldtype = self._fieldtypes[name]
        except KeyError:
            raise AttributeError(name)
        value = fieldtype._CData_input(value)
        self._buffer.__setattr__(name, value[0])

    def __getattr__(self, name):
        try:
            fieldtype = self._fieldtypes[name]
        except KeyError:
            raise AttributeError(name)
        return fieldtype._CData_output(self._subarray(fieldtype, name))

    def _get_buffer_for_param(self):
        return self._buffer.byptr()
