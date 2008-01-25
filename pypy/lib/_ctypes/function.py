
import types
from _ctypes.basics import _CData, _CDataMeta, ArgumentError
import _rawffi

class CFuncPtrType(_CDataMeta):
    # XXX write down here defaults and such things

    def _sizeofinstances(self):
        return _rawffi.sizeof('P')

    def _alignmentofinstances(self):
        return _rawffi.alignment('P')

class CFuncPtr(_CData):
    __metaclass__ = CFuncPtrType

    _argtypes_ = None
    _restype_ = None
    _ffiletter = 'P'
    _ffishape = 'P'

    def _getargtypes(self):
        return self._argtypes_
    def _setargtypes(self, argtypes):
        self._argtypes_ = argtypes    
    argtypes = property(_getargtypes, _setargtypes)

    def _getrestype(self):
        return self._restype_
    def _setrestype(self, restype):
        if restype is int:
            from ctypes import c_int
            restype = c_int
        if not isinstance(restype, _CDataMeta) and not restype is None:
            raise TypeError("Expected ctypes type, got %s" % (restype,))
        self._restype_ = restype
    restype = property(_getrestype, _setrestype)    

    def __init__(self, argument=None):
        self.callable = None
        self.name = None
        if isinstance(argument, int):
            self._buffer = _rawffi.Array('P').fromaddress(argument, 1)
            # XXX finish this one, we need to be able to jump there somehow
        elif callable(argument):
            self.callable = argument
            argtypes = [arg._ffiletter for arg in self._argtypes_]
            restype = self._restype_._ffiletter
            self._ptr = _rawffi.CallbackPtr(argument, argtypes, restype)
            self._buffer = self._ptr.byptr()
        elif isinstance(argument, tuple) and len(argument) == 2:
            import ctypes
            self.name, self.dll = argument
            if isinstance(self.dll, str):
                self.dll = ctypes.CDLL(self.dll)
            # we need to check dll anyway
            self._getfuncptr([], ctypes.c_int)
        elif argument is None:
            return # needed for test..
        else:
            raise TypeError("Unknown constructor %s" % (argument,))
    
    def __call__(self, *args):
        if self.callable is not None:
            return self.callable(*args)
        argtypes = self._argtypes_
        if argtypes is None:
            argtypes = self._guess_argtypes(args)
        else:
            dif = len(args) - len(argtypes)
            if dif < 0:
                raise TypeError("Not enough arguments")
            if dif > 0:
                cut = len(args) - dif
                argtypes = argtypes[:] + self._guess_argtypes(args[cut:])
        restype = self._restype_
        funcptr = self._getfuncptr(argtypes, restype)
        resarray = funcptr(*self._wrap_args(argtypes, args))
        if restype is not None:
            return restype._CData_output(resarray)

    def _getfuncptr(self, argtypes, restype):
        if restype is None:
            import ctypes
            restype = ctypes.c_int
        argletters = [arg._ffiletter for arg in argtypes]
        return self.dll._handle.ptr(self.name, argletters, restype._ffiletter)

    def _guess_argtypes(self, args):
        from _ctypes import _CData
        from ctypes import c_char_p, c_void_p, c_int, Array, Structure
        res = []
        for arg in args:
            if hasattr(arg, '_as_parameter_'):
                arg = arg._as_parameter_
            if isinstance(arg, str):
                res.append(c_char_p)
            elif isinstance(arg, _CData):
                res.append(type(arg))
            elif arg is None:
                res.append(c_void_p)
            elif arg == 0:
                res.append(c_void_p)
            elif isinstance(arg, (int, long)):
                res.append(c_int)
            else:
                raise TypeError("Don't know how to handle %s" % (arg,))
        return res

    def _wrap_args(self, argtypes, args):
        try:
            return [argtype._CData_input(arg) for argtype, arg in
                    zip(argtypes, args)]
        except TypeError, e:
            raise ArgumentError(e.args[0])
