
from _ctypes.basics import _CData, _CDataMeta, cdata_from_address
from _ctypes.primitive import SimpleType, _SimpleCData
from _ctypes.basics import ArgumentError, keepalive_key
from _ctypes.basics import shape_to_ffi_type, is_struct_shape
from _ctypes.builtin import set_errno, set_last_error
import _rawffi
import _ffi
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
    _errcheck_ = None
    _flags_ = 0
    _ffiargshape = 'P'
    _ffishape = 'P'
    _fficompositesize = None
    _ffiarray = _rawffi.Array('P')
    _needs_free = False
    callable = None
    _ptr = None
    _buffer = None
    _address = None
    # win32 COM properties
    _paramflags = None
    _com_index = None
    _com_iid = None

    def _getargtypes(self):
        return self._argtypes_
    def _setargtypes(self, argtypes):
        self._ptr = None
        if argtypes is None:
            self._argtypes_ = None
        else:
            for i, argtype in enumerate(argtypes):
                if not hasattr(argtype, 'from_param'):
                    raise TypeError(
                        "item %d in _argtypes_ has no from_param method" % (
                            i + 1,))
            self._argtypes_ = argtypes
    argtypes = property(_getargtypes, _setargtypes)

    def _getrestype(self):
        return self._restype_
    def _setrestype(self, restype):
        self._ptr = None
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

    def _geterrcheck(self):
        return getattr(self, '_errcheck_', None)
    def _seterrcheck(self, errcheck):
        if not callable(errcheck):
            raise TypeError("The errcheck attribute must be callable")
        self._errcheck_ = errcheck
    def _delerrcheck(self):
        try:
            del self._errcheck_
        except AttributeError:
            pass
    errcheck = property(_geterrcheck, _seterrcheck, _delerrcheck)

    def _ffishapes(self, args, restype):
        argtypes = [arg._ffiargshape for arg in args]
        if restype is not None:
            if not isinstance(restype, SimpleType):
                raise TypeError("invalid result type for callback function")
            restype = restype._ffiargshape
        else:
            restype = 'O' # void
        return argtypes, restype

    def _set_address(self, address):
        if not self._buffer:
            self._buffer = _rawffi.Array('P')(1)
        self._buffer[0] = address

    def _get_address(self):
        return self._buffer[0]

    def __init__(self, *args):
        self.name = None
        self._objects = {keepalive_key(0):self}
        self._needs_free = True
        argument = None
        if len(args) == 1:
            argument = args[0]

        if isinstance(argument, (int, long)):
            # direct construction from raw address
            self._set_address(argument)
            argshapes, resshape = self._ffishapes(self._argtypes_, self._restype_)
            self._ptr = self._getfuncptr_fromaddress(argshapes, resshape)
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
            self._set_address(ptr.getaddr())

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
            self._set_address(0)
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
            if len(args) == len(self._argtypes_):
                pass
            elif self._flags_ & _rawffi.FUNCFLAG_CDECL:
                if len(args) < len(self._argtypes_):
                    plural = len(self._argtypes_) > 1 and "s" or ""
                    raise TypeError(
                        "This function takes at least %d argument%s (%s given)"
                        % (len(self._argtypes_), plural, len(args)))
                else:
                    # For cdecl functions, we allow more actual arguments
                    # than the length of the argtypes tuple.
                    args = args[:len(self._argtypes_)]
            else:
                plural = len(self._argtypes_) > 1 and "s" or ""
                raise TypeError(
                    "This function takes %d argument%s (%s given)"
                    % (len(self._argtypes_), plural, len(args)))

            # check that arguments are convertible
            # XXX: uncomment me, but right now it makes a lot of tests failing :-(
            #self._convert_args(self._argtypes_, args)

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
            assert False, 'TODO2'
            from ctypes import cast, c_void_p, POINTER
            thisarg = cast(args[0], POINTER(POINTER(c_void_p))).contents
            argtypes = [c_void_p] + list(argtypes)
            args = list(args)
            args[0] = args[0].value
        else:
            thisarg = None
            
        if argtypes is None:
            argtypes = []
        args = self._convert_args(argtypes, args)
        argtypes = [type(arg) for arg in args]
        newargs = self._unwrap_args(argtypes, args)

        restype = self._restype_
        funcptr = self._getfuncptr(argtypes, restype, thisarg)
        if self._flags_ & _rawffi.FUNCFLAG_USE_ERRNO:
            set_errno(_rawffi.get_errno())
        if self._flags_ & _rawffi.FUNCFLAG_USE_LASTERROR:
            set_last_error(_rawffi.get_last_error())
        try:
            result = funcptr(*newargs)
            ## resbuffer = funcptr(*[arg._get_buffer_for_param()._buffer
            ##                       for arg in args])
        finally:
            if self._flags_ & _rawffi.FUNCFLAG_USE_ERRNO:
                set_errno(_rawffi.get_errno())
            if self._flags_ & _rawffi.FUNCFLAG_USE_LASTERROR:
                set_last_error(_rawffi.get_last_error())
        result = self._build_result(restype, result, argtypes, newargs)

        # The 'errcheck' protocol
        if self._errcheck_:
            v = self._errcheck_(result, self, args)
            # If the errcheck funtion failed, let it throw
            # If the errcheck function returned callargs unchanged,
            # continue normal processing.
            # If the errcheck function returned something else,
            # use that as result.
            if v is not args:
                result = v

        return result

    def _getfuncptr_fromaddress(self, argshapes, resshape):
        address = self._get_address()
        ffiargs = [shape_to_ffi_type(shape) for shape in argshapes]
        ffires = shape_to_ffi_type(resshape)
        return _ffi.FuncPtr.fromaddr(address, '', ffiargs, ffires)

    def _getfuncptr(self, argtypes, restype, thisarg=None):
        if self._ptr is not None and argtypes is self._argtypes_:
            return self._ptr
        if restype is None or not isinstance(restype, _CDataMeta):
            import ctypes
            restype = ctypes.c_int
        argshapes = [arg._ffiargshape for arg in argtypes]
        resshape = restype._ffiargshape
        if self._buffer is not None:
            ptr = self._getfuncptr_fromaddress(argshapes, resshape)
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
            #return cdll.ptr(self.name, argshapes, resshape, self._flags_)
            ffi_argtypes = [shape_to_ffi_type(shape) for shape in argshapes]
            ffi_restype = shape_to_ffi_type(resshape)
            self._ptr = cdll.getfunc(self.name, ffi_argtypes, ffi_restype)
            return self._ptr
        except AttributeError:
            if self._flags_ & _rawffi.FUNCFLAG_CDECL:
                raise

            # For stdcall, try mangled names:
            # funcname -> _funcname@<n>
            # where n is 0, 4, 8, 12, ..., 128
            for i in range(33):
                mangled_name = "_%s@%d" % (self.name, i*4)
                try:
                    return cdll.getfunc(mangled_name,
                                        ffi_argtypes, ffi_restype,
                                        # XXX self._flags_
                                        )
                except AttributeError:
                    pass
            raise

    @staticmethod
    def _conv_param(argtype, arg, index):
        from ctypes import c_char_p, c_wchar_p, c_void_p, c_int
        if argtype is not None:
            arg = argtype.from_param(arg)
        if hasattr(arg, '_as_parameter_'):
            arg = arg._as_parameter_

        if isinstance(arg, _CData):
            # The usual case when argtype is defined
            cobj = arg
        elif isinstance(arg, str):
            cobj = c_char_p(arg)
        elif isinstance(arg, unicode):
            cobj = c_wchar_p(arg)
        elif arg is None:
            cobj = c_void_p()
        elif isinstance(arg, (int, long)):
            cobj = c_int(arg)
        else:
            raise TypeError("Don't know how to handle %s" % (arg,))

        return cobj

    def _convert_args(self, argtypes, args):
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
                    wrapped = self._conv_param(argtype, val, consumed)
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
                wrapped = self._conv_param(argtype, arg, consumed)
            except (UnicodeError, TypeError, ValueError), e:
                raise ArgumentError(str(e))
            wrapped_args.append(wrapped)
            consumed += 1

        if len(wrapped_args) < len(args):
            extra = args[len(wrapped_args):]
            argtypes = list(argtypes)
            for i, arg in enumerate(extra):
                try:
                    wrapped = self._conv_param(None, arg, i)
                except (UnicodeError, TypeError, ValueError), e:
                    raise ArgumentError(str(e))
                wrapped_args.append(wrapped)
        return wrapped_args


    def _unwrap_args(self, argtypes, args):
        """
        Convert from ctypes high-level values to low-level values suitables to
        be passed to _ffi
        """
        assert len(argtypes) == len(args)
        newargs = []
        for argtype, arg in zip(argtypes, args):
            shape = argtype._ffiargshape
            if isinstance(shape, str) and shape in "POszZ": # pointer types
                value = arg._get_buffer_value()
            elif is_struct_shape(shape):
                value = arg._buffer
            else:
                value = arg.value
            newargs.append(value)
        return newargs
    
    def _wrap_result(self, restype, result):
        """
        Convert from low-level repr of the result to the high-level python
        one.
        """
        # hack for performance: if restype is a "simple" primitive type, don't
        # allocate the buffer because it's going to be thrown away immediately
        if restype.__bases__[0] is _SimpleCData and not restype._is_pointer_like():
            return result
        #
        shape = restype._ffishape
        if is_struct_shape(shape):
            buf = result
        else:
            buf = _rawffi.Array(shape)(1, autofree=True)
            buf[0] = result
        retval = restype._CData_retval(buf)
        return retval

    def _build_result(self, restype, result, argtypes, argsandobjs):
        """Build the function result:
           If there is no OUT parameter, return the actual function result
           If there is one OUT parameter, return it
           If there are many OUT parameters, return a tuple"""

        # XXX: note for the future: the function used to take a "resbuffer",
        # i.e. an array of ints. Now it takes a result, which is already a
        # python object. All places that do "resbuffer[0]" should check that
        # result is actually an int and just use it.
        #
        # Also, argsandobjs used to be "args" in __call__, now it's "newargs"
        # (i.e., the already unwrapped objects). It's used only when we have a
        # PARAMFLAG_FOUT and it's probably wrong, I'll fix it when I find a
        # failing test

        retval = None

        if self._com_index:
            if resbuffer[0] & 0x80000000:
                raise get_com_error(resbuffer[0],
                                    self._com_iid, argsandobjs[0])
            else:
                retval = int(resbuffer[0])
        elif restype is not None:
            checker = getattr(self.restype, '_check_retval_', None)
            if checker:
                val = restype(result)
                # the original ctypes seems to make the distinction between
                # classes defining a new type, and their subclasses
                if '_type_' in restype.__dict__:
                    val = val.value
                retval = checker(val)
            elif not isinstance(restype, _CDataMeta):
                retval = restype(result)
            else:
                retval = self._wrap_result(restype, result)

        results = []
        if self._paramflags:
            for argtype, obj, paramflag in zip(argtypes[1:], argsandobjs[1:],
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

    def __nonzero__(self):
        return bool(self._buffer[0])

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
