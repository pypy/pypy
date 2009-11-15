from pypy.rpython.lltypesystem import rffi, lltype
from pypy.module.oracle import roci, config
from pypy.interpreter.error import OperationError

from pypy.module.oracle.interp_error import W_Error, get

class Environment:
    def __init__(self, space, threaded, events):
        self.space = space
        mode = roci.OCI_OBJECT
        if threaded:
            mode |= roci.OCI_THREADED
        if events:
            mode |= roci.OCI_EVENTS

        handleptr = lltype.malloc(rffi.CArrayPtr(roci.OCIEnv).TO,
                                  1, flavor='raw')

        try:

            status = roci.OCIEnvNlsCreate(
                handleptr, mode,
                None,
                lltype.nullptr(lltype.FuncType(     # malocfp
                    [roci.dvoidp, roci.size_t], roci.dvoidp)),
                lltype.nullptr(lltype.FuncType(     # ralocfp
                    [roci.dvoidp, roci.dvoidp, roci.size_t], roci.dvoidp)),
                lltype.nullptr(lltype.FuncType(     # mfreefp
                    [roci.dvoidp, roci.dvoidp], lltype.Void)),
                0, lltype.nullptr(rffi.CArray(roci.dvoidp)),
                config.CHARSETID, config.CHARSETID)

            if not handleptr[0] or status not in (roci.OCI_SUCCESS,
                                                  roci.OCI_SUCCESS_WITH_INFO):
                raise OperationError(
                    get(self.space).w_InterfaceError,
                    self.space.wrap(
                        "Unable to acquire Oracle environment handle"))

            self.handle = handleptr[0]
        finally:
            lltype.free(handleptr, flavor='raw')


        self.maxBytesPerCharacter = config.BYTES_PER_CHAR
        self.maxStringBytes = config.BYTES_PER_CHAR * config.MAX_STRING_CHARS

        # create the error handle
        handleptr = lltype.malloc(rffi.CArrayPtr(roci.OCIError).TO,
                                  1, flavor='raw')
        try:
            status = roci.OCIHandleAlloc(
                self.handle,
                handleptr, roci.OCI_HTYPE_ERROR, 0,
                lltype.nullptr(rffi.CArray(roci.dvoidp)))
            self.checkForError(
                status, "Environment_New(): create error handle")
            self.errorHandle = handleptr[0]
        finally:
            lltype.free(handleptr, flavor='raw')


    def checkForError(self, status, context):
        if status in (roci.OCI_SUCCESS, roci.OCI_SUCCESS_WITH_INFO):
            return
        
        if status != roci.OCI_INVALID_HANDLE:
            # At this point it is assumed that the Oracle
            # environment is fully initialized
            error = W_Error(self.space, self, context, 1)
            if error.code in (1, 1400, 2290, 2291, 2292):
                w_type = get(self.space).w_IntegrityError
            elif error.code in (1012, 1033, 1034, 1089, 3113, 3114,
                                12203, 12500, 12571):
                w_type = get(self.space).w_OperationalError
            else:
                w_type = get(self.space).w_DatabaseError
            raise OperationError(w_type, self.space.wrap(error))

        error = W_Error(self.space, self, context, 0)
        error.code = 0
        error.message = self.space.wrap("Invalid handle!")
        raise OperationError(get(self.space).w_DatabaseError,
                             self.space.wrap(error))
