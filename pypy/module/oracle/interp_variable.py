from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.typedef import interp_attrproperty
from pypy.interpreter.gateway import ObjSpace, W_Root
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.error import OperationError
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.rlib.rarithmetic import ovfcheck

import sys
from pypy.module.oracle import roci, config, transform
from pypy.module.oracle.interp_error import get
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
    varType = _typeByOracleDescriptor(param, cursor.environment)
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
            sizeFromOracle = attrptr[0]
        finally:
            lltype.free(attrptr, flavor='raw')

        # use the length from Oracle directly if available
        if sizeFromOracle:
            size = sizeFromOracle

        # otherwise, use the value set with the setoutputsize() parameter
        elif cursor.outputSize >= 0:
            if (cursor.outputSizeColumn < 0 or
                position == cursor.outputSizeColumn):
                size = cursor.outputSize

    # create a variable of the correct type
    if cursor.outputTypeHandler:
        var = _newByOutputTypeHandler(
            cursor, param,
            cursor.outputTypeHandler,
            varType, size, numElements)
    elif cursor.connection.outputTypeHandler:
        var = _newByOutputTypeHandler(
            cursor, param,
            cursor.connection.outputTypeHandler,
            varType, size, numElements)
    else:
        var = varType(cursor, numElements, size)

    # call the procedure to set values prior to define
    var.preDefine(param)

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
    var.postDefine()

    return var


class W_Variable(Wrappable):
    charsetForm = roci.SQLCS_IMPLICIT
    isVariableLength = False
    
    def __init__(self, cursor, numElements, size=0):
        self.environment = cursor.environment
        self.boundCursorHandle = lltype.nullptr(roci.OCIStmt.TO)
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
        self.allocateData()
    
        # allocate the indicator for the variable
        self.indicator = lltype.malloc(rffi.CArrayPtr(roci.sb2).TO,
                                       self.allocatedElements,
                                       flavor='raw', zero=True) # XXX

        # ensure that all variable values start out NULL
        for i in range(self.allocatedElements):
            self.indicator[i] = rffi.cast(roci.sb2, roci.OCI_IND_NULL)

        # for variable length data, also allocate the return code
        if self.isVariableLength:
            self.returnCode = lltype.malloc(rffi.CArrayPtr(roci.ub2).TO,
                                            self.allocatedElements,
                                            flavor='raw', zero=True) # XXX

        # perform extended initialization
        self.initialize(cursor)

    def __del__(self):
        lltype.free(self.actualElementsPtr, flavor='raw')
        if self.actualLength:
            lltype.free(self.actualLength, flavor='raw')
        if self.data:
            lltype.free(self.data, flavor='raw')

    def getBufferSize(self):
        return self.size

    def allocateData(self):
        # set the buffer size for the variable
        self.bufferSize = self.getBufferSize()

        # allocate the data as long as it is small enough
        dataLength = ovfcheck(self.allocatedElements * self.bufferSize)
        if dataLength > sys.maxint:
            raise ValueError("array size too large")

        self.data = lltype.malloc(rffi.CCHARP.TO, int(dataLength),
                                  flavor='raw', zero=True)

    def initialize(self, cursor):
        pass

    def preDefine(self, param):
        pass

    def postDefine(self):
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

    def isNull(self, pos):
        return self.indicator[pos] == roci.OCI_IND_NULL

    def verifyFetch(self, space, pos):
        # Verifies that truncation or other problems did not take place on
        # retrieve.
        if self.isVariableLength:
            if self.returnCode[pos] != 0:
                error = W_Error(space, self.environment,
                                "Variable_VerifyFetch()", 0)
                error.code = self.returnCode[pos]
                error.message = self.space.wrap(
                    "column at array pos %d fetched with error: %d" %
                    (pos, self.returnCode[pos]))
                w_error = get(self.space).w_DatabaseError

                raise OperationError(get(self.space).w_DatabaseError,
                                     self.space.wrap(error))

    def getSingleValue(self, space, pos):
        # ensure we do not exceed the number of allocated elements
        if pos >= self.allocatedElements:
            raise OperationError(
                space.w_PyExc_IndexError,
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

    def getValue(self, space, pos=0):
        if self.isArray:
            return self.getArrayValue(self, self.actualElements)
        return self.getSingleValue(space, pos)
    getValue.unwrap_spec = ['self', ObjSpace, int]

    def setSingleValue(self, space, pos, w_value):
        # ensure we do not exceed the number of allocated elements
        if pos >= self.allocatedElements:
            raise OperationError(
                space.w_PyExc_IndexError,
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

    def setValue(self, space, pos, w_value):
        if self.isArray:
            self.setArrayValue(self, w_value)
        self.setSingleValue(space, pos, w_value)
    setValue.unwrap_spec = ['self', ObjSpace, int, W_Root]


W_Variable.typedef = TypeDef(
    'Variable',
    getvalue = interp2app(W_Variable.getValue,
                          unwrap_spec=W_Variable.getValue.unwrap_spec),
    setvalue = interp2app(W_Variable.setValue,
                          unwrap_spec=W_Variable.setValue.unwrap_spec),

    maxlength = interp_attrproperty('bufferSize', W_Variable),

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

    def initialize(self, cursor):
        self.actualLength = lltype.malloc(rffi.CArrayPtr(roci.ub2).TO,
                                          self.allocatedElements,
                                          zero=True, flavor='raw')

    def getValueProc(self, space, pos):
        offset = pos * self.bufferSize
        length = self.actualLength[pos]

        l = []
        i = 0
        if config.WITH_UNICODE:
            if isinstance(self, VT_Binary):
                while i < length:
                    l.append(self.data[offset + i])
                    i += 1
                return space.wrap(''.join(l))
            else:
                while i < length:
                    l.append(unichr((ord(self.data[offset + i]) << 8) +
                                    ord(self.data[offset + i + 1])))
                    i += 2
                return space.wrap(u''.join(l))
        else:
            if self.charsetForm == roci.SQLCS_IMPLICIT:
                while i < length:
                    l.append(self.data[offset + i])
                    i += 1
                return space.wrap(''.join(l))
            else:
                while i < length:
                    l.append(unichr((ord(self.data[offset + i]) << 8) +
                                    ord(self.data[offset + i + 1])))
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

        try:
            if buf.size > self.environment.maxStringBytes:
                raise OperationError(
                    space.w_ValueError,
                    space.wrap("string data too large"))

            # ensure that the buffer is large enough
            if buf.size > self.bufferSize:
                self.resize(size)

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

class VT_NationalCharString(W_Variable):
    pass

class VT_LongString(W_Variable):
    pass

class VT_FixedNationalChar(W_Variable):
    pass

class VT_Rowid(W_Variable):
    pass

class VT_Binary(W_Variable):
    pass

class VT_LongBinary(W_Variable):
    pass

class VT_NativeFloat(W_Variable):
    pass

class VT_Float(W_Variable):
    oracleType = roci.SQLT_VNU
    size = rffi.sizeof(roci.OCINumber)

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
                    return space.newbool(integerValuePtr[0])
                else:
                    return space.wrap(integerValuePtr[0])
            finally:
                lltype.free(integerValuePtr, flavor='raw')
        elif isinstance(self, (VT_NumberAsString, VT_LongInteger)):
            XXX = NumberAsString, LongInteger
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
            status = roci.OCINumberFromText(
                self.environment.errorHandle,
                text_buf.ptr, text_buf.size,
                format_buf.ptr, format_buf.size,
                None, 0, dataptr)
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
        dataptr = rffi.cast(roci.Ptr(roci.OCIDate), self.data)
        return transform.OracleDateToPythonDateTime(self.environment, dataptr)

class VT_Date(W_Variable):
    oracleType = roci.SQLT_ODT
    size = rffi.sizeof(roci.OCIDate)

    def getValueProc(self, space, pos):
        dataptr = rffi.ptradd(
            rffi.cast(roci.Ptr(roci.OCIDate), self.data),
            pos)
        return transform.OracleDateToPythonDate(self.environment, dataptr)

class VT_Timestamp(W_Variable):
    pass

class VT_Interval(W_Variable):
    pass

class VT_CLOB(W_Variable):
    pass

class VT_NCLOB(W_Variable):
    pass

class VT_BLOB(W_Variable):
    pass

class VT_BFILE(W_Variable):
    pass

class VT_Cursor(W_Variable):
    pass

class VT_Object(W_Variable):
    pass

variableTypeByTypedef = {}
for name, cls in globals().items():
    if not name.startswith('VT_') or not isinstance(cls, type):
        continue
    cls.typedef = TypeDef(
        cls.__name__, W_Variable.typedef,
        )
    variableTypeByTypedef[cls.typedef] = cls

def _typeByOracleDescriptor(param, environment):
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
        dataType = attrptr[0]
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
            charsetForm = attrptr[0]
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

def _typeByOracleDataType(dataType, charsetForm):
    if charsetForm == roci.SQLCS_NCHAR:
        varType = variableTypeNChar.get(dataType)
    else:
        varType = variableType.get(dataType)

    if varType is None:
        raise ValueError("Variable_TypeByOracleDataType: "
                         "unhandled data type %d" % (dataType,))

    return varType

def typeByPythonType(space, cursor, w_type):
    """Return a variable type given a Python type object"""
    moduledict = get(space)
    if w_type.instancetypedef in variableTypeByTypedef:
        return variableTypeByTypedef[w_type.instancetypedef]
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
        size = space.int_w(space.len(w_value))
        return VT_String, size, numElements

    # XXX Unicode

    if space.is_true(space.isinstance(w_value, space.w_int)):
        return VT_Integer, 0, numElements

    # XXX long

    if space.is_true(space.isinstance(w_value, space.w_float)):
        return VT_Float, 0, numElements

    # XXX cxBinary

    # XXX bool

    # XXX datetime

    # XXX date

    # XXX Delta

    # XXX cursorType

    if space.is_true(space.isinstance(w_value, get(space).w_DecimalType)):
        return VT_NumberAsString, 0, numElements

    raise OperationError(
        moduledict.w_NotSupportedError,
        space.wrap("Variable_TypeByValue(): unhandled data type %s" %
                   (space.type(w_value).getname(space, '?'),)))

def newVariableByValue(space, cursor, w_value, numElements):
    if cursor.inputTypeHandler:
        return newByInputTypeHandler(
            cursor, cursor.inputTypeHandler,
            w_value, numElements)
    elif cursor.connection.inputTypeHandler:
        return newByInputTypeHandler(
            cursor, cursor.connection.inputTypeHandler,
            w_value, numElements)
    else:
        varType, size, numElements = typeByValue(space, w_value, numElements)
        var = varType(cursor, numElements, size)
        if space.is_true(space.isinstance(w_value, space.w_list)):
            var.makeArray()
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
        XXX

    # handle directly bound variables
    if space.is_true(space.isinstance(w_value,
                                      get(space).w_Variable)):
        return space.interp_w(W_Variable, w_value)

    # everything else ought to be a Python type
    varType = typeByPythonType(space, cursor, w_value)
    return varType(cursor, numElements)
