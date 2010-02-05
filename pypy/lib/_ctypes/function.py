
from _ctypes.basics import _CData, _CDataMeta, cdata_from_address
from _ctypes.basics import ArgumentError, keepalive_key
import _rawffi
import sys
import traceback

# XXX this file needs huge refactoring I fear

PARAMFLAG_FIN   = 0x1
PARAMFLAG_FOUT  = 0x2
PARAMFLAG_FLCID = 0x4
def get_com_error(errcode, riid, pIunk):
    "Win32 specific: build a COM Error exception"
    # XXX need C support code
    from _ctypes import COMError
    return COMError(errcode, None, None)

class CFuncPtrType(_CDataMeta):
    # XXX write down here defaults and such things

    def _sizeofinstances(self):
        return _rawffi.sizeof('P')

    def _alignmentofinstances(self):
        return _rawffi.alignment('P')

    def _is_pointer_like(self):
        return True

    from_address = cdata_from_address

class CFuncPtr(_CData):
    __metaclass__ = CFuncPtrType

    _argtypes_ = None
    _restype_ = None
    _flags_ = 0
    _ffiargshape = 'P'
    _ffishape = 'P'
    _fficompositesize = None
    _ffiarray = _rawffi.Array('P')
    _needs_free = False
    callable = None
    _ptr = None
    _buffer = None
    # win32 COM properties
    _paramflags = None
    _com_index = None
    _com_iid = None

    def _getargtypes(self):
        return self._argtypes_
    def _setargtypes(self, argtypes):
        self._ptr = None
        self._argtypes_ = argtypes    
    argtypes = property(_getargtypes, _setargtypes)

    def _getrestype(self):
        return self._restype_
    def _setrestype(self, restype):
        self._ptr = None
        from ctypes import c_char_p
        if restype is int:
            from ctypes import c_int
            restype = c_int
        if not isinstance(restype, _CDataMeta) and not restype is None and \
               not callable(restype):
            raise TypeError("Expected ctypes type, got %s" % (restype,))
        self._restype_ = restype
    def _delrestype(self):
        self._ptr = None
        del self._restype_
    restype = property(_getrestype, _setrestype, _delrestype)

    def _ffishapes(self, args, restype):
        argtypes = [arg._ffiargshape for arg in args]
        if restype is not None:
            restype = restype._ffiargshape
        else:
            restype = 'O' # void
        return argtypes, restype

    def __init__(self, *args):
        self.name = None
        self._objects = {keepalive_key(0):self}
        self._needs_free = True
        argument = None
        if len(args) == 1:
            argument = args[0]

        if isinstance(argument, (int, long)):
            # direct construction from raw address
            ffiargs, ffires = self._ffishapes(self._argtypes_, self._restype_)
            self._ptr = _rawffi.FuncPtr(argument, ffiargs, ffires,
                                        self._flags_)
            self._buffer = self._ptr.byptr()
        elif callable(argument):
            # A callback into python
            self.callable = argument
            ffiargs, ffires = self._ffishapes(self._argtypes_, self._restype_)
            self._ptr = _rawffi.CallbackPtr(self._wrap_callable(argument,
                                                                self.argtypes),
                                            ffiargs, ffires, self._flags_)
            self._buffer = self._ptr.byptr()
        elif isinstance(argument, tuple) and len(argument) == 2:
            # function exported from a shared library
            import ctypes
            self.name, self.dll = argument
            if isinstance(self.dll, str):
                self.dll = ctypes.CDLL(self.dll)
            # we need to check dll anyway
            ptr = self._getfuncptr([], ctypes.c_int)
            self._buffer = ptr.byptr()

        elif (sys.platform == 'win32' and
              len(args) >= 2 and isinstance(args[0], (int, long))):
            # A COM function call, by index
            ffiargs, ffires = self._ffishapes(self._argtypes_, self._restype_)
            self._com_index =  args[0] + 0x1000
            self.name = args[1]
            if len(args) > 2:
                self._paramflags = args[2]
            # XXX ignored iid = args[3]

        elif len(args) == 0:
            # Empty function object.
            # this is needed for casts
            self._buffer = _rawffi.Array('P')(1)
            return
        else:
            raise TypeError("Unknown constructor %s" % (args,))

    def _wrap_callable(self, to_call, argtypes):
        def f(*args):
            if argtypes:
                args = [argtype._CData_retval(argtype.from_address(arg)._buffer)
                        for argtype, arg in zip(argtypes, args)]
            return to_call(*args)
        return f
    
    def __call__(self, *args):
        if self.callable is not None:
            try:
                res = self.callable(*args)
            except:
                exc_info = sys.exc_info()
                traceback.print_tb(exc_info[2], file=sys.stderr)
                print >>sys.stderr, "%s: %s" % (exc_info[0].__name__, exc_info[1])
                return 0
            if self._restype_ is not None:
                return res
            return
        argtypes = self._argtypes_

        if self._com_index:
            from ctypes import cast, c_void_p, POINTER
            thisarg = cast(args[0], POINTER(POINTER(c_void_p))).contents
            argtypes = [c_void_p] + list(argtypes)
            args = list(args)
            args[0] = args[0].value
        else:
            thisarg = None
            
        if argtypes is None:
            argtypes = self._guess_argtypes(args)
        argtypes, argsandobjs = self._wrap_args(argtypes, args)
        
        restype = self._restype_
        funcptr = self._getfuncptr(argtypes, restype, thisarg)
        resbuffer = funcptr(*[arg._buffer for _, arg in argsandobjs])
        return self._build_result(restype, resbuffer, argtypes, argsandobjs)

    def _getfuncptr(self, argtypes, restype, thisarg=None):
        if self._ptr is not None:
            return self._ptr
        if restype is None or not isinstance(restype, _CDataMeta):
            import ctypes
            restype = ctypes.c_int
        argshapes = [arg._ffiargshape for arg in argtypes]
        resshape = restype._ffiargshape
        if self._buffer is not None:
            ptr = _rawffi.FuncPtr(self._buffer[0], argshapes, resshape,
                                  self._flags_)
            if argtypes is self._argtypes_:
                self._ptr = ptr
            return ptr

        if self._com_index:
            # extract the address from the object's virtual table
            if not thisarg:
                raise ValueError("COM method call without VTable")
            ptr = thisarg[self._com_index - 0x1000]
            return _rawffi.FuncPtr(ptr, argshapes, resshape, self._flags_)
        
        cdll = self.dll._handle
        try:
            return cdll.ptr(self.name, argshapes, resshape, self._flags_)
        except AttributeError:
            if self._flags_ & _rawffi.FUNCFLAG_CDECL:
                raise

            # For stdcall, try mangled names:
            # funcname -> _funcname@<n>
            # where n is 0, 4, 8, 12, ..., 128
            for i in range(33):
                mangled_name = "_%s@%d" % (self.name, i*4)
                try:
                    return cdll.ptr(mangled_name, argshapes, resshape,
                                    self._flags_)
                except AttributeError:
                    pass
            raise

    @staticmethod
    def _guess_argtypes(args):
        from _ctypes import _CData
        from ctypes import c_char_p, c_wchar_p, c_void_p, c_int
        from ctypes import Array, Structure
        res = []
        for arg in args:
            if hasattr(arg, '_as_parameter_'):
                arg = arg._as_parameter_
            if isinstance(arg, str):
                res.append(c_char_p)
            elif isinstance(arg, unicode):
                res.append(c_wchar_p)
            elif isinstance(arg, _CData):
                res.append(type(arg))
            elif arg is None:
                res.append(c_void_p)
            #elif arg == 0:
            #    res.append(c_void_p)
            elif isinstance(arg, (int, long)):
                res.append(c_int)
            else:
                raise TypeError("Don't know how to handle %s" % (arg,))
        return res

    def _wrap_args(self, argtypes, args):
        wrapped_args = []
        consumed = 0
        for i, argtype in enumerate(argtypes):
            defaultvalue = None
            if i > 0 and self._paramflags is not None:
                paramflag = self._paramflags[i-1]
                if len(paramflag) == 2:
                    idlflag, name = paramflag
                elif len(paramflag) == 3:
                    idlflag, name, defaultvalue = paramflag
                else:
                    idlflag = 0
                idlflag &= (PARAMFLAG_FIN | PARAMFLAG_FOUT | PARAMFLAG_FLCID)

                if idlflag in (0, PARAMFLAG_FIN):
                    pass
                elif idlflag == PARAMFLAG_FOUT:
                    import ctypes
                    val = argtype._type_()
                    wrapped = (val, ctypes.byref(val))
                    wrapped_args.append(wrapped)
                    continue
                elif idlflag == PARAMFLAG_FIN | PARAMFLAG_FLCID:
                    # Always taken from defaultvalue if given,
                    # else the integer 0.
                    val = defaultvalue
                    if val is None:
                        val = 0
                    wrapped = argtype._CData_input(val)
                    wrapped_args.append(wrapped)
                    continue
                else:
                    raise NotImplementedError(
                        "paramflags = %s" % (self._paramflags[i-1],))

            if consumed < len(args):
                arg = args[consumed]
            elif defaultvalue is not None:
                arg = defaultvalue
            else:
                raise TypeError("Not enough arguments")

            try:
                wrapped = argtype._CData_input(arg)
            except (UnicodeError, TypeError), e:
                raise ArgumentError(str(e))
            wrapped_args.append(wrapped)
            consumed += 1

        if len(wrapped_args) < len(args):
            extra = args[len(wrapped_args):]
            extra_types = self._guess_argtypes(extra)
            for arg, argtype in zip(extra, extra_types):
                try:
                    wrapped = argtype._CData_input(arg)
                except (UnicodeError, TypeError), e:
                    raise ArgumentError(str(e))
                wrapped_args.append(wrapped)
            argtypes = list(argtypes) + extra_types
        return argtypes, wrapped_args

    def _build_result(self, restype, resbuffer, argtypes, argsandobjs):
        """Build the function result:
           If there is no OUT parameter, return the actual function result
           If there is one OUT parameter, return it
           If there are many OUT parameters, return a tuple"""

        retval = None

        if self._com_index:
            if resbuffer[0] & 0x80000000:
                raise get_com_error(resbuffer[0],
                                    self._com_iid, argsandobjs[0][0])
            else:
                retval = int(resbuffer[0])
        elif restype is not None:
            checker = getattr(self.restype, '_check_retval_', None)
            if checker:
                val = restype(resbuffer[0])
                # the original ctypes seems to make the distinction between
                # classes defining a new type, and their subclasses
                if '_type_' in restype.__dict__:
                    val = val.value
                retval = checker(val)
            elif not isinstance(restype, _CDataMeta):
                retval = restype(resbuffer[0])
            else:
                retval = restype._CData_retval(resbuffer)

        results = []
        if self._paramflags:
            for argtype, (obj, _), paramflag in zip(argtypes[1:], argsandobjs[1:],
                                                    self._paramflags):
                if len(paramflag) == 2:
                    idlflag, name = paramflag
                elif len(paramflag) == 3:
                    idlflag, name, defaultvalue = paramflag
                else:
                    idlflag = 0
                idlflag &= (PARAMFLAG_FIN | PARAMFLAG_FOUT | PARAMFLAG_FLCID)

                if idlflag in (0, PARAMFLAG_FIN):
                    pass
                elif idlflag == PARAMFLAG_FOUT:
                    val = obj.__ctypes_from_outparam__()
                    results.append(val)
                elif idlflag == PARAMFLAG_FIN | PARAMFLAG_FLCID:
                    pass
                else:
                    raise NotImplementedError(
                        "paramflags = %s" % (paramflag,))

        if results:
            if len(results) == 1:
                return results[0]
            else:
                return tuple(results)

        # No output parameter, return the actual function result.
        return retval

    def __del__(self):
        if self._needs_free:
            # XXX we need to find a bad guy here
            if self._buffer is None:
                return
            self._buffer.free()
            self._buffer = None
            if isinstance(self._ptr, _rawffi.CallbackPtr):
                self._ptr.free()
                self._ptr = None
            self._needs_free = False
