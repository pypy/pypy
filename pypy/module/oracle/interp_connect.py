from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.gateway import ObjSpace, W_Root, NoneNotWrapped
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
from pypy.module.oracle.interp_variable import VT_String

class W_Connection(Wrappable):
    def __init__(self):
        self.commitMode = roci.OCI_DEFAULT
        self.environment = None
        self.autocommit = False

        self.inputTypeHandler = None
        self.outputTypeHandler = None

        self.w_version = None

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
                  purity=False,
                  w_newpassword=Null):
        self = space.allocate_instance(W_Connection, w_subtype)
        W_Connection.__init__(self)

        # set up the environment
        if w_pool:
            pool = space.instance_w(W_Pool, w_pool)
            self.environment = pool.environment.clone()
        else:
            self.environment = Environment(space, threaded, events)

        self.w_username = w_user
        self.w_password = w_password
        self.w_tnsentry = w_dsn

        # perform some parsing, if necessary
        if (self.w_username and not self.w_password and
            space.is_true(space.contains(self.w_username, space.wrap('/')))):
            (self.w_username, self.w_password) = space.unpackiterable(
                space.call_method(self.w_username, 'split',
                                  space.wrap('/'), space.wrap(1)))
            
        if (self.w_password and not self.w_tnsentry and
            space.is_true(space.contains(self.w_password, space.wrap('@')))):
            (self.w_password, self.w_tnsentry) = space.unpackiterable(
                space.call_method(self.w_password, 'split',
                                  space.wrap('@'), space.wrap(1)))

        self.connect(space, mode, twophase)
        return space.wrap(self)

    descr_new.unwrap_spec = [ObjSpace, W_Root,
                             W_Root, W_Root, W_Root,
                             int, int,
                             W_Root,
                             bool, bool, bool,
                             W_Root,
                             bool,
                             W_Root]
                                       
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
            self.sessionHandle = None
            raise

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

        self.handle = None
    close.unwrap_spec = ['self', ObjSpace]

    def commit(self, space):
        # make sure we are actually connected
        self._checkConnected(space)

        status = roci.OCITransCommit(
            self.handle, self.environment.errorHandle,
            self.commitMode)
        self.environment.checkForError(
            status, "Connection_Commit()")

        self.commitMode = roci.OCI_DEFAULT
    commit.unwrap_spec = ['self', ObjSpace]

    def rollback(self, space):
        # make sure we are actually connected
        self._checkConnected(space)

        status = roci.OCITransRollback(
            self.handle, self.environment.errorHandle,
            self.OCI_DEFAULT)
        self.environment.checkForError(
            status, "Connection_Rollback()")
    rollback.unwrap_spec = ['self', ObjSpace]

    def newCursor(self, space):
        return space.wrap(W_Cursor(space, self))
    newCursor.unwrap_spec = ['self', ObjSpace]

    def _getCharacterSetName(self, space, attribute):
        # get character set id
        status = roci.OCIAttrGet(
            self.environment.handle, roci.HTYPE_ENV,
            charsetId, None,
            attribute,
            self.environment.errorHandle)
        self.environment.checkForError(
            status, "Connection_GetCharacterSetName(): get charset id")

        # get character set name
        status = roci.OCINlsCharsetIdToName(
            self.environmentHandle,
            charsetNameBuf.buf, charsetNameBuf.size,
            charsetIdPtr[0])
        self.environment.checkForError(
            status, "Connection_GetCharacterSetName(): get Oracle charset name")

        # get IANA character set name
        status = roci.OCINlsNameMap(
            self.environmentHandle,
            ianaCharsetNameBuf.buf, inaCharsetNameBuf.size,
            charsetNameBuf.buf, roci.OCI_NLS_CS_ORA_TO_IANA)
        self.environment.checkForError(
            status, "Connection_GetCharacterSetName(): translate NLS charset")

        return space.wrap(ianaCharsetName) 
        
    def get_encoding(space, self):
        return self._getCharacterSetName(space, roci.OCI_ATTR_ENV_CHARSET_ID)
    def get_nationalencoding(space, self):
        return self._getCharacterSetName(space, roci.OCI_ATTR_ENV_CHARSET_ID)

    def get_version(space, self):
        # if version has already been determined, no need to determine again
        if self.w_version:
            return self.w_version

        # allocate a cursor to retrieve the version
        cursor = self.newCursor(space)

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
    __new__ = interp2app(W_Connection.descr_new.im_func,
                         unwrap_spec=W_Connection.descr_new.unwrap_spec),
    username = interp_attrproperty_w('w_username', W_Connection),
    password = interp_attrproperty_w('w_password', W_Connection),
    tnsentry = interp_attrproperty_w('w_tnsentry', W_Connection),
    
    close = interp2app(W_Connection.close,
                       unwrap_spec=W_Connection.close.unwrap_spec),
    commit = interp2app(W_Connection.commit,
                       unwrap_spec=W_Connection.commit.unwrap_spec),
    rollback = interp2app(W_Connection.rollback,
                       unwrap_spec=W_Connection.rollback.unwrap_spec),

    cursor = interp2app(W_Connection.newCursor,
                        unwrap_spec=W_Connection.newCursor.unwrap_spec),

    encoding = GetSetProperty(W_Connection.get_encoding),
    nationalencoding = GetSetProperty(W_Connection.get_nationalencoding),
    version = GetSetProperty(W_Connection.get_version),
    )
