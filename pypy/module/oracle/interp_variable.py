from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.typedef import interp_attrproperty
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.error import OperationError
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.rlib.rarithmetic import ovfcheck

import sys
from pypy.module.oracle import roci, config, transform
from pypy.module.oracle import interp_lob, interp_object
from pypy.module.oracle.interp_error import W_Error, get
from pypy.module.oracle.config import string_w, StringBuffer

def define(cursor, position, numElements):
    paramptr = lltype.malloc(roci.Ptr(roci.OCIParam).TO, 1, flavor='raw')
    try:
        status = roci.OCIParamGet(
            cursor.handle, roci.OCI_HTYPE_STMT,
            cursor.environment.errorHandle,
            paramptr, position)
        cursor.environment.checkForError(
            status,
            "Variable_Define(): parameter")

        param = paramptr[0]
    finally:
        lltype.free(paramptr, flavor='raw')

    # call the helper to do the actual work
    var = _defineHelper(cursor, param, position, numElements)

    roci.OCIDescriptorFree(param, roci.OCI_DTYPE_PARAM)

    return var

def _defineHelper(cursor, param, position, numElements):
    # determine data type
    varType = typeByOracleDescriptor(param, cursor.environment)
    if cursor.numbersAsStrings and varType is VT_Float:
        varType = VT_NumberAsString

    # retrieve size of the parameter
    size = varType.size
    if varType.isVariableLength:

        # determine the maximum length from Oracle
        attrptr = lltype.malloc(rffi.CArrayPtr(roci.ub2).TO, 1, flavor='raw')
        try:
            status = roci.OCIAttrGet(
                param, roci.OCI_HTYPE_DESCRIBE,
                rffi.cast(roci.dvoidp, attrptr),
                lltype.nullptr(roci.Ptr(roci.ub4).TO),
                roci.OCI_ATTR_DATA_SIZE,
                cursor.environment.errorHandle)

            cursor.environment.checkForError(
                status, "Variable_Define(): data size")
            sizeFromOracle = rffi.cast(lltype.Signed, attrptr[0])
        finally:
            lltype.free(attrptr, flavor='raw')

        # use the length from Oracle directly if available
        if sizeFromOracle:
            size = rffi.cast(lltype.Signed, sizeFromOracle)

        # otherwise, use the value set with the setoutputsize() parameter
        elif cursor.outputSize >= 0:
            if (cursor.outputSizeColumn < 0 or
                position == cursor.outputSizeColumn):
                size = cursor.outputSize

    # call the procedure to set values prior to define
    varType2 = varType.preDefine(varType, param, cursor.environment)

    # create a variable of the correct type
    if 0 and cursor.w_outputTypeHandler: # XXX
        var = newByOutputTypeHandler(
            cursor, param,
            cursor.w_outputTypeHandler,
            varType2, size, numElements)
    elif 0 and cursor.connection.w_outputTypeHandler: # XXX
        var = newByOutputTypeHandler(
            cursor, param,
            cursor.connection.w_outputTypeHandler,
            varType2, size, numElements)
    else:
        var = varType2(cursor, numElements, size)

    assert isinstance(var, W_Variable)

    # perform the define
    handleptr = lltype.malloc(roci.Ptr(roci.OCIDefine).TO, 1, flavor='raw')
    try:
        status = roci.OCIDefineByPos(
            cursor.handle,
            handleptr,
            var.environment.errorHandle,
            position,
            var.data, var.bufferSize,
            var.oracleType,
            rffi.cast(roci.dvoidp, var.indicator),
            var.actualLength,
            var.returnCode,
            roci.OCI_DEFAULT)
        var.environment.checkForError(
            status,
            "Variable_Define(): define")
        var.defineHandle = handleptr[0]
    finally:
        lltype.free(handleptr, flavor='raw')

    # call the procedure to set values after define
    var.postDefine(param)

    return var


class W_Variable(Wrappable):
    charsetForm = roci.SQLCS_IMPLICIT
    isVariableLength = False
    canBeInArray = True

    def __init__(self, cursor, numElements, size=0):
        self.environment = cursor.environment
        self.boundCursorHandle = lltype.nullptr(roci.OCIStmt.TO)
        self.boundName = None
        self.boundPos = 0
        self.isArray = False
        self.actualElementsPtr = lltype.malloc(roci.Ptr(roci.ub4).TO, 1,
                                               zero=True, flavor='raw')

        if numElements < 1:
            self.allocatedElements = 1
        else:
            self.allocatedElements = numElements
        self.internalFetchNum = 0
        self.actualLength = lltype.nullptr(rffi.CArrayPtr(roci.ub2).TO)
        self.returnCode = lltype.nullptr(rffi.CArrayPtr(roci.ub2).TO)

        # set the maximum length of the variable, ensure that a minimum of
        # 2 bytes is allocated to ensure that the array size check works
        if self.isVariableLength:
            size = max(size, rffi.sizeof(roci.ub2))
            if self.size != size:
                self.size = size

        # allocate the data for the variable
        self.allocateData(self.environment.space)

        # allocate the indicator for the variable
        self.indicator = lltype.malloc(rffi.CArrayPtr(roci.sb2).TO,
                                       self.allocatedElements,
                                       flavor='raw', zero=True)

        # ensure that all variable values start out NULL
        for i in range(self.allocatedElements):
            self.indicator[i] = rffi.cast(roci.sb2, roci.OCI_IND_NULL)

        # for variable length data, also allocate the return code
        if self.isVariableLength:
            self.returnCode = lltype.malloc(rffi.CArrayPtr(roci.ub2).TO,
                                            self.allocatedElements,
                                            flavor='raw', zero=True)

        # perform extended initialization
        self.initialize(self.environment.space, cursor)

    def __del__(self):
        self.finalize()
        lltype.free(self.actualElementsPtr, flavor='raw')
        if self.actualLength:
            lltype.free(self.actualLength, flavor='raw')
        if self.data:
            lltype.free(self.data, flavor='raw')
        if self.returnCode:
            lltype.free(self.returnCode, flavor='raw')
        if self.indicator:
            lltype.free(self.indicator, flavor='raw')

    def getBufferSize(self):
        return self.size

    def allocateData(self, space):
        # set the buffer size for the variable
        self.bufferSize = self.getBufferSize()

        # allocate the data as long as it is small enough
        try:
            dataLength = ovfcheck(self.allocatedElements * self.bufferSize)
        except OverflowError:
            too_large = True
        else:
            too_large = False

        if too_large or dataLength >= roci.INT_MAX:
            raise OperationError(
                space.w_ValueError,
                space.wrap("array size too large"))

        self.data = lltype.malloc(rffi.CCHARP.TO, int(dataLength),
                                  flavor='raw', zero=True)

    def resize(self, space, size):
        # allocate the data for the new array
        orig_data = self.data
        orig_size = self.bufferSize
        self.size = size
        self.allocateData(space)

        # copy the data from the original array to the new array
        for i in range(self.allocatedElements):
            for j in range(orig_size):
                self.data[self.bufferSize * i + j] = \
                                          orig_data[orig_size * i + j]

        lltype.free(orig_data, flavor='raw')

        # force rebinding
        if self.boundName or self.boundPos:
            self._internalBind(space)

    def makeArray(self, space):
        if not self.canBeInArray:
            raise OperationError(
                get(space).w_NotSupportedError,
                space.wrap(
                    "Variable_MakeArray(): type does not support arrays"))
        self.isArray = True

    def initialize(self, space, cursor):
        pass

    def finalize(self):
        pass

    @staticmethod
    def preDefine(cls, param, environment):
        return cls

    def postDefine(self, param):
        pass

    def bind(self, space, cursor, w_name, pos):
        # nothing to do if already bound
        if (cursor.handle == self.boundCursorHandle and
            w_name == self.w_boundName and pos == self.boundPos):
            return

        # set the instance variables specific for binding
        self.boundCursorHandle = cursor.handle
        self.boundPos = pos
        self.w_boundName = w_name

        # perform the bind
        self._internalBind(space)

    def _internalBind(self, space):
        bindHandlePtr = lltype.malloc(roci.Ptr(roci.OCIBind).TO, 1,
                                      flavor='raw')
        if self.isArray:
            allocatedElements = self.allocatedElements
            actualElementsPtr = self.actualElementsPtr
        else:
            allocatedElements = 0
            actualElementsPtr = lltype.nullptr(roci.Ptr(roci.ub4).TO)

        try:
            if self.w_boundName:
                nameBuffer = config.StringBuffer()
                nameBuffer.fill(space, self.w_boundName)
                status = roci.OCIBindByName(
                    self.boundCursorHandle, bindHandlePtr,
                    self.environment.errorHandle,
                    nameBuffer.ptr, nameBuffer.size,
                    self.data, self.bufferSize,
                    self.oracleType,
                    rffi.cast(roci.dvoidp, self.indicator),
                    self.actualLength, self.returnCode,
                    allocatedElements, actualElementsPtr,
                    roci.OCI_DEFAULT)
            else:
                status = roci.OCIBindByPos(
                    self.boundCursorHandle, bindHandlePtr,
                    self.environment.errorHandle,
                    self.boundPos,
                    self.data, self.bufferSize,
                    self.oracleType,
                    rffi.cast(roci.dvoidp, self.indicator),
                    self.actualLength, self.returnCode,
                    allocatedElements, actualElementsPtr,
                    roci.OCI_DEFAULT)

            self.environment.checkForError(
                status, "NumberVar_InternalBind()")
            self.bindHandle = bindHandlePtr[0]
        finally:
            lltype.free(bindHandlePtr, flavor='raw')

        # set the charset form and id if applicable
        if self.charsetForm != roci.SQLCS_IMPLICIT:
            charsetformptr = lltype.malloc(roci.Ptr(roci.ub1).TO, 1,
                                           zero=True, flavor='raw')
            charsetformptr[0] = rffi.cast(roci.ub1, self.charsetForm)
            try:
                status = roci.OCIAttrSet(
                    self.bindHandle, roci.OCI_HTYPE_BIND,
                    rffi.cast(roci.dvoidp, charsetformptr), 0,
                    roci.OCI_ATTR_CHARSET_FORM,
                    self.environment.errorHandle)
                self.environment.checkForError(
                    status, "NumberVar_InternalBind(): set charset form")
            finally:
                lltype.free(charsetformptr, flavor='raw')

            charsetidptr = lltype.malloc(roci.Ptr(roci.ub2).TO, 1,
                                         zero=True, flavor='raw')
            charsetidptr[0] = rffi.cast(roci.ub2, roci.OCI_UTF16ID)
            try:
                status = roci.OCIAttrSet(
                    self.bindHandle, roci.OCI_HTYPE_BIND,
                    rffi.cast(roci.dvoidp, charsetidptr), 0,
                    roci.OCI_ATTR_CHARSET_ID,
                    self.environment.errorHandle)
                self.environment.checkForError(
                    status, "NumberVar_InternalBind(): set charset Id")
            finally:
                lltype.free(charsetidptr, flavor='raw')

        # set the max data size for strings
        buffersizeptr = lltype.malloc(roci.Ptr(roci.ub4).TO, 1,
                                      zero=True, flavor='raw')
        buffersizeptr[0] = rffi.cast(roci.ub4, self.size)
        try:
            status = roci.OCIAttrSet(
                self.bindHandle, roci.OCI_HTYPE_BIND,
                rffi.cast(roci.dvoidp, buffersizeptr), 0,
                roci.OCI_ATTR_MAXDATA_SIZE,
                self.environment.errorHandle)
            self.environment.checkForError(
                status, "NumberVar_InternalBind(): set max data size")
        finally:
            lltype.free(buffersizeptr, flavor='raw')


    def isNull(self, pos):
        return (rffi.cast(lltype.Signed, self.indicator[pos])
                ==
                rffi.cast(lltype.Signed, roci.OCI_IND_NULL))

    def verifyFetch(self, space, pos):
        # Verifies that truncation or other problems did not take place on
        # retrieve.
        if self.isVariableLength:
            if rffi.cast(lltype.Signed, self.returnCode[pos]) != 0:
                error = W_Error(space, self.environment,
                                "Variable_VerifyFetch()", 0)
                error.code = self.returnCode[pos]
                error.message = space.wrap(
                    "column at array pos %d fetched with error: %d" %
                    (pos,
                     rffi.cast(lltype.Signed, self.returnCode[pos])))
                w_error = get(space).w_DatabaseError

                raise OperationError(get(space).w_DatabaseError,
                                     space.wrap(error))

    def getSingleValue(self, space, pos):
        # ensure we do not exceed the number of allocated elements
        if pos >= self.allocatedElements:
            raise OperationError(
                space.w_IndexError,
                space.wrap("Variable_GetSingleValue: array size exceeded"))

        # check for a NULL value
        if self.isNull(pos):
            return space.wrap(None)

        # check for truncation or other problems on retrieve
        self.verifyFetch(space, pos)

        # calculate value to return
        value = self.getValueProc(space, pos)
        # XXX outConverter
        return value

    def getArrayValue(self, space, numElements):
        return space.newlist(
            [self.getSingleValue(space, i)
             for i in range(numElements)])

    @unwrap_spec(pos=int)
    def getValue(self, space, pos=0):
        if self.isArray:
            return self.getArrayValue(space, self.actualElementsPtr[0])
        return self.getSingleValue(space, pos)

    def setSingleValue(self, space, pos, w_value):
        # ensure we do not exceed the number of allocated elements
        if pos >= self.allocatedElements:
            raise OperationError(
                space.w_IndexError,
                space.wrap("Variable_SetSingleValue: array size exceeded"))

        # convert value, if necessary
        # XXX inConverter

        # check for a NULL value
        if space.is_w(w_value, space.w_None):
            self.indicator[pos] = roci.OCI_IND_NULL
            return

        self.indicator[pos] = roci.OCI_IND_NOTNULL
        if self.isVariableLength:
            self.returnCode[pos] = rffi.cast(roci.ub2, 0)

        self.setValueProc(space, pos, w_value)

    def setArrayValue(self, space, w_value):
        # ensure we have an array to set
        if not space.is_true(space.isinstance(w_value, space.w_list)):
            raise OperationError(
                space.w_TypeError,
                space.wrap("expecting array data"))

        elements_w = space.listview(w_value)

        # ensure we haven't exceeded the number of allocated elements
        if len(elements_w) > self.allocatedElements:
            raise OperationError(
                space.w_IndexError,
                space.wrap("Variable_SetArrayValue: array size exceeded"))

        # set all of the values
        self.actualElementsPtr[0] = rffi.cast(roci.ub4, len(elements_w))
        for i in range(len(elements_w)):
            self.setSingleValue(space, i, elements_w[i])

    @unwrap_spec(pos=int)
    def setValue(self, space, pos, w_value):
        if self.isArray:
            self.setArrayValue(space, w_value)
        else:
            self.setSingleValue(space, pos, w_value)


W_Variable.typedef = TypeDef(
    'Variable',
    getvalue = interp2app(W_Variable.getValue),
    setvalue = interp2app(W_Variable.setValue),

    maxlength  = interp_attrproperty('bufferSize', W_Variable),
    bufferSize = interp_attrproperty('bufferSize', W_Variable),
    size = interp_attrproperty('size', W_Variable),
    )

class VT_String(W_Variable):
    oracleType = roci.SQLT_CHR
    size = config.MAX_STRING_CHARS
    isVariableLength = True

    def getBufferSize(self):
        if config.WITH_UNICODE:
            return self.size * BYTES_PER_CHAR
        else:
            if self.charsetForm == roci.SQLCS_IMPLICIT:
                return self.size * self.environment.maxBytesPerCharacter
            else:
                return self.size * 2

    def initialize(self, space, cursor):
        self.actualLength = lltype.malloc(rffi.CArrayPtr(roci.ub2).TO,
                                          self.allocatedElements,
                                          zero=True, flavor='raw')

    def getValueProc(self, space, pos):
        offset = pos * self.bufferSize
        dataptr = rffi.ptradd(self.data, offset)
        length = rffi.cast(lltype.Signed, self.actualLength[pos])

        i = 0
        if config.WITH_UNICODE:
            if isinstance(self, VT_Binary):
                return space.wrap(rffi.charpsize2str(dataptr, length))
            else:
                l = []
                while i < length:
                    l.append(unichr((ord(dataptr[i + 1]) << 8) +
                                    ord(dataptr[i])))
                    i += 2
                return space.wrap(u''.join(l))
        else:
            if self.charsetForm == roci.SQLCS_IMPLICIT:
                return space.wrap(rffi.charpsize2str(dataptr, length))
            else:
                l = []
                while i < length:
                    l.append(unichr((ord(dataptr[i + 1]) << 8) +
                                    ord(dataptr[i])))
                    i += 2
                return space.wrap(u''.join(l))

    def setValueProc(self, space, pos, w_value):
        if config.WITH_UNICODE:
            wantBytes = not self.isCharacterData
        else:
            wantBytes = self.charsetForm == roci.SQLCS_IMPLICIT

        if wantBytes:
            if space.is_true(space.isinstance(w_value, space.w_str)):
                buf = config.StringBuffer()
                buf.fill(space, w_value)
                size = buf.size
            else:
                raise OperationError(
                    space.w_TypeError,
                    space.wrap("expecting string or buffer data"))
        else:
            if space.is_true(space.isinstance(w_value, space.w_unicode)):
                buf = config.StringBuffer()
                buf.fill_with_unicode(space, w_value)
                size = buf.size
            else:
                raise OperationError(
                    space.w_TypeError,
                    space.wrap("expecting unicode data"))

        try:
            if wantBytes:
                if buf.size > self.environment.maxStringBytes:
                    raise OperationError(
                        space.w_ValueError,
                        space.wrap("string data too large"))
            else:
                if buf.size > config.MAX_STRING_CHARS * 2:
                    raise OperationError(
                        space.w_ValueError,
                        space.wrap("unicode data too large"))

            # ensure that the buffer is large enough
            if buf.size > self.bufferSize:
                self.resize(space, size)

            # keep a copy of the string
            self.actualLength[pos] = rffi.cast(roci.ub2, buf.size)
            offset = pos * self.bufferSize
            for index in range(buf.size):
                self.data[offset + index] = buf.ptr[index]
        finally:
            buf.clear()

class VT_FixedChar(VT_String):
    oracleType = roci.SQLT_AFC
    size = 2000

class VT_NationalCharString(VT_String):
    charsetForm = roci.SQLCS_NCHAR

    def postDefine(self, param):
        charsetformptr = lltype.malloc(roci.Ptr(roci.ub1).TO, 1,
                                       zero=True, flavor='raw')
        charsetformptr[0] = rffi.cast(roci.ub1, self.charsetForm)
        try:
            status = roci.OCIAttrSet(
                self.defineHandle, roci.OCI_HTYPE_DEFINE,
                rffi.cast(roci.dvoidp, charsetformptr), 0,
                roci.OCI_ATTR_CHARSET_FORM,
                self.environment.errorHandle)
            self.environment.checkForError(
                status, "StringVar_PostDefine(): set charset form")
        finally:
            lltype.free(charsetformptr, flavor='raw')

        charsetidptr = lltype.malloc(roci.Ptr(roci.ub2).TO, 1,
                                     zero=True, flavor='raw')
        charsetidptr[0] = rffi.cast(roci.ub2, roci.OCI_UTF16ID)
        try:
            status = roci.OCIAttrSet(
                self.defineHandle, roci.OCI_HTYPE_DEFINE,
                rffi.cast(roci.dvoidp, charsetidptr), 0,
                roci.OCI_ATTR_CHARSET_ID,
                self.environment.errorHandle)
            self.environment.checkForError(
                status, "StringVar_PostDefine(): set charset Id")
        finally:
            lltype.free(charsetidptr, flavor='raw')


class VT_FixedNationalChar(VT_NationalCharString):
    oracleType = roci.SQLT_AFC
    size = 2000

class VT_LongString(W_Variable):
    oracleType = roci.SQLT_LVC
    isVariableLength = True
    size = 128 * 1024

    def getBufferSize(self):
        return self.size + rffi.sizeof(roci.ub4)

    def getValueProc(self, space, pos):
        ptr = rffi.ptradd(self.data, pos * self.bufferSize)
        length = rffi.cast(roci.Ptr(roci.ub4), ptr)[0]

        ptr = rffi.ptradd(ptr, rffi.sizeof(roci.ub4))
        return space.wrap(rffi.charpsize2str(ptr, length))

    def setValueProc(self, space, pos, w_value):
        buf = config.StringBuffer()
        buf.fill(space, w_value)

        try:
            # ensure that the buffer is large enough
            if buf.size + rffi.sizeof(roci.ub4) > self.bufferSize:
                self.resize(space, buf.size + rffi.sizeof(roci.ub4))

            # copy the string to the Oracle buffer
            ptr = rffi.ptradd(self.data, pos * self.bufferSize)
            rffi.cast(roci.Ptr(roci.ub4), ptr)[0] = rffi.cast(roci.ub4, buf.size)
            for index in range(buf.size):
                ptr[index + rffi.sizeof(roci.ub4)] = buf.ptr[index]
        finally:
            buf.clear()

class VT_Rowid(VT_String):
    oracleType = roci.SQLT_CHR
    size = 18
    isVariableLength = False

class VT_Binary(VT_String):
    oracleType = roci.SQLT_BIN
    size = config.MAX_BINARY_BYTES

class VT_LongBinary(VT_LongString):
    oracleType = roci.SQLT_LVB

class VT_NativeFloat(W_Variable):
    pass

class VT_Float(W_Variable):
    oracleType = roci.SQLT_VNU
    size = rffi.sizeof(roci.OCINumber)

    @staticmethod
    def preDefine(cls, param, environment):
        # if the return type has not already been specified, check to
        # see if the number can fit inside an integer by looking at
        # the precision and scale
        if cls is VT_Float:
            attrptr = lltype.malloc(rffi.CArrayPtr(roci.sb1).TO, 1,
                                    flavor='raw')
            try:
                status = roci.OCIAttrGet(
                    param, roci.OCI_HTYPE_DESCRIBE,
                    rffi.cast(roci.dvoidp, attrptr),
                    lltype.nullptr(roci.Ptr(roci.ub4).TO),
                    roci.OCI_ATTR_SCALE,
                    environment.errorHandle)
                environment.checkForError(
                    status,
                    "NumberVar_PreDefine(): scale")
                scale = rffi.cast(lltype.Signed, attrptr[0])
            finally:
                lltype.free(attrptr, flavor='raw')

            attrptr = lltype.malloc(rffi.CArrayPtr(roci.ub2).TO, 1,
                                    flavor='raw')
            try:
                status = roci.OCIAttrGet(
                    param, roci.OCI_HTYPE_DESCRIBE,
                    rffi.cast(roci.dvoidp, attrptr),
                    lltype.nullptr(roci.Ptr(roci.ub4).TO),
                    roci.OCI_ATTR_PRECISION,
                    environment.errorHandle)
                environment.checkForError(
                    status,
                    "NumberVar_PreDefine(): precision")
                precision = rffi.cast(lltype.Signed, attrptr[0])
            finally:
                lltype.free(attrptr, flavor='raw')

            if scale == 0 or (scale == -127 and precision == 0):
                if precision > 0 and precision < 10:
                    return VT_Integer
                else:
                    return VT_LongInteger

        return cls

    def getValueProc(self, space, pos):
        dataptr = rffi.ptradd(
            rffi.cast(roci.Ptr(roci.OCINumber), self.data),
            pos)
        if isinstance(self, VT_Integer):
            integerValuePtr = lltype.malloc(roci.Ptr(lltype.Signed).TO, 1,
                                            flavor='raw')
            try:
                status = roci.OCINumberToInt(
                    self.environment.errorHandle,
                    dataptr,
                    rffi.sizeof(rffi.LONG),
                    roci.OCI_NUMBER_SIGNED,
                    rffi.cast(roci.dvoidp, integerValuePtr))
                self.environment.checkForError(
                    status, "NumberVar_GetValue(): as integer")
                if isinstance(self, VT_Boolean):
                    return space.newbool(bool(integerValuePtr[0]))
                else:
                    return space.wrap(integerValuePtr[0])
            finally:
                lltype.free(integerValuePtr, flavor='raw')
        elif isinstance(self, VT_NumberAsString) or isinstance(self, VT_LongInteger):
            format_buf = config.StringBuffer()
            format_buf.fill(space, space.wrap("TM9"))
            sizeptr = lltype.malloc(rffi.CArray(roci.ub4), 1, flavor='raw')
            BUFSIZE = 200
            sizeptr[0] = rffi.cast(roci.ub4, BUFSIZE)
            textbuf, text = rffi.alloc_buffer(BUFSIZE)
            try:
                status = roci.OCINumberToText(
                    self.environment.errorHandle,
                    dataptr,
                    format_buf.ptr, format_buf.size,
                    None, 0,
                    sizeptr, textbuf);
                self.environment.checkForError(
                    status, "NumberVar_GetValue(): as string")
                w_strvalue = space.wrap(
                    rffi.str_from_buffer(textbuf, text,
                                         BUFSIZE,
                                         rffi.cast(lltype.Signed, sizeptr[0])))
            finally:
                rffi.keep_buffer_alive_until_here(textbuf, text)
                lltype.free(sizeptr, flavor='raw')

            if isinstance(self, VT_NumberAsString):
                return w_strvalue

            try:
                return space.call_function(space.w_int, w_strvalue)
            except OperationError, e:
                if e.match(space, space.w_ValueError):
                    return space.call_function(space.w_float, w_strvalue)
                raise
        else:
            return transform.OracleNumberToPythonFloat(
                self.environment, dataptr)

    def setValueProc(self, space, pos, w_value):
        dataptr = rffi.ptradd(
            rffi.cast(roci.Ptr(roci.OCINumber), self.data),
            pos)

        if space.is_true(space.isinstance(w_value, space.w_int)):
            integerValuePtr = lltype.malloc(roci.Ptr(lltype.Signed).TO, 1,
                                            flavor='raw')
            try:
                integerValuePtr[0] = space.int_w(w_value)
                status = roci.OCINumberFromInt(
                    self.environment.errorHandle,
                    rffi.cast(roci.dvoidp, integerValuePtr),
                    rffi.sizeof(lltype.Signed),
                    roci.OCI_NUMBER_SIGNED,
                    dataptr)
                self.environment.checkForError(
                    status, "NumberVar_SetValue(): from integer")
            finally:
                lltype.free(integerValuePtr, flavor='raw')
            return
        elif space.is_true(space.isinstance(w_value, space.w_long)):
            text_buf = config.StringBuffer()
            text_buf.fill(space, space.str(w_value))
            format_buf = config.StringBuffer()
            format_buf.fill(space, space.wrap("9" * 63))
            status = roci.OCINumberFromText(
                self.environment.errorHandle,
                text_buf.ptr, text_buf.size,
                format_buf.ptr, format_buf.size,
                None, 0,
                dataptr)
            self.environment.checkForError(
                status, "NumberVar_SetValue(): from long")
            return
        # XXX The bool case was already processed above
        elif space.is_true(space.isinstance(w_value, space.w_float)):
            doubleValuePtr = lltype.malloc(roci.Ptr(lltype.Float).TO, 1,
                                           flavor='raw')
            try:
                doubleValuePtr[0] = space.float_w(w_value)
                status = roci.OCINumberFromReal(
                    self.environment.errorHandle,
                    rffi.cast(roci.dvoidp, doubleValuePtr),
                    rffi.sizeof(lltype.Float),
                    dataptr)
                self.environment.checkForError(
                    status, "NumberVar_SetValue(): from float")
            finally:
                lltype.free(doubleValuePtr, flavor='raw')
            return
        elif space.is_true(space.isinstance(w_value, get(space).w_DecimalType)):
            w_text, w_format = transform.DecimalToFormatAndText(self.environment, w_value)
            text_buf = config.StringBuffer()
            text_buf.fill(space, w_text)
            format_buf = config.StringBuffer()
            format_buf.fill(space, w_format)
            nls_params = "NLS_NUMERIC_CHARACTERS='.,'"
            status = roci.OCINumberFromText(
                self.environment.errorHandle,
                text_buf.ptr, text_buf.size,
                format_buf.ptr, format_buf.size,
                nls_params, len(nls_params),
                dataptr)
            self.environment.checkForError(
                status, "NumberVar_SetValue(): from decimal")
            return
        raise OperationError(
            space.w_TypeError,
            space.wrap("expecting numeric data"))

class VT_Integer(VT_Float):
    pass

class VT_Boolean(VT_Integer):
    pass

class VT_NumberAsString(VT_Float):
    pass

class VT_LongInteger(VT_Float):
    pass

class VT_DateTime(W_Variable):
    oracleType = roci.SQLT_ODT
    size = rffi.sizeof(roci.OCIDate)

    def getValueProc(self, space, pos):
        dataptr = rffi.ptradd(
            rffi.cast(roci.Ptr(roci.OCIDate), self.data),
            pos)
        return transform.OracleDateToPythonDateTime(self.environment, dataptr)

    def setValueProc(self, space, pos, w_value):
        dataptr = rffi.ptradd(
            rffi.cast(roci.Ptr(roci.OCIDate), self.data),
            pos)
        if space.is_true(space.isinstance(w_value, get(space).w_DateTimeType)):
            year = space.int_w(space.getattr(w_value, space.wrap('year')))
            month = space.int_w(space.getattr(w_value, space.wrap('month')))
            day = space.int_w(space.getattr(w_value, space.wrap('day')))
            hour = space.int_w(space.getattr(w_value, space.wrap('hour')))
            minute = space.int_w(space.getattr(w_value, space.wrap('minute')))
            second = space.int_w(space.getattr(w_value, space.wrap('second')))
        elif space.is_true(space.isinstance(w_value, get(space).w_DateType)):
            year = space.int_w(space.getattr(w_value, space.wrap('year')))
            month = space.int_w(space.getattr(w_value, space.wrap('month')))
            day = space.int_w(space.getattr(w_value, space.wrap('day')))
            hour = minute = second = 0
        else:
            raise OperationError(
                space.w_TypeError,
                space.wrap("expecting date data"))

        # store a copy of the value
        value = dataptr[0]
        timePart = value.c_OCIDateTime
        rffi.setintfield(timePart, 'c_OCITimeHH', hour)
        rffi.setintfield(timePart, 'c_OCITimeMI', minute)
        rffi.setintfield(timePart, 'c_OCITimeSS', second)
        rffi.setintfield(dataptr[0], 'c_OCIDateYYYY', year)
        rffi.setintfield(dataptr[0], 'c_OCIDateMM', month)
        rffi.setintfield(dataptr[0], 'c_OCIDateDD', day)

class VT_Date(VT_DateTime):
    oracleType = roci.SQLT_ODT
    size = rffi.sizeof(roci.OCIDate)

    def getValueProc(self, space, pos):
        dataptr = rffi.ptradd(
            rffi.cast(roci.Ptr(roci.OCIDate), self.data),
            pos)
        return transform.OracleDateToPythonDate(self.environment, dataptr)

class W_VariableWithDescriptor(W_Variable):
    size = rffi.sizeof(roci.dvoidp)

    def initialize(self, space, cursor):
        # initialize the descriptors
        for i in range(self.allocatedElements):
            dataptr = rffi.ptradd(
                rffi.cast(roci.Ptr(roci.dvoidp), self.data),
                i)
            status = roci.OCIDescriptorAlloc(
                self.environment.handle,
                dataptr,
                self.descriptorType,
                0, None)
            self.environment.checkForError(
                status, self.descriptionText + "_Initialize()")

    def finalize(self):
        dataptr = rffi.cast(roci.Ptr(roci.dvoidp), self.data)
        for i in range(self.allocatedElements):
            if dataptr[i]:
                roci.OCIDescriptorFree(
                    dataptr[i], self.descriptorType)

    def getDataptr(self, pos):
        return rffi.ptradd(
            rffi.cast(roci.Ptr(roci.dvoidp), self.data),
            pos)

class VT_Timestamp(W_VariableWithDescriptor):
    oracleType = roci.SQLT_TIMESTAMP
    descriptorType = roci.OCI_DTYPE_TIMESTAMP
    descriptionText = "TimestampVar"

    def getValueProc(self, space, pos):
        return transform.OracleTimestampToPythonDate(
            self.environment, self.getDataptr(pos))

    def setValueProc(self, space, pos, w_value):
        # make sure a timestamp is being bound
        if not space.is_true(space.isinstance(w_value, get(space).w_DateTimeType)):
            raise OperationError(
                space.w_TypeError,
                space.wrap("expecting timestamp data"))

        year = space.int_w(space.getattr(w_value, space.wrap('year')))
        month = space.int_w(space.getattr(w_value, space.wrap('month')))
        day = space.int_w(space.getattr(w_value, space.wrap('day')))
        hour = space.int_w(space.getattr(w_value, space.wrap('hour')))
        minute = space.int_w(space.getattr(w_value, space.wrap('minute')))
        second = space.int_w(space.getattr(w_value, space.wrap('second')))
        microsecond = space.int_w(space.getattr(w_value, space.wrap('microsecond')))

        status = roci.OCIDateTimeConstruct(
            self.environment.handle,
            self.environment.errorHandle,
            self.getDataptr(pos)[0],
            year, month, day, hour, minute, second, microsecond * 1000,
            None, 0)

        self.environment.checkForError(
            status, "TimestampVar_SetValue(): create structure")

        validptr = lltype.malloc(rffi.CArrayPtr(roci.ub4).TO, 1, flavor='raw')
        try:
            status = roci.OCIDateTimeCheck(
                self.environment.handle,
                self.environment.errorHandle,
                self.getDataptr(pos)[0],
                validptr);
            self.environment.checkForError(
                status,
                "TimestampVar_SetValue()")
            valid = rffi.cast(lltype.Signed, validptr[0])
        finally:
            lltype.free(validptr, flavor='raw')

        if valid != 0:
            raise OperationError(
                get(space).w_DataError,
                space.wrap("invalid date"))

class VT_Interval(W_VariableWithDescriptor):
    oracleType = roci.SQLT_INTERVAL_DS
    descriptorType = roci.OCI_DTYPE_INTERVAL_DS
    descriptionText = "TimestampVar"

    def getValueProc(self, space, pos):
        return transform.OracleIntervalToPythonDelta(
            self.environment, self.getDataptr(pos))

    def setValueProc(self, space, pos, w_value):
        if not space.is_true(space.isinstance(w_value,
                                              get(space).w_TimedeltaType)):
            raise OperationError(
                space.w_TypeError,
                space.wrap("expecting timedelta data"))

        days = space.int_w(space.getattr(w_value, space.wrap('days')))
        seconds = space.int_w(space.getattr(w_value, space.wrap('seconds')))
        hours = seconds / 3600
        seconds -= hours * 3600
        minutes = seconds / 60
        seconds -= minutes * 60
        microseconds = space.int_w(
            space.getattr(w_value, space.wrap('microseconds')))

        status = roci.OCIIntervalSetDaySecond(
            self.environment.handle,
            self.environment.errorHandle,
            days, hours, minutes, seconds, microseconds,
            self.getDataptr(pos)[0])

        self.environment.checkForError(
            status, "IntervalVar_SetValue()")

class W_LobVariable(W_VariableWithDescriptor):
    descriptorType = roci.OCI_DTYPE_LOB
    descriptionText = "LobVar"
    temporaryLobType = roci.OCI_TEMP_CLOB

    def initialize(self, space, cursor):
        W_VariableWithDescriptor.initialize(self, space, cursor)
        self.connection = cursor.connection

    def ensureTemporary(self, space, pos):
        # make sure we have a temporary LOB set up
        temporaryptr = lltype.malloc(rffi.CArrayPtr(roci.boolean).TO, 1, flavor='raw')
        try:
            status = roci.OCILobIsTemporary(
                self.environment.handle,
                self.environment.errorHandle,
                self.getDataptr(pos)[0],
                temporaryptr);
            self.environment.checkForError(
                status,
                "LobVar_SetValue(): check temporary")
            temporary = rffi.cast(lltype.Signed, temporaryptr[0])
        finally:
            lltype.free(temporaryptr, flavor='raw')

        if temporary:
            return

        status = roci.OCILobCreateTemporary(
            self.connection.handle,
            self.environment.errorHandle,
            self.getDataptr(pos)[0],
            roci.OCI_DEFAULT,
            roci.OCI_DEFAULT,
            self.temporaryLobType,
            False,
            roci.OCI_DURATION_SESSION)
        self.environment.checkForError(
            status,
            "LobVar_SetValue(): create temporary")


    def setValueProc(self, space, pos, w_value):
        self.ensureTemporary(space, pos)
        self.trim(space, pos, 0)
        self.write(space, pos, w_value, 1)

    def getLength(self, space, pos):
        "Return the size of the LOB variable for internal comsumption."
        lengthptr = lltype.malloc(rffi.CArrayPtr(roci.ub4).TO, 1, flavor='raw')
        try:
            status = roci.OCILobGetLength(
                self.connection.handle,
                self.environment.errorHandle,
                self.getDataptr(pos)[0],
                lengthptr)
            self.environment.checkForError(
                status,
                "LobVar_GetLength()")
            return rffi.cast(lltype.Signed,
                             lengthptr[0]) # XXX test overflow
        finally:
            lltype.free(lengthptr, flavor='raw')

    def trim(self, space, pos, newSize):
        status = roci.OCILobTrim(
            self.connection.handle,
            self.environment.errorHandle,
            self.getDataptr(pos)[0],
            newSize)
        self.environment.checkForError(
            status,
            "LobVar_Trim()")

    def read(self, space, pos, offset, amount):
        # modify the arguments
        if offset <= 0:
            offset = 1
        if amount < 0:
            amount = self.getLength(space, pos) - offset + 1
            if amount <= 0:
                amount = 1

        bufferSize = amount
        raw_buffer, gc_buffer = rffi.alloc_buffer(bufferSize)
        amountptr = lltype.malloc(rffi.CArrayPtr(roci.ub4).TO, 1, flavor='raw')
        amountptr[0] = rffi.cast(roci.ub4, amount)
        try:
            status = roci.OCILobRead(
                self.connection.handle,
                self.environment.errorHandle,
                self.getDataptr(pos)[0],
                amountptr, offset,
                raw_buffer, bufferSize,
                None, None,
                config.CHARSETID, self.charsetForm)
            self.environment.checkForError(
                status,
                "LobVar_Read()")
            amount = rffi.cast(lltype.Signed,
                               amountptr[0]) # XXX test overflow
            value = rffi.str_from_buffer(raw_buffer, gc_buffer, bufferSize, amount)
            return space.wrap(value)
        finally:
            lltype.free(amountptr, flavor='raw')
            rffi.keep_buffer_alive_until_here(raw_buffer, gc_buffer)

    def write(self, space, pos, w_value, offset):
        databuf = config.StringBuffer()
        databuf.fill(space, w_value)
        amountptr = lltype.malloc(rffi.CArrayPtr(roci.ub4).TO, 1, flavor='raw')
        amountptr[0] = rffi.cast(roci.ub4, databuf.size)

        try:
            # nothing to do if no data to write
            if databuf.size == 0:
                return 0

            status = roci.OCILobWrite(
                self.connection.handle,
                self.environment.errorHandle,
                self.getDataptr(pos)[0],
                amountptr, offset,
                databuf.ptr, databuf.size,
                roci.OCI_ONE_PIECE,
                None, None,
                config.CHARSETID, self.charsetForm)
            self.environment.checkForError(
                status,
                "LobVar_Write()")
            amount = amountptr[0]
        finally:
            lltype.free(amountptr, flavor='raw')
            databuf.clear()

        return amount

    def getValueProc(self, space, pos):
        return space.wrap(interp_lob.W_ExternalLob(self, pos))

class VT_CLOB(W_LobVariable):
    oracleType = roci.SQLT_CLOB

class VT_NCLOB(W_LobVariable):
    oracleType = roci.SQLT_CLOB

class VT_BLOB(W_LobVariable):
    oracleType = roci.SQLT_BLOB
    temporaryLobType = roci.OCI_TEMP_BLOB

class VT_BFILE(W_LobVariable):
    oracleType = roci.SQLT_BFILE

    def write(self, space, pos, w_value, offset):
        raise OperationError(
            space.w_TypeError,
            space.wrap("BFILEs are read only"))

    def read(self, space, pos, offset, amount):
        self.openFile()
        try:
            return W_LobVariable.read(self, space, pos, offset, amount)
        finally:
            self.closeFile()

    def openFile(self):
        pass # XXX

    def closeFile(self):
        pass # XXX

class VT_Cursor(W_Variable):
    oracleType = roci.SQLT_RSET
    size = rffi.sizeof(roci.OCIStmt)
    canBeInArray = False

    def initialize(self, space, cursor):
        from pypy.module.oracle import interp_cursor
        self.connection = cursor.connection
        self.cursors_w = [None] * self.allocatedElements
        for i in range(self.allocatedElements):
            tempCursor = interp_cursor.W_Cursor(space, self.connection)
            tempCursor.allocateHandle()
            self.cursors_w[i] = space.wrap(tempCursor)

            dataptr = rffi.ptradd(
                rffi.cast(roci.Ptr(roci.OCIStmt), self.data),
                i)
            dataptr[0] = tempCursor.handle

    def getValueProc(self, space, pos):
        from pypy.module.oracle import interp_cursor
        w_cursor = self.cursors_w[pos]
        space.interp_w(interp_cursor.W_Cursor, w_cursor).statementType = -1
        return w_cursor

    def setValueProc(self, space, pos, w_value):
        from pypy.module.oracle import interp_cursor
        w_CursorType = space.gettypeobject(interp_cursor.W_Cursor.typedef)
        if not space.is_true(space.isinstance(w_value, w_CursorType)):
            raise OperationError(
                space.w_TypeError,
                space.wrap("expecting cursor"))

        self.cursors_w[pos] = w_value

        cursor = space.interp_w(interp_cursor.W_Cursor, w_value)
        if not cursor.isOwned:
            cursor.freeHandle(space, raiseError=True)
            cursor.isOwned = True
            cursor.allocateHandle()

        dataptr = rffi.ptradd(
            rffi.cast(roci.Ptr(roci.OCIStmt), self.data),
            pos)
        dataptr[0] = cursor.handle
        cursor.statementType = -1


class VT_Object(W_Variable):
    oracleType = roci.SQLT_NTY
    size = rffi.sizeof(roci.dvoidp)
    canBeInArray = False

    objectIndicator = lltype.nullptr(rffi.CArrayPtr(roci.dvoidp).TO)

    def initialize(self, space, cursor):
        self.connection = cursor.connection
        self.objectType = None
        self.objectIndicator = lltype.malloc(
            rffi.CArrayPtr(roci.dvoidp).TO,
            self.allocatedElements,
            flavor='raw', zero=True)

    def finalize(self):
        for i in range(self.allocatedElements):
            data = rffi.cast(roci.Ptr(roci.dvoidp), self.data)
            roci.OCIObjectFree(
                self.environment.handle,
                self.environment.errorHandle,
                data[i],
                roci.OCI_OBJECTFREE_FORCE)
        if self.objectIndicator:
            lltype.free(self.objectIndicator, flavor='raw')

    def postDefine(self, param):
        # XXX this used to be in preDefine
        self.objectType = interp_object.W_ObjectType(self.connection, param)

        data = rffi.cast(roci.Ptr(roci.dvoidp), self.data)

        status = roci.OCIDefineObject(
            self.defineHandle,
            self.environment.errorHandle,
            self.objectType.tdo,
            data,
            0,
            self.objectIndicator,
            0)
        self.environment.checkForError(
            status,
            "ObjectVar_PostDefine(): define object")

    def isNull(self, pos):
        # look at our own indicator array
        if not self.objectIndicator[pos]:
            return True
        return (rffi.cast(lltype.Signed,
                          rffi.cast(roci.Ptr(roci.OCIInd),
                                    self.objectIndicator[pos])[0])
                ==
                rffi.cast(lltype.Signed, roci.OCI_IND_NULL))

    def getValueProc(self, space, pos):
        data = rffi.cast(roci.Ptr(roci.dvoidp), self.data)
        # only allowed to get the value once (for now)
        if not data[pos]:
            raise OperationError(
                get(space).w_ProgrammingError,
                space.wrap("variable value can only be acquired once"))


        # for collections, return the list rather than the object
        if self.objectType.isCollection:
            return interp_object.convertCollection(
                space, self.environment, data[pos], self, self.objectType)

        # for objects, return a representation of the object
        var = interp_object.W_ExternalObject(
            self, self.objectType, data[pos], self.objectIndicator[pos])

        data[pos] = lltype.nullptr(roci.dvoidp.TO)
        self.objectIndicator[pos] = lltype.nullptr(roci.dvoidp.TO)
        return space.wrap(var)

all_variable_types = []
for name, cls in globals().items():
    if not name.startswith('VT_') or not isinstance(cls, type):
        continue
    def register_variable_class(cls):
        def clone(self, cursor, numElements, size):
            return cls(cursor, numElements, size)
        cls.clone = clone
        cls.typedef = TypeDef(
            cls.__name__, W_Variable.typedef,
            )
        all_variable_types.append(cls)
    register_variable_class(cls)

def typeByOracleDescriptor(param, environment):
    # retrieve datatype of the parameter
    attrptr = lltype.malloc(rffi.CArrayPtr(roci.ub2).TO, 1, flavor='raw')
    try:
        status = roci.OCIAttrGet(
            param, roci.OCI_HTYPE_DESCRIBE,
            rffi.cast(roci.dvoidp, attrptr),
            lltype.nullptr(roci.Ptr(roci.ub4).TO),
            roci.OCI_ATTR_DATA_TYPE,
            environment.errorHandle)
        environment.checkForError(
            status,
            "Variable_TypeByOracleDescriptor(): data type")
        dataType = rffi.cast(lltype.Signed, attrptr[0])
    finally:
        lltype.free(attrptr, flavor='raw')

    # retrieve character set form of the parameter
    if dataType not in (roci.SQLT_CHR, roci.SQLT_AFC, roci.SQLT_CLOB):
        charsetForm = roci.SQLCS_IMPLICIT
    else:
        attrptr = lltype.malloc(rffi.CArrayPtr(roci.ub1).TO, 1, flavor='raw')
        try:
            status = roci.OCIAttrGet(
                param, roci.OCI_HTYPE_DESCRIBE,
                rffi.cast(roci.dvoidp, attrptr),
                lltype.nullptr(roci.Ptr(roci.ub4).TO),
                roci.OCI_ATTR_CHARSET_FORM,
                environment.errorHandle)
            environment.checkForError(
                status,
                "Variable_TypeByOracleDescriptor(): charset form")
            charsetForm = rffi.cast(lltype.Signed, attrptr[0])
        finally:
            lltype.free(attrptr, flavor='raw')

    return _typeByOracleDataType(dataType, charsetForm)

variableType = {
    roci.SQLT_LNG: VT_LongString,
    roci.SQLT_AFC: VT_FixedChar,
    roci.SQLT_CHR: VT_String,
    roci.SQLT_RDD: VT_Rowid,
    roci.SQLT_BIN: VT_Binary,
    roci.SQLT_LBI: VT_LongBinary,
    roci.SQLT_BFLOAT: VT_NativeFloat,
    roci.SQLT_IBFLOAT: VT_NativeFloat,
    roci.SQLT_BDOUBLE: VT_NativeFloat,
    roci.SQLT_IBDOUBLE: VT_NativeFloat,
    roci.SQLT_NUM: VT_Float,
    roci.SQLT_VNU: VT_Float,
    roci.SQLT_DAT: VT_DateTime,
    roci.SQLT_ODT: VT_DateTime,
    roci.SQLT_DATE: VT_Timestamp,
    roci.SQLT_TIMESTAMP: VT_Timestamp,
    roci.SQLT_TIMESTAMP_TZ: VT_Timestamp,
    roci.SQLT_TIMESTAMP_LTZ: VT_Timestamp,
    roci.SQLT_INTERVAL_DS: VT_Interval,
    roci.SQLT_CLOB: VT_CLOB,
    roci.SQLT_BLOB: VT_BLOB,
    roci.SQLT_BFILE: VT_BFILE,
    roci.SQLT_RSET: VT_Cursor,
    roci.SQLT_NTY: VT_Object,
    }
variableTypeNChar = {
    roci.SQLT_AFC: VT_FixedNationalChar,
    roci.SQLT_CHR: VT_NationalCharString,
    roci.SQLT_CLOB: VT_NCLOB,
    }
# remove eventual undefined types
try:
    del variableType[None]
except KeyError:
    pass
try:
    del variableTypeNChar[None]
except KeyError:
    pass

def _typeByOracleDataType(dataType, charsetForm):
    if charsetForm == roci.SQLCS_NCHAR:
        varType = variableTypeNChar.get(dataType, None)
    else:
        varType = variableType.get(dataType, None)

    if varType is None:
        raise ValueError("Variable_TypeByOracleDataType: "
                         "unhandled data type %d" % (dataType,))

    return varType

def typeByPythonType(space, cursor, w_type):
    """Return a variable type given a Python type object"""
    from pypy.objspace.std.typeobject import W_TypeObject

    moduledict = get(space)
    if not space.is_true(space.isinstance(w_type, space.w_type)):
        raise OperationError(
            space.w_TypeError,
            space.wrap("Variable_TypeByPythonType(): type expected"))
    assert isinstance(w_type, W_TypeObject)
    if w_type in get(space).variableTypeByPythonType:
        return get(space).variableTypeByPythonType[w_type]
    if space.is_w(w_type, space.w_int):
        return VT_Integer
    raise OperationError(
        moduledict.w_NotSupportedError,
        space.wrap("Variable_TypeByPythonType(): unhandled data type"))

def typeByValue(space, w_value, numElements):
    "Return a variable type given a Python object"
    moduledict = get(space)

    # handle scalars
    if space.is_w(w_value, space.w_None):
        return VT_String, 1, numElements

    if space.is_true(space.isinstance(w_value, space.w_str)):
        size = space.len_w(w_value)
        if size > config.MAX_STRING_CHARS:
            return VT_LongString, size, numElements
        else:
            return VT_String, size, numElements

    if space.is_true(space.isinstance(w_value, space.w_unicode)):
        size = space.len_w(w_value)
        return VT_NationalCharString, size, numElements

    if space.is_true(space.isinstance(w_value, space.w_int)):
        return VT_Integer, 0, numElements

    if space.is_true(space.isinstance(w_value, space.w_long)):
        return VT_LongInteger, 0, numElements

    if space.is_true(space.isinstance(w_value, space.w_float)):
        return VT_Float, 0, numElements

    # XXX cxBinary

    # XXX bool

    if space.is_true(space.isinstance(w_value, get(space).w_DateTimeType)):
        return VT_DateTime, 0, numElements

    if space.is_true(space.isinstance(w_value, get(space).w_DateType)):
        return VT_Date, 0, numElements

    # XXX Delta

    from pypy.module.oracle import interp_cursor
    if space.is_true(space.isinstance( # XXX is there an easier way?
        w_value,
        space.gettypeobject(interp_cursor.W_Cursor.typedef))):
        return VT_Cursor, 0, numElements

    if space.is_true(space.isinstance(w_value, get(space).w_DecimalType)):
        return VT_NumberAsString, 0, numElements

    # handle arrays
    if space.is_true(space.isinstance(w_value, space.w_list)):
        elements_w = space.listview(w_value)
        for w_element in elements_w:
            if not space.is_w(w_element, space.w_None):
                break
        else:
            w_element = space.w_None
        varType, size, _ = typeByValue(space, w_element, numElements)
        return varType, size, len(elements_w)

    raise OperationError(
        moduledict.w_NotSupportedError,
        space.wrap("Variable_TypeByValue(): unhandled data type %s" %
                   (space.type(w_value).getname(space, '?'),)))

def newByInputTypeHandler(space, cursor, w_inputTypeHandler, w_value, numElements):
    w_var = space.call(w_inputTypeHandler,
                       space.wrap(cursor),
                       w_value,
                       space.wrap(numElements))
    if not space.is_true(space.isinstance(w_var,
                                          get(space).w_Variable)):
        raise OperationError(
            space.w_TypeError,
            space.wrap("expecting variable from input type handler"))
    return space.interp_w(W_Variable, w_var)

def newVariableByValue(space, cursor, w_value, numElements):
    var = space.w_None

    if cursor.w_inputTypeHandler:
        var = newByInputTypeHandler(
            space, cursor, cursor.w_inputTypeHandler,
            w_value, numElements)
    elif cursor.connection.w_inputTypeHandler:
        var =  newByInputTypeHandler(
            space, cursor, cursor.connection.w_inputTypeHandler,
            w_value, numElements)

    if space.is_w(var, space.w_None):
        varType, size, numElements = typeByValue(space, w_value, numElements)
        var = varType(cursor, numElements, size)
        if space.is_true(space.isinstance(w_value, space.w_list)):
            var.makeArray(space)

    assert isinstance(var, W_Variable)
    return var

def newArrayVariableByType(space, cursor, w_value):
    "Allocate a new PL/SQL array by looking at the Python data type."

    w_type, w_numElements = space.fixedview(w_value, 2)

    numElements = space.int_w(w_numElements)
    varType = typeByPythonType(space, cursor, w_type)

    var = varType(cursor, numElements)
    var.makeArray(space)
    return var

def newVariableByType(space, cursor, w_value, numElements):
    # passing an integer is assumed to be a string
    if space.is_true(space.isinstance(w_value, space.w_int)):
        size = space.int_w(w_value)
        if size > config.MAX_STRING_CHARS:
            varType = VT_LongString
        else:
            varType = VT_String
        return varType(cursor, numElements, size)

    # passing an array of two elements define an array
    if space.is_true(space.isinstance(w_value, space.w_list)):
        return newArrayVariableByType(space, cursor, w_value)

    # handle directly bound variables
    if space.is_true(space.isinstance(w_value,
                                      get(space).w_Variable)):
        return space.interp_w(W_Variable, w_value)

    # everything else ought to be a Python type
    varType = typeByPythonType(space, cursor, w_value)
    return varType(cursor, numElements, varType.size)
