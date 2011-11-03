from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.gateway import unwrap_spec, NoneNotWrapped
from pypy.interpreter.typedef import (TypeDef, interp_attrproperty_w,
                                      GetSetProperty)
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.error import OperationError
from pypy.rpython.lltypesystem import rffi, lltype

Null = NoneNotWrapped

from pypy.module.oracle import roci, interp_error
from pypy.module.oracle.config import string_w, StringBuffer, MAX_STRING_CHARS
from pypy.module.oracle.interp_environ import Environment
from pypy.module.oracle.interp_cursor import W_Cursor
from pypy.module.oracle.interp_pool import W_SessionPool
from pypy.module.oracle.interp_variable import VT_String

class W_Connection(Wrappable):
    def __init__(self):
        self.commitMode = roci.OCI_DEFAULT
        self.environment = None
        self.autocommit = False

        self.sessionHandle = lltype.nullptr(roci.OCISession.TO)
        self.serverHandle = lltype.nullptr(roci.OCIServer.TO)

        self.w_inputTypeHandler = None
        self.w_outputTypeHandler = None

        self.w_version = None
        self.release = False


    @unwrap_spec(mode=int, handle=int,
                 threaded=bool, twophase=bool, events=bool,
                 purity=bool)
    def descr_new(space, w_subtype,
                  w_user=NoneNotWrapped,
                  w_password=NoneNotWrapped,
                  w_dsn=NoneNotWrapped,
                  mode=roci.OCI_DEFAULT,
                  handle=0,         # XXX should be a ptr type
                  w_pool=Null,
                  threaded=False,
                  twophase=False,
                  events=False,
                  w_cclass=Null,
                  purity=0,
                  w_newpassword=Null):
        self = space.allocate_instance(W_Connection, w_subtype)
        W_Connection.__init__(self)

        # set up the environment
        if w_pool:
            pool = space.interp_w(W_SessionPool, w_pool)
            self.environment = pool.environment.clone()
        else:
            pool = None
            self.environment = Environment.create(space, threaded, events)

        self.w_username = w_user
        self.w_password = w_password
        self.w_tnsentry = w_dsn

        # perform some parsing, if necessary
        if (self.w_username and not self.w_password and
            space.is_true(space.contains(self.w_username, space.wrap('/')))):
            (self.w_username, self.w_password) = space.listview(
                space.call_method(self.w_username, 'split',
                                  space.wrap('/'), space.wrap(1)))

        if (self.w_password and not self.w_tnsentry and
            space.is_true(space.contains(self.w_password, space.wrap('@')))):
            (self.w_password, self.w_tnsentry) = space.listview(
                space.call_method(self.w_password, 'split',
                                  space.wrap('@'), space.wrap(1)))

        if pool or w_cclass is not None:
            self.getConnection(space, pool, w_cclass, purity)
        else:
            self.connect(space, mode, twophase)
        return space.wrap(self)

    def __del__(self):
        self.enqueue_for_destruction(self.environment.space,
                                     W_Connection.destructor,
                                     '__del__ method of ')

    def destructor(self):
        assert isinstance(self, W_Connection)
        if self.release:
            roci.OCITransRollback(
                self.handle, self.environment.errorHandle,
                roci.OCI_DEFAULT)
            roci.OCISessionRelease(
                self.handle, self.environment.errorHandle,
                None, 0, roci.OCI_DEFAULT)
        else:
            if self.sessionHandle:
                roci.OCITransRollback(
                    self.handle, self.environment.errorHandle,
                    roci.OCI_DEFAULT)
                roci.OCISessionEnd(
                    self.handle, self.environment.errorHandle,
                    self.sessionHandle, roci.OCI_DEFAULT)
            if self.serverHandle:
                roci.OCIServerDetach(
                    self.serverHandle, self.environment.errorHandle,
                    roci.OCI_DEFAULT)

    def connect(self, space, mode, twophase):
        stringBuffer = StringBuffer()

        # allocate the server handle
        handleptr = lltype.malloc(rffi.CArrayPtr(roci.OCIServer).TO,
                                  1, flavor='raw')
        try:
            status = roci.OCIHandleAlloc(
                self.environment.handle,
                handleptr, roci.OCI_HTYPE_SERVER, 0,
                lltype.nullptr(rffi.CArray(roci.dvoidp)))
            self.environment.checkForError(
                status, "Connection_Connect(): allocate server handle")
            self.serverHandle = handleptr[0]
        finally:
            lltype.free(handleptr, flavor='raw')

        # attach to the server
        stringBuffer.fill(space, self.w_tnsentry)
        try:
            status = roci.OCIServerAttach(
                self.serverHandle,
                self.environment.errorHandle,
                stringBuffer.ptr, stringBuffer.size,
                roci.OCI_DEFAULT)
            self.environment.checkForError(
                status, "Connection_Connect(): server attach")
        finally:
            stringBuffer.clear()

        # allocate the service context handle
        handleptr = lltype.malloc(rffi.CArrayPtr(roci.OCISvcCtx).TO,
                                  1, flavor='raw')

        try:
            status = roci.OCIHandleAlloc(
                self.environment.handle,
                handleptr, roci.OCI_HTYPE_SVCCTX, 0,
                lltype.nullptr(rffi.CArray(roci.dvoidp)))
            self.environment.checkForError(
                status, "Connection_Connect(): allocate service context handle")
            self.handle = handleptr[0]
        finally:
            lltype.free(handleptr, flavor='raw')

        # set attribute for server handle
        status = roci.OCIAttrSet(
            self.handle, roci.OCI_HTYPE_SVCCTX,
            self.serverHandle, 0,
            roci.OCI_ATTR_SERVER,
            self.environment.errorHandle)
        self.environment.checkForError(
            status, "Connection_Connect(): set server handle")

        # set the internal and external names; these are needed for global
        # transactions but are limited in terms of the lengths of the strings
        if twophase:
            status = roci.OCIAttrSet(
                self.serverHandle, roci.OCI_HTYPE_SERVER,
                "cx_Oracle", 0,
                roci.OCI_ATTR_INTERNAL_NAME,
                self.environment.errorHandle)
            self.environment.checkForError(
                status, "Connection_Connect(): set internal name")
            status = roci.OCIAttrSet(
                self.serverHandle, roci.OCI_HTYPE_SERVER,
                "cx_Oracle", 0,
                roci.OCI_ATTR_EXTERNAL_NAME,
                self.environment.errorHandle)
            self.environment.checkForError(
                status, "Connection_Connect(): set external name")

        # allocate the session handle
        handleptr = lltype.malloc(rffi.CArrayPtr(roci.OCISession).TO,
                                  1, flavor='raw')
        try:
            status = roci.OCIHandleAlloc(
                self.environment.handle,
                handleptr, roci.OCI_HTYPE_SESSION, 0,
                lltype.nullptr(rffi.CArray(roci.dvoidp)))
            self.environment.checkForError(
                status, "Connection_Connect(): allocate session handle")
            self.sessionHandle = handleptr[0]
        finally:
            lltype.free(handleptr, flavor='raw')

        credentialType = roci.OCI_CRED_EXT

        # set user name in session handle
        stringBuffer.fill(space, self.w_username)
        try:
            if stringBuffer.size > 0:
                credentialType = roci.OCI_CRED_RDBMS
                status = roci.OCIAttrSet(
                    self.sessionHandle,
                    roci.OCI_HTYPE_SESSION,
                    stringBuffer.ptr, stringBuffer.size,
                    roci.OCI_ATTR_USERNAME,
                    self.environment.errorHandle)
                self.environment.checkForError(
                    status, "Connection_Connect(): set user name")
        finally:
            stringBuffer.clear()

        # set password in session handle
        stringBuffer.fill(space, self.w_password)
        try:
            if stringBuffer.size > 0:
                credentialType = roci.OCI_CRED_RDBMS
                status = roci.OCIAttrSet(
                    self.sessionHandle,
                    roci.OCI_HTYPE_SESSION,
                    stringBuffer.ptr, stringBuffer.size,
                    roci.OCI_ATTR_PASSWORD,
                    self.environment.errorHandle)
                self.environment.checkForError(
                    status, "Connection_Connect(): set password")
        finally:
            stringBuffer.clear()

        # set the session handle on the service context handle
        status = roci.OCIAttrSet(
            self.handle, roci.OCI_HTYPE_SVCCTX,
            self.sessionHandle, 0,
            roci.OCI_ATTR_SESSION,
            self.environment.errorHandle)
        self.environment.checkForError(
            status, "Connection_Connect(): set session handle")
    
        # if a new password has been specified, change it which will also
        # establish the session

        # begin the session
        status = roci.OCISessionBegin(
            self.handle, self.environment.errorHandle,
            self.sessionHandle, credentialType, mode)
        try:
            self.environment.checkForError(
                status, "Connection_Connect(): begin session")
        except:
            self.sessionHandle = lltype.nullptr(roci.OCISession.TO)
            raise

    def getConnection(self, space, pool, w_cclass, purity):
        """Get a connection using the OCISessionGet() interface
        rather than using the low level interface for connecting."""

        proxyCredentials = False
        authInfo = lltype.nullptr(roci.OCIAuthInfo.TO)

        if pool:
            w_dbname = pool.w_name
            mode = roci.OCI_SESSGET_SPOOL
            if not pool.homogeneous and pool.w_username and self.w_username:
                proxyCredentials = space.is_true(space.ne(pool.w_username, self.w_username))
                mode |= roci.OCI_SESSGET_CREDPROXY
        else:
            w_dbname = self.w_tnsentry
            mode = roci.OCI_SESSGET_STMTCACHE

        stringBuffer = StringBuffer()

        # set up authorization handle, if needed
        if not pool or w_cclass or proxyCredentials:
            # create authorization handle
            handleptr = lltype.malloc(rffi.CArrayPtr(roci.OCIAuthInfo).TO,
                                      1, flavor='raw')
            try:
                status = roci.OCIHandleAlloc(
                    self.environment.handle,
                    handleptr,
                    roci.OCI_HTYPE_AUTHINFO,
                    0, lltype.nullptr(rffi.CArray(roci.dvoidp)))
                self.environment.checkForError(
                    status, "Connection_GetConnection(): allocate handle")

                authInfo = handleptr[0]
            finally:
                lltype.free(handleptr, flavor='raw')

            externalCredentials = True

            # set the user name, if applicable
            stringBuffer.fill(space, self.w_username)
            try:
                if stringBuffer.size > 0:
                    externalCredentials = False
                    status = roci.OCIAttrSet(
                        authInfo,
                        roci.OCI_HTYPE_AUTHINFO,
                        stringBuffer.ptr, stringBuffer.size,
                        roci.OCI_ATTR_USERNAME,
                        self.environment.errorHandle)
                    self.environment.checkForError(
                        status, "Connection_GetConnection(): set user name")
            finally:
                stringBuffer.clear()

            # set the password, if applicable
            stringBuffer.fill(space, self.w_password)
            try:
                if stringBuffer.size > 0:
                    externalCredentials = False
                    status = roci.OCIAttrSet(
                        authInfo,
                        roci.OCI_HTYPE_AUTHINFO,
                        stringBuffer.ptr, stringBuffer.size,
                        roci.OCI_ATTR_PASSWORD,
                        self.environment.errorHandle)
                    self.environment.checkForError(
                        status, "Connection_GetConnection(): set password")
            finally:
                stringBuffer.clear()

            # if no user name or password are set, using external credentials
            if not pool and externalCredentials:
                mode |= roci.OCI_SESSGET_CREDEXT

            # set the connection class, if applicable
            if roci.OCI_ATTR_CONNECTION_CLASS is not None:
                stringBuffer.fill(space, w_cclass)
                try:
                    if stringBuffer.size > 0:
                        externalCredentials = False
                        status = roci.OCIAttrSet(
                            authInfo,
                            roci.OCI_HTYPE_AUTHINFO,
                            stringBuffer.ptr, stringBuffer.size,
                            roci.OCI_ATTR_CONNECTION_CLASS,
                            self.environment.errorHandle)
                        self.environment.checkForError(
                            status,
                            "Connection_GetConnection(): set connection class")
                finally:
                    stringBuffer.clear()

            # set the purity, if applicable
            if (roci.OCI_ATTR_PURITY is not None
                and purity != roci.OCI_ATTR_PURITY_DEFAULT):
                purityptr = lltype.malloc(rffi.CArrayPtr(roci.ub4).TO,
                                          1, flavor='raw')
                purityptr[0] = rffi.cast(roci.ub4, purity)
                try:
                    status = roci.OCIAttrSet(
                        authInfo,
                        roci.OCI_HTYPE_AUTHINFO,
                        rffi.cast(roci.dvoidp, purityptr),
                        rffi.sizeof(roci.ub4),
                        roci.OCI_ATTR_PURITY,
                        self.environment.errorHandle)
                    self.environment.checkForError(
                        status, "Connection_GetConnection(): set purity")
                finally:
                    lltype.free(purityptr, flavor='raw')

        # acquire the new session
        stringBuffer.fill(space, w_dbname)
        foundptr = lltype.malloc(rffi.CArrayPtr(roci.boolean).TO,
                                 1, flavor='raw')
        handleptr = lltype.malloc(rffi.CArrayPtr(roci.OCISvcCtx).TO,
                                  1, flavor='raw')
        try:
            status = roci.OCISessionGet(
                self.environment.handle,
                self.environment.errorHandle,
                handleptr,
                authInfo,
                stringBuffer.ptr, stringBuffer.size,
                None, 0,
                lltype.nullptr(roci.Ptr(roci.oratext).TO),
                lltype.nullptr(roci.Ptr(roci.ub4).TO),
                foundptr,
                mode)
            self.environment.checkForError(
                status, "Connection_GetConnection(): get connection")

            self.handle = handleptr[0]
        finally:
            stringBuffer.clear()
            lltype.free(foundptr, flavor='raw')
            lltype.free(handleptr, flavor='raw')

        # eliminate the authorization handle immediately, if applicable
        if authInfo:
            roci.OCIHandleFree(authInfo, roci.OCI_HTYPE_AUTHINFO)

        # copy members in the case where a pool is being used
        if pool:
            if not proxyCredentials:
                self.w_username = pool.w_username
                self.w_password = pool.w_password
            self.w_tnsentry = pool.w_tnsentry
            self.sessionPool = pool

        self.release = True

    def _checkConnected(self, space):
        if not self.handle:
            raise OperationError(
                interp_error.get(space).w_InterfaceError,
                space.wrap("not connected"))

    def close(self, space):
        # make sure we are actually connnected
        self._checkConnected(space)

        # perform a rollback
        status = roci.OCITransRollback(
            self.handle, self.environment.errorHandle,
            roci.OCI_DEFAULT)
        self.environment.checkForError(
            status, "Connection_Close(): rollback")

        # logoff of the server
        if self.sessionHandle:
            status = roci.OCISessionEnd(
                self.handle, self.environment.errorHandle,
                self.sessionHandle, roci.OCI_DEFAULT)
            self.environment.checkForError(
                status, "Connection_Close(): end session")
            roci.OCIHandleFree(self.handle, roci.OCI_HTYPE_SVCCTX)

        self.handle = lltype.nullptr(roci.OCISvcCtx.TO)

    def commit(self, space):
        # make sure we are actually connected
        self._checkConnected(space)

        status = roci.OCITransCommit(
            self.handle, self.environment.errorHandle,
            self.commitMode)
        self.environment.checkForError(
            status, "Connection_Commit()")

        self.commitMode = roci.OCI_DEFAULT

    def rollback(self, space):
        # make sure we are actually connected
        self._checkConnected(space)

        status = roci.OCITransRollback(
            self.handle, self.environment.errorHandle,
            roci.OCI_DEFAULT)
        self.environment.checkForError(
            status, "Connection_Rollback()")

    def newCursor(self, space):
        return space.wrap(W_Cursor(space, self))

    def _getCharacterSetName(self, space, attribute):
        # get character set id
        charsetIdPtr = lltype.malloc(rffi.CArrayPtr(roci.ub2).TO,
                                  1, flavor='raw')
        try:
            status = roci.OCIAttrGet(
                self.environment.handle, roci.OCI_HTYPE_ENV,
                rffi.cast(roci.dvoidp, charsetIdPtr),
                lltype.nullptr(roci.Ptr(roci.ub4).TO),
                attribute,
                self.environment.errorHandle)
            self.environment.checkForError(
                status, "Connection_GetCharacterSetName(): get charset id")
            charsetId = charsetIdPtr[0]
        finally:
            lltype.free(charsetIdPtr, flavor='raw')

        # get character set name
        charsetname_buf, charsetname = rffi.alloc_buffer(roci.OCI_NLS_MAXBUFSZ)
        try:
            status = roci.OCINlsCharSetIdToName(
                self.environment.handle,
                charsetname_buf, roci.OCI_NLS_MAXBUFSZ,
                charsetId)
            self.environment.checkForError(
                status,
                "Connection_GetCharacterSetName(): get Oracle charset name")

            ianacharset_buf, ianacharset = rffi.alloc_buffer(
                roci.OCI_NLS_MAXBUFSZ)

            try:
                # get IANA character set name
                status = roci.OCINlsNameMap(
                    self.environment.handle,
                    ianacharset_buf, roci.OCI_NLS_MAXBUFSZ,
                    charsetname_buf, roci.OCI_NLS_CS_ORA_TO_IANA)
                self.environment.checkForError(
                    status,
                    "Connection_GetCharacterSetName(): translate NLS charset")
                charset = rffi.charp2str(ianacharset_buf)
            finally:
                rffi.keep_buffer_alive_until_here(ianacharset_buf, ianacharset)
        finally:
            rffi.keep_buffer_alive_until_here(charsetname_buf, charsetname)
        return space.wrap(charset)

    def get_encoding(self, space):
        return self._getCharacterSetName(space, roci.OCI_ATTR_ENV_CHARSET_ID)
    def get_nationalencoding(self, space):
        return self._getCharacterSetName(space, roci.OCI_ATTR_ENV_CHARSET_ID)
    def get_maxbytespercharacter(self, space):
        return space.wrap(self.environment.maxBytesPerCharacter)

    def get_version(self, space):
        # if version has already been determined, no need to determine again
        if self.w_version:
            return self.w_version

        # allocate a cursor to retrieve the version
        cursor = W_Cursor(space, self)

        # allocate version and compatibility variables
        versionVar = VT_String(cursor, cursor.arraySize, MAX_STRING_CHARS)
        compatVar = VT_String(cursor, cursor.arraySize, MAX_STRING_CHARS)

        # call stored procedure
        cursor._call(space, "dbms_utility.db_version",
                     None, space.newlist([space.wrap(versionVar),
                                          space.wrap(compatVar)]))

        # retrieve value
        self.w_version = versionVar.getValue(space, 0)
        return self.w_version

W_Connection.typedef = TypeDef(
    "Connection",
    __new__ = interp2app(W_Connection.descr_new.im_func),
    username = interp_attrproperty_w('w_username', W_Connection),
    password = interp_attrproperty_w('w_password', W_Connection),
    tnsentry = interp_attrproperty_w('w_tnsentry', W_Connection),

    close = interp2app(W_Connection.close),
    commit = interp2app(W_Connection.commit),
    rollback = interp2app(W_Connection.rollback),

    cursor = interp2app(W_Connection.newCursor),

    encoding = GetSetProperty(W_Connection.get_encoding),
    nationalencoding = GetSetProperty(W_Connection.get_nationalencoding),
    maxBytesPerCharacter = GetSetProperty(W_Connection.get_maxbytespercharacter),
    version = GetSetProperty(W_Connection.get_version),
    )
