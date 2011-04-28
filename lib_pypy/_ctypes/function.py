import _rawffi
import sys
import traceback
import warnings

from _ctypes.basics import ArgumentError, keepalive_key
from _ctypes.basics import _CData, _CDataMeta, cdata_from_address
from _ctypes.builtin import set_errno, set_last_error
from _ctypes.primitive import SimpleType

# XXX this file needs huge refactoring I fear

PARAMFLAG_FIN   = 0x1
PARAMFLAG_FOUT  = 0x2
PARAMFLAG_FLCID = 0x4
PARAMFLAG_COMBINED = PARAMFLAG_FIN | PARAMFLAG_FOUT | PARAMFLAG_FLCID

VALID_PARAMFLAGS = (
    0,
    PARAMFLAG_FIN,
    PARAMFLAG_FIN | PARAMFLAG_FOUT,
    PARAMFLAG_FIN | PARAMFLAG_FLCID
    )

WIN64 = sys.platform == 'win32' and sys.maxint == 2**63 - 1

def get_com_error(errcode, riid, pIunk):
    "Win32 specific: build a COM Error exception"
    # XXX need C support code
    from _ctypes import COMError
    return COMError(errcode, None, None)

def call_function(func, args):
    "Only for debugging so far: So that we can call CFunction instances"
    funcptr = CFuncPtr(func)
    funcptr.restype = int
    return funcptr(*args)

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
    # win32 COM properties
    _paramflags = None
    _com_index = None
    _com_iid = None

    __restype_set = False

    def _getargtypes(self):
        return self._argtypes_

    def _setargtypes(self, argtypes):
        self._ptr = None
        if argtypes is None:
            self._argtypes_ = ()
        else:
            for i, argtype in enumerate(argtypes):
                if not hasattr(argtype, 'from_param'):
                    raise TypeError(
                        "item %d in _argtypes_ has no from_param method" % (
                            i + 1,))
            self._argtypes_ = argtypes

    argtypes = property(_getargtypes, _setargtypes)

    def _getparamflags(self):
        return self._paramflags

    def _setparamflags(self, paramflags):
        if paramflags is None or not self._argtypes_:
            self._paramflags = None
            return
        if not isinstance(paramflags, tuple):
            raise TypeError("paramflags must be a tuple or None")
        if len(paramflags) != len(self._argtypes_):
            raise ValueError("paramflags must have the same length as argtypes")
        for idx, paramflag in enumerate(paramflags):
            paramlen = len(paramflag)
            name = default = None
            if paramlen == 1:
                flag = paramflag[0]
            elif paramlen == 2:
                flag, name = paramflag
            elif paramlen == 3:
                flag, name, default = paramflag
            else:
                raise TypeError(
                    "paramflags must be a sequence of (int [,string [,value]]) "
                    "tuples"
                    )
            if not isinstance(flag, int):
                raise TypeError(
                    "paramflags must be a sequence of (int [,string [,value]]) "
                    "tuples"
                    )
            _flag = flag & PARAMFLAG_COMBINED
            if _flag == PARAMFLAG_FOUT:
                typ = self._argtypes_[idx]
                if getattr(typ, '_ffiargshape', None) not in ('P', 'z', 'Z'):
                    raise TypeError(
                        "'out' parameter %d must be a pointer type, not %s"
                        % (idx+1, type(typ).__name__)
                        )
            elif _flag not in VALID_PARAMFLAGS:
                raise TypeError("paramflag value %d not supported" % flag)
        self._paramflags = paramflags

    paramflags = property(_getparamflags, _setparamflags)

    def _getrestype(self):
        return self._restype_

    def _setrestype(self, restype):
        self.__restype_set = True
        self._ptr = None
        if restype is int:
            from ctypes import c_int
            restype = c_int
        if not (isinstance(restype, _CDataMeta) or restype is None or
                callable(restype)):
            raise TypeError("restype must be a type, a callable, or None")
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
        if args is None:
            args = []
        argtypes = [arg._ffiargshape for arg in args]
        if restype is not None:
            if not isinstance(restype, SimpleType):
                raise TypeError("invalid result type for callback function")
            restype = restype._ffiargshape
        else:
            restype = 'O' # void
        return argtypes, restype

    def __init__(self, *args):
        self.name = None
        self._objects = {keepalive_key(0):self}
        self._needs_free = True

        # Empty function object -- this is needed for casts
        if not args:
            self._buffer = _rawffi.Array('P')(1)
            return

        argsl = list(args)
        argument = argsl.pop(0)

        # Direct construction from raw address
        if isinstance(argument, (int, long)) and not argsl:
            ffiargs, ffires = self._ffishapes(self._argtypes_, self._restype_)
            self._ptr = _rawffi.FuncPtr(argument, ffiargs, ffires, self._flags_)
            self._buffer = self._ptr.byptr()
            return

        # A callback into Python
        if callable(argument) and not argsl:
            self.callable = argument
            ffiargs, ffires = self._ffishapes(self._argtypes_, self._restype_)
            if self._restype_ is None:
                ffires = None
            self._ptr = _rawffi.CallbackPtr(self._wrap_callable(
                argument, self.argtypes
                ), ffiargs, ffires, self._flags_)
            self._buffer = self._ptr.byptr()
            return

        # Function exported from a shared library
        if isinstance(argument, tuple) and len(argument) == 2:
            import ctypes
            self.name, dll = argument
            if isinstance(dll, str):
                self.dll = ctypes.CDLL(dll)
            else:
                self.dll = dll
            if argsl:
                self.paramflags = argsl.pop(0)
                if argsl:
                    raise TypeError("Unknown constructor %s" % (args,))
            # We need to check dll anyway
            ptr = self._getfuncptr([], ctypes.c_int)
            self._buffer = ptr.byptr()
            return

        # A COM function call, by index
        if (sys.platform == 'win32' and isinstance(argument, (int, long))
            and argsl):
            ffiargs, ffires = self._ffishapes(self._argtypes_, self._restype_)
            self._com_index =  argument + 0x1000
            self.name = argsl.pop(0)
            if argsl:
                self.paramflags = argsl.pop(0)
                if argsl:
                    self._com_iid = argsl.pop(0)
                    if argsl:
                        raise TypeError("Unknown constructor %s" % (args,))
            return

        raise TypeError("Unknown constructor %s" % (args,))

    def _wrap_callable(self, to_call, argtypes):
        def f(*args):
            if argtypes:
                args = [argtype._CData_retval(argtype.from_address(arg)._buffer)
                        for argtype, arg in zip(argtypes, args)]
            return to_call(*args)
        return f
    
    def __call__(self, *args, **kwargs):
        argtypes = self._argtypes_
        if self.callable is not None:
            if len(args) == len(argtypes):
                pass
            elif self._flags_ & _rawffi.FUNCFLAG_CDECL:
                if len(args) < len(argtypes):
                    plural = len(argtypes) > 1 and "s" or ""
                    raise TypeError(
                        "This function takes at least %d argument%s (%s given)"
                        % (len(argtypes), plural, len(args)))
                else:
                    # For cdecl functions, we allow more actual arguments
                    # than the length of the argtypes tuple.
                    args = args[:len(self._argtypes_)]
            else:
                plural = len(argtypes) > 1 and "s" or ""
                raise TypeError(
                    "This function takes %d argument%s (%s given)"
                    % (len(argtypes), plural, len(args)))

            # check that arguments are convertible
            ## XXX Not as long as ctypes.cast is a callback function with
            ## py_object arguments...
            ## self._convert_args(argtypes, args, {})

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

        if argtypes is None:
            warnings.warn('C function without declared arguments called',
                          RuntimeWarning, stacklevel=2)
            argtypes = []
            
        if not self.__restype_set:
            warnings.warn('C function without declared return type called',
                          RuntimeWarning, stacklevel=2)

        if self._com_index:
            from ctypes import cast, c_void_p, POINTER
            if not args:
                raise ValueError(
                    "native COM method call without 'this' parameter"
                    )
            thisarg = cast(args[0], POINTER(POINTER(c_void_p))).contents
            argtypes = [c_void_p] + list(argtypes)
            args = list(args)
            args[0] = args[0].value
        else:
            thisarg = None

        args, outargs = self._convert_args(argtypes, args, kwargs)
        argtypes = [type(arg) for arg in args]

        restype = self._restype_
        funcptr = self._getfuncptr(argtypes, restype, thisarg)
        if self._flags_ & _rawffi.FUNCFLAG_USE_ERRNO:
            set_errno(_rawffi.get_errno())
        if self._flags_ & _rawffi.FUNCFLAG_USE_LASTERROR:
            set_last_error(_rawffi.get_last_error())
        try:
            resbuffer = funcptr(*[arg._get_buffer_for_param()._buffer
                                  for arg in args])
        finally:
            if self._flags_ & _rawffi.FUNCFLAG_USE_ERRNO:
                set_errno(_rawffi.get_errno())
            if self._flags_ & _rawffi.FUNCFLAG_USE_LASTERROR:
                set_last_error(_rawffi.get_last_error())

        result = None
        if self._com_index:
            if resbuffer[0] & 0x80000000:
                raise get_com_error(resbuffer[0],
                                    self._com_iid, args[0])
            else:
                result = int(resbuffer[0])
        elif restype is not None:
            checker = getattr(self.restype, '_check_retval_', None)
            if checker:
                val = restype(resbuffer[0])
                # the original ctypes seems to make the distinction between
                # classes defining a new type, and their subclasses
                if '_type_' in restype.__dict__:
                    val = val.value
                result = checker(val)
            elif not isinstance(restype, _CDataMeta):
                result = restype(resbuffer[0])
            else:
                result = restype._CData_retval(resbuffer)

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

        if not outargs:
            return result

        if len(outargs) == 1:
            return outargs[0]

        return tuple(outargs)

    def _getfuncptr(self, argtypes, restype, thisarg=None):
        if self._ptr is not None and argtypes is self._argtypes_:
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
            # Win64 has no stdcall calling conv, so it should also not have the
            # name mangling of it.
            if WIN64:
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
    def _conv_param(argtype, arg):
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

    def _convert_args(self, argtypes, args, kwargs, marker=object()):
        callargs = []
        outargs = []
        total = len(args)
        paramflags = self._paramflags

        if self._com_index:
            inargs_idx = 1
        else:
            inargs_idx = 0

        if not paramflags and total < len(argtypes):
            raise TypeError("not enough arguments")

        for i, argtype in enumerate(argtypes):
            flag = 0
            name = None
            defval = marker
            if paramflags:
                paramflag = paramflags[i]
                paramlen = len(paramflag)
                name = None
                if paramlen == 1:
                    flag = paramflag[0]
                elif paramlen == 2:
                    flag, name = paramflag
                elif paramlen == 3:
                    flag, name, defval = paramflag
                flag = flag & PARAMFLAG_COMBINED
                if flag == PARAMFLAG_FIN | PARAMFLAG_FLCID:
                    val = defval
                    if val is marker:
                        val = 0
                    wrapped = self._conv_param(argtype, val)
                    callargs.append(wrapped)
                elif flag in (0, PARAMFLAG_FIN):
                    if inargs_idx < total:
                        val = args[inargs_idx]
                        inargs_idx += 1
                    elif kwargs and name in kwargs:
                        val = kwargs[name]
                        inargs_idx += 1
                    elif defval is not marker:
                        val = defval
                    elif name:
                        raise TypeError("required argument '%s' missing" % name)
                    else:
                        raise TypeError("not enough arguments")
                    wrapped = self._conv_param(argtype, val)
                    callargs.append(wrapped)
                elif flag == PARAMFLAG_FOUT:
                    if defval is not marker:
                        outargs.append(defval)
                        wrapped = self._conv_param(argtype, defval)
                    else:
                        import ctypes
                        val = argtype._type_()
                        outargs.append(val)
                        wrapped = ctypes.byref(val)
                    callargs.append(wrapped)
                else:
                    raise ValueError("paramflag %d not yet implemented" % flag)
            else:
                try:
                    wrapped = self._conv_param(argtype, args[i])
                except (UnicodeError, TypeError, ValueError), e:
                    raise ArgumentError(str(e))
                callargs.append(wrapped)
                inargs_idx += 1

        if len(callargs) < total:
            extra = args[len(callargs):]
            for i, arg in enumerate(extra):
                try:
                    wrapped = self._conv_param(None, arg)
                except (UnicodeError, TypeError, ValueError), e:
                    raise ArgumentError(str(e))
                callargs.append(wrapped)

        return callargs, outargs

    def __nonzero__(self):
        return self._com_index is not None or bool(self._buffer[0])

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
