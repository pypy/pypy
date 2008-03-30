
import types
from _ctypes.basics import _CData, _CDataMeta, ArgumentError, keepalive_key
import _rawffi

class CFuncPtrType(_CDataMeta):
    # XXX write down here defaults and such things

    def _sizeofinstances(self):
        return _rawffi.sizeof('P')

    def _alignmentofinstances(self):
        return _rawffi.alignment('P')

    def _is_pointer_like(self):
        return True

class CFuncPtr(_CData):
    __metaclass__ = CFuncPtrType

    _argtypes_ = None
    _restype_ = None
    _ffiargshape = 'P'
    _ffishape = 'P'
    _fficompositesize = None
    _needs_free = False

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
        self._objects = {keepalive_key(0):self}
        if isinstance(argument, int):
            self._buffer = _rawffi.Array('P').fromaddress(argument, 1)
            # XXX finish this one, we need to be able to jump there somehow
        elif callable(argument):
            self.callable = argument
            argtypes = [arg._ffiargshape for arg in self._argtypes_]
            restype = self._restype_
            if restype is not None:
                restype = restype._ffiargshape
            else:
                restype = 'O' # void
            self._ptr = _rawffi.CallbackPtr(self._wrap_callable(argument,
                                                                self.argtypes),
                                            argtypes, restype)
            self._needs_free = True
            self._buffer = self._ptr.byptr()
        elif isinstance(argument, tuple) and len(argument) == 2:
            import ctypes
            self.name, self.dll = argument
            if isinstance(self.dll, str):
                self.dll = ctypes.CDLL(self.dll)
            # we need to check dll anyway
            self._getfuncptr([], ctypes.c_int)
        elif argument is None:
            self._buffer = _rawffi.Array('P')(1)
            self._needs_free = True
            return # needed for test..
        else:
            raise TypeError("Unknown constructor %s" % (argument,))

    def _wrap_callable(self, to_call, argtypes):
        def f(*args):
            if argtypes:
                args = [argtype._CData_retval(argtype.from_address(arg)._buffer)
                        for argtype, arg in zip(argtypes, args)]
            return to_call(*args)
        return f
    
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
        args = self._wrap_args(argtypes, args)
        resbuffer = funcptr(*[arg._buffer for obj, arg in args])
        if restype is not None:
            return restype._CData_retval(resbuffer)

    def _getfuncptr(self, argtypes, restype):
        if restype is None:
            import ctypes
            restype = ctypes.c_int
        argshapes = [arg._ffiargshape for arg in argtypes]
        resshape = restype._ffiargshape
        return self.dll._handle.ptr(self.name, argshapes, resshape)

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
        except (UnicodeError, TypeError), e:
            raise ArgumentError(str(e))

    def __del__(self):
        if self._needs_free:
            self._buffer.free()
            self._buffer = None
            if hasattr(self, '_ptr'):
                self._ptr.free()
                self._ptr = None
                self._needs_free = False
