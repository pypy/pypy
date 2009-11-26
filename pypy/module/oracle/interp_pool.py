from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.gateway import ObjSpace, W_Root, NoneNotWrapped
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.typedef import TypeDef, GetSetProperty
from pypy.interpreter.typedef import interp_attrproperty, interp_attrproperty_w
from pypy.rpython.lltypesystem import rffi, lltype

Null = NoneNotWrapped

from pypy.module.oracle import roci, config, interp_error, interp_environ


class W_SessionPool(Wrappable):
    def __init__(self):
        self.environment = None

    def descr_new(space, w_subtype,
                  w_user, w_password, w_dsn,
                  min, max, increment,
                  w_connectiontype=Null,
                  threaded=False,
                  getmode=roci.OCI_SPOOL_ATTRVAL_NOWAIT,
                  events=False,
                  homogeneous=True):
        self = space.allocate_instance(W_SessionPool, w_subtype)
        W_SessionPool.__init__(self)

        if w_connectiontype is not None:
            if not space.is_true(space.issubtype(w_value,
                                                 interp_connect.W_Connection)):
                raise OperationError(
                    interp_error.get(space).w_ProgrammingError,
                    space.wrap(
                        "connectiontype must be a subclass of Connection"))
        self.w_username = w_user
        self.w_password = w_password
        self.w_tnsentry = w_dsn

        self.w_connectionType = w_connectiontype
        self.minSessions = min
        self.maxSessions = max
        self.sessionIncrement = increment
        self.homogeneous = homogeneous

        # set up the environment
        self.environment = interp_environ.Environment(space, threaded, events)

        # create the session pool handle
        handleptr = lltype.malloc(rffi.CArrayPtr(roci.OCIServer).TO,
                                  1, flavor='raw')
        try:
            status = roci.OCIHandleAlloc(
                self.environment.handle,
                handleptr, roci.OCI_HTYPE_SPOOL, 0,
                lltype.nullptr(rffi.CArray(roci.dvoidp)))
            self.environment.checkForError(
                status, "SessionPool_New(): allocate handle")
            self.handle = handleptr[0]
        finally:
            lltype.free(handleptr, flavor='raw')

        # prepare pool mode
        poolMode = roci.OCI_SPC_STMTCACHE
        if self.homogeneous:
            poolMode |= roci.OCI_SPC_HOMOGENEOUS

        # create the session pool
        user_buf = config.StringBuffer()
        user_buf.fill(space, self.w_username)
        password_buf = config.StringBuffer()
        password_buf.fill(space, self.w_password)
        dsn_buf = config.StringBuffer()
        dsn_buf.fill(space, self.w_tnsentry)
        poolnameptr = lltype.malloc(rffi.CArrayPtr(roci.oratext).TO, 1,
                                    flavor='raw')
        poolnamelenptr = lltype.malloc(rffi.CArrayPtr(roci.ub4).TO, 1,
                                       flavor='raw')

        try:
            status = roci.OCISessionPoolCreate(
                self.environment.handle,
                self.environment.errorHandle,
                self.handle,
                poolnameptr, poolnamelenptr,
                dsn_buf.ptr, dsn_buf.size,
                min, max, increment,
                user_buf.ptr, user_buf.size,
                password_buf.ptr, password_buf.size,
                poolMode)
            self.environment.checkForError(
                status, "SessionPool_New(): create pool")

            self.w_name = config.w_string(space, poolnameptr[0],
                                          poolnamelenptr[0])
        finally:
            user_buf.clear()
            password_buf.clear()
            dsn_buf.clear()

        return space.wrap(self)
    descr_new.unwrap_spec = [ObjSpace, W_Root,
                             W_Root, W_Root, W_Root,
                             int, int, int,
                             W_Root,
                             bool, int, bool, bool]

    def checkConnected(self, space):
        if not self.handle:
            raise OperationError(
                get(space).w_InterfaceError,
                space.wrap("not connected"))

def computedProperty(oci_attr_code, oci_value_type):
    def fget(space, self):
        self.checkConnected(space)

        valueptr = lltype.malloc(rffi.CArrayPtr(oci_value_type).TO,
                                 1, flavor='raw')
        try:
            status = roci.OCIAttrGet(
                self.handle, roci.OCI_HTYPE_SPOOL,
                rffi.cast(roci.dvoidp, valueptr),
                lltype.nullptr(roci.Ptr(roci.ub4).TO),
                oci_attr_code,
                self.environment.errorHandle)
            return space.wrap(valueptr[0])
        finally:
            lltype.free(valueptr, flavor='raw')
    return GetSetProperty(fget)

W_SessionPool.typedef = TypeDef(
    "SessionPool",
    __new__ = interp2app(W_SessionPool.descr_new.im_func),
    username = interp_attrproperty_w('w_username', W_SessionPool),
    password = interp_attrproperty_w('w_password', W_SessionPool),
    tnsentry = interp_attrproperty_w('w_tnsentry', W_SessionPool),
    min = interp_attrproperty('minSessions', W_SessionPool),
    max = interp_attrproperty('maxSessions', W_SessionPool),
    increment = interp_attrproperty('sessionIncrement', W_SessionPool),
    opened = computedProperty(roci.OCI_ATTR_SPOOL_OPEN_COUNT, roci.ub4),
    busy = computedProperty(roci.OCI_ATTR_SPOOL_BUSY_COUNT, roci.ub4),
    timeout = computedProperty(roci.OCI_ATTR_SPOOL_TIMEOUT, roci.ub4),
    getmode = computedProperty(roci.OCI_ATTR_SPOOL_GETMODE, roci.ub1),
    )
