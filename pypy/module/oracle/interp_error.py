from pypy.interpreter.baseobjspace import Wrappable
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.typedef import interp_attrproperty, interp_attrproperty_w
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.error import OperationError

from pypy.module.oracle import roci, config
from pypy.rlib.unroll import unrolling_iterable

exported_names = unrolling_iterable("""
    DatabaseError OperationalError InterfaceError ProgrammingError
    NotSupportedError IntegrityError InternalError DataError
    Variable Connection""".split())

class State:
    # XXX move to another file

    def __init__(self, space):
        "NOT_RPYTHON"
        self.variableTypeByPythonType = {}
        self.w_DecimalType = None
        self.w_DateTimeType = None
        self.w_DateType = None
        self.w_TimedeltaType = None

        for name in exported_names:
            setattr(self, 'w_' + name, None)

    def startup(self, space):
        w_module = space.getbuiltinmodule('cx_Oracle')
        for name in exported_names:
            setattr(self, 'w_' + name, space.getattr(w_module, space.wrap(name)))

        from pypy.module.oracle.interp_variable import all_variable_types
        for varType in all_variable_types:
            w_type = space.gettypeobject(varType.typedef)
            self.variableTypeByPythonType[w_type] = varType

        (self.w_DecimalType,
         self.w_DateTimeType, self.w_DateType, self.w_TimedeltaType,
         ) = space.fixedview(space.appexec([], """():
             import decimal, datetime
             return (decimal.Decimal,
                     datetime.datetime, datetime.date, datetime.timedelta)
        """))

def get(space): 
    return space.fromcache(State) 

class W_Error(Wrappable):
    def __init__(self, space, environment, context, retrieveError):
        self.context = context
        if retrieveError:
            if environment.errorHandle:
                handle = environment.errorHandle
                handleType = roci.OCI_HTYPE_ERROR
            else:
                handle = environment.handle
                handleType = roci.OCI_HTYPE_ENV

            codeptr = lltype.malloc(rffi.CArray(roci.sb4), 1, flavor='raw')
            BUFSIZE = 1024
            textbuf, text = rffi.alloc_buffer(BUFSIZE)

            try:
                status = roci.OCIErrorGet(
                    handle, 1, lltype.nullptr(roci.oratext.TO), codeptr,
                    textbuf, BUFSIZE, handleType)
                if status != roci.OCI_SUCCESS:
                    raise OperationError(
                        get(space).w_InternalError,
                        space.wrap("No Oracle error?"))

                self.code = codeptr[0]
                self.w_message = config.w_string(space, textbuf)
            finally:
                lltype.free(codeptr, flavor='raw')
                rffi.keep_buffer_alive_until_here(textbuf, text)

            if config.WITH_UNICODE:
                # XXX remove double zeros at the end
                pass

    def desc_str(self):
        return self.w_message

W_Error.typedef = TypeDef(
    'Error',
    __str__ = interp2app(W_Error.desc_str),
    code = interp_attrproperty('code', W_Error),
    message = interp_attrproperty_w('w_message', W_Error))


