
import _rawffi
from _ctypes.basics import _CData, _CDataMeta
import inspect

class StructureMeta(_CDataMeta):
    def __new__(self, name, cls, typedict):
        res = type.__new__(self, name, cls, typedict)
        if '_fields_' in typedict:
            all_fields = typedict['_fields_'][:]
            for cls in inspect.getmro(cls[0]):
                all_fields += getattr(cls, '_fields_', [])
            names = [name for name, ctype in all_fields]
            res._fieldtypes = dict(all_fields)
            rawfields = [(name, ctype._ffiletter)
                         for name, ctype in all_fields]
            ffistruct = _rawffi.Structure(rawfields)
            res._ffistruct = ffistruct

            def __init__(self, *args, **kwds):
                self.__dict__['_buffer'] = ffistruct()
                if len(args) > len(names):
                    raise TypeError("too many arguments")
                for name, arg in zip(names, args):
                    if name in kwds:
                        raise TypeError("duplicate value for argument %r" % (
                            name,))
                    self.__setattr__(name, arg)
                for name, arg in kwds.items():
                    self.__setattr__(name, arg)
            res.__init__ = __init__

        return res

    def from_address(self, address):
        instance = self.__new__(self)
        instance.__dict__['_buffer'] = self._ffistruct.fromaddress(address)
        return instance

    def _sizeofinstances(self):
        return self._ffistruct.size

class Structure(_CData):
    __metaclass__ = StructureMeta

    def _subarray(self, fieldtype, name):
        """Return a _rawffi array of length 1 whose address is the same as
        the address of the field 'name' of self."""
        address = self._buffer.fieldaddress(name)
        A = _rawffi.Array(fieldtype._ffiletter)
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
