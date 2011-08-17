from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.typedef import TypeDef, GetSetProperty
from pypy.interpreter.typedef import interp_attrproperty
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.error import OperationError
from pypy.rpython.lltypesystem import rffi, lltype

from pypy.module.oracle import roci, config, transform
from pypy.module.oracle.interp_error import get

class W_ObjectType(Wrappable):
    def __init__(self, connection, param):
        self.tdo = lltype.nullptr(roci.dvoidp.TO)
        self.environment = connection.environment
        self.isCollection = False
        self.initialize(connection, param)

    def __del__(self):
        self.enqueue_for_destruction(self.space, W_ObjectType.destructor,
                                     '__del__ method of ')

    def destructor(self):
        assert isinstance(self, W_ObjectType)
        if self.tdo:
            roci.OCIObjectUnpin(
                self.environment.handle,
                self.environment.errorHandle,
                self.tdo)

    def initialize(self, connection, param):
        nameptr = lltype.malloc(rffi.CArrayPtr(roci.oratext).TO, 1,
                                flavor='raw')
        lenptr = lltype.malloc(rffi.CArrayPtr(roci.ub4).TO, 1,
                               flavor='raw')
        try:
            # determine the schema of the type
            status = roci.OCIAttrGet(
                param, roci.OCI_HTYPE_DESCRIBE,
                rffi.cast(roci.dvoidp, nameptr),
                lenptr,
                roci.OCI_ATTR_SCHEMA_NAME,
                self.environment.errorHandle)
            self.environment.checkForError(
                status,
                "ObjectType_Initialize(): get schema name")
            self.schema = rffi.charpsize2str(nameptr[0], rffi.cast(lltype.Signed, lenptr[0]))

            # determine the name of the type
            status = roci.OCIAttrGet(
                param, roci.OCI_HTYPE_DESCRIBE,
                rffi.cast(roci.dvoidp, nameptr),
                lenptr,
                roci.OCI_ATTR_TYPE_NAME,
                self.environment.errorHandle)
            self.environment.checkForError(
                status,
                "ObjectType_Initialize(): get schema name")
            self.name = rffi.charpsize2str(nameptr[0], rffi.cast(lltype.Signed, lenptr[0]))
        finally:
            lltype.free(nameptr, flavor='raw')
            lltype.free(lenptr, flavor='raw')

        # retrieve TDO (type descriptor object) of the parameter
        tdorefptr = lltype.malloc(rffi.CArrayPtr(roci.OCIRef).TO, 1,
                                  flavor='raw')
        try:
            status = roci.OCIAttrGet(
                param, roci.OCI_HTYPE_DESCRIBE,
                rffi.cast(roci.dvoidp, tdorefptr),
                lltype.nullptr(roci.Ptr(roci.ub4).TO),
                roci.OCI_ATTR_REF_TDO,
                self.environment.errorHandle)
            self.environment.checkForError(
                status,
                "ObjectType_Initialize(): get TDO reference")
            tdoref = tdorefptr[0]
        finally:
            lltype.free(tdorefptr, flavor='raw')

        tdoptr = lltype.malloc(rffi.CArrayPtr(roci.dvoidp).TO, 1,
                               flavor='raw')
        try:
            status = roci.OCIObjectPin(
                self.environment.handle,
                self.environment.errorHandle,
                tdoref,
                None, roci.OCI_PIN_ANY,
                roci.OCI_DURATION_SESSION, roci.OCI_LOCK_NONE,
                tdoptr)
            self.environment.checkForError(
                status,
                "ObjectType_Initialize(): pin TDO reference")
            self.tdo = tdoptr[0]
        finally:
            lltype.free(tdoptr, flavor='raw')

        # acquire a describe handle
        handleptr = lltype.malloc(rffi.CArrayPtr(roci.OCIDescribe).TO,
                                  1, flavor='raw')
        try:
            status = roci.OCIHandleAlloc(
                self.environment.handle,
                handleptr, roci.OCI_HTYPE_DESCRIBE, 0,
                lltype.nullptr(rffi.CArray(roci.dvoidp)))
            self.environment.checkForError(
                status, "ObjectType_Initialize(): allocate describe handle")
            describeHandle = handleptr[0]
        finally:
            lltype.free(handleptr, flavor='raw')

        # describe the type
        try:
            self.describe(connection, describeHandle)
        finally:
            roci.OCIHandleFree(describeHandle, roci.OCI_HTYPE_DESCRIBE)

    def describe(self, connection, describeHandle):
        "Describe the type and store information about it as needed"

        # describe the type
        status = roci.OCIDescribeAny(
            connection.handle,
            self.environment.errorHandle,
            self.tdo, 0,
            roci.OCI_OTYPE_PTR,
            roci.OCI_DEFAULT,
            roci.OCI_PTYPE_TYPE,
            describeHandle)
        self.environment.checkForError(
            status, "ObjectType_Describe(): describe type")

        # get top level parameter descriptor
        paramptr = lltype.malloc(roci.Ptr(roci.OCIParam).TO,
                                 1, flavor='raw')
        try:
            status = roci.OCIAttrGet(
                describeHandle, roci.OCI_HTYPE_DESCRIBE,
                rffi.cast(roci.dvoidp, paramptr),
                lltype.nullptr(roci.Ptr(roci.ub4).TO),
                roci.OCI_ATTR_PARAM,
                self.environment.errorHandle)
            self.environment.checkForError(
                status,
                "ObjectType_Describe(): get top level parameter descriptor")
            toplevelParam = paramptr[0]
        finally:
            lltype.free(paramptr, flavor='raw')

        # determine type of type
        typecodeptr = lltype.malloc(roci.Ptr(roci.OCITypeCode).TO,
                                    1, flavor='raw')
        try:
            status = roci.OCIAttrGet(
                toplevelParam, roci.OCI_DTYPE_PARAM,
                rffi.cast(roci.dvoidp, typecodeptr),
                lltype.nullptr(roci.Ptr(roci.ub4).TO),
                roci.OCI_ATTR_TYPECODE,
                self.environment.errorHandle)
            self.environment.checkForError(
                status, "ObjectType_Describe(): get type code")
            typeCode = rffi.cast(lltype.Signed, typecodeptr[0])
        finally:
            lltype.free(typecodeptr, flavor='raw')

        # if a collection, need to determine the sub type
        if typeCode == roci.OCI_TYPECODE_NAMEDCOLLECTION:
            self.isCollection = 1

            # determine type of collection
            typecodeptr = lltype.malloc(roci.Ptr(roci.OCITypeCode).TO,
                                        1, flavor='raw')
            try:
                status = roci.OCIAttrGet(
                    toplevelParam, roci.OCI_DTYPE_PARAM,
                    rffi.cast(roci.dvoidp, typecodeptr),
                    lltype.nullptr(roci.Ptr(roci.ub4).TO),
                    roci.OCI_ATTR_TYPECODE,
                    self.environment.errorHandle)
                self.environment.checkForError(
                    status, "ObjectType_Describe(): get collection type code")
                self.collectionTypeCode = typecodeptr[0]
            finally:
                lltype.free(typecodeptr, flavor='raw')

            # acquire collection parameter descriptor
            paramptr = lltype.malloc(roci.Ptr(roci.OCIParam).TO,
                                     1, flavor='raw')
            try:
                status = roci.OCIAttrGet(
                    toplevelParam, roci.OCI_DTYPE_PARAM,
                    rffi.cast(roci.dvoidp, paramptr),
                    lltype.nullptr(roci.Ptr(roci.ub4).TO),
                    roci.OCI_ATTR_COLLECTION_ELEMENT,
                    self.environment.errorHandle)
                self.environment.checkForError(
                    status,
                    "ObjectType_Describe(): get collection descriptor")
                collectionParam = paramptr[0]
            finally:
                lltype.free(paramptr, flavor='raw')

            # determine type of element
            typecodeptr = lltype.malloc(roci.Ptr(roci.OCITypeCode).TO,
                                        1, flavor='raw')
            try:
                status = roci.OCIAttrGet(
                    collectionParam, roci.OCI_DTYPE_PARAM,
                    rffi.cast(roci.dvoidp, typecodeptr),
                    lltype.nullptr(roci.Ptr(roci.ub4).TO),
                    roci.OCI_ATTR_TYPECODE,
                    self.environment.errorHandle)
                self.environment.checkForError(
                    status, "ObjectType_Describe(): get element type code")
                self.elementTypeCode = rffi.cast(lltype.Signed, typecodeptr[0])
            finally:
                lltype.free(typecodeptr, flavor='raw')

            # if element type is an object type get its type
            if self.elementTypeCode == roci.OCI_TYPECODE_OBJECT:
                self.elementType = W_ObjectType(connection, collectionParam)
            else:
                self.elementType = None

        # determine the number of attributes
        numptr = lltype.malloc(roci.Ptr(roci.ub2).TO,
                               1, flavor='raw')
        try:
            status = roci.OCIAttrGet(
                toplevelParam, roci.OCI_DTYPE_PARAM,
                rffi.cast(roci.dvoidp, numptr),
                lltype.nullptr(roci.Ptr(roci.ub4).TO),
                roci.OCI_ATTR_NUM_TYPE_ATTRS,
                self.environment.errorHandle)
            self.environment.checkForError(
                status, "ObjectType_Describe(): get number of attributes")
            numAttributes = numptr[0]
        finally:
            lltype.free(numptr, flavor='raw')

        # allocate the attribute list and dictionary
        self.attributes = []
        self.attributesByName = {}

        # acquire the list parameter descriptor
        listptr = lltype.malloc(roci.Ptr(roci.OCIParam).TO,
                               1, flavor='raw')
        try:
            status = roci.OCIAttrGet(
                toplevelParam, roci.OCI_DTYPE_PARAM,
                rffi.cast(roci.dvoidp, listptr),
                lltype.nullptr(roci.Ptr(roci.ub4).TO),
                roci.OCI_ATTR_LIST_TYPE_ATTRS,
                self.environment.errorHandle)
            self.environment.checkForError(
                status, "ObjectType_Describe(): get list parameter descriptor")
            attributeListParam = listptr[0]
        finally:
            lltype.free(listptr, flavor='raw')

        # create attribute information for each attribute
        for i in range(numAttributes):
            paramptr = lltype.malloc(roci.Ptr(roci.OCIParam).TO,
                                    1, flavor='raw')
            try:
                status = roci.OCIParamGet(
                    attributeListParam, roci.OCI_DTYPE_PARAM,
                    self.environment.errorHandle,
                    paramptr, i + 1)
                self.environment.checkForError(
                    status,
                    "ObjectType_Describe(): get attribute param descriptor")
                attribute = W_ObjectAttribute(connection, paramptr[0])
            finally:
                lltype.free(paramptr, flavor='raw')

            self.attributes.append(attribute)
            self.attributesByName[attribute.name] = attribute

    def get_attributes(self, space):
        return space.newlist([space.wrap(attr) for attr in self.attributes])

W_ObjectType.typedef = TypeDef(
    'ObjectType',
    schema = interp_attrproperty('schema', W_ObjectType),
    name = interp_attrproperty('name', W_ObjectType),
    attributes = GetSetProperty(W_ObjectType.get_attributes),
    )

class W_ObjectAttribute(Wrappable):
    def __init__(self, connection, param):
        self.initialize(connection, param)

    def initialize(self, connection, param):
        # determine the name of the attribute
        nameptr = lltype.malloc(rffi.CArrayPtr(roci.oratext).TO, 1,
                                flavor='raw')
        lenptr = lltype.malloc(rffi.CArrayPtr(roci.ub4).TO, 1,
                               flavor='raw')
        try:
            status = roci.OCIAttrGet(
                param, roci.OCI_DTYPE_PARAM,
                rffi.cast(roci.dvoidp, nameptr),
                lenptr,
                roci.OCI_ATTR_NAME,
                connection.environment.errorHandle)
            connection.environment.checkForError(
                status,
                "ObjectAttribute_Initialize(): get name")
            self.name = rffi.charpsize2str(nameptr[0], rffi.cast(lltype.Signed, lenptr[0]))
        finally:
            lltype.free(nameptr, flavor='raw')
            lltype.free(lenptr, flavor='raw')

        # determine the type of the attribute
        typecodeptr = lltype.malloc(roci.Ptr(roci.OCITypeCode).TO,
                                    1, flavor='raw')
        try:
            status = roci.OCIAttrGet(
                param, roci.OCI_DTYPE_PARAM,
                rffi.cast(roci.dvoidp, typecodeptr),
                lltype.nullptr(roci.Ptr(roci.ub4).TO),
                roci.OCI_ATTR_TYPECODE,
                connection.environment.errorHandle)
            connection.environment.checkForError(
                status, "ObjectType_Describe(): get type code")
            self.typeCode = rffi.cast(lltype.Signed, typecodeptr[0])
        finally:
            lltype.free(typecodeptr, flavor='raw')

        # if the type of the attribute is object, recurse
        if self.typeCode in (roci.OCI_TYPECODE_NAMEDCOLLECTION,
                             roci.OCI_TYPECODE_OBJECT):
            self.subType = W_ObjectType(connection, param)
        else:
            self.subType = None

W_ObjectAttribute.typedef = TypeDef(
    'ObjectAttribute',
    name = interp_attrproperty('name', W_ObjectAttribute),
    )

class W_ExternalObject(Wrappable):
    def __init__(self, var, objectType, instance, indicator,
                 isIndependent=True):
        self.var = var # keepalive
        self.objectType = objectType
        self.instance = instance
        self.indicator = indicator
        self.isIndependent = isIndependent

    @unwrap_spec(attr=str)
    def getattr(self, space, attr):
        try:
            attribute = self.objectType.attributesByName[attr]
        except KeyError:
            msg = "ExternalObject has no attribute '%s'" %(attr,)
            raise OperationError(space.w_AttributeError, space.wrap(msg))

        environment = self.objectType.environment

        scalarvalueindicatorptr = lltype.malloc(rffi.CArrayPtr(roci.OCIInd).TO,
                                                1, flavor='raw')
        valueindicatorptr = lltype.malloc(rffi.CArrayPtr(roci.dvoidp).TO,
                                          1, flavor='raw')
        valueptr = lltype.malloc(rffi.CArrayPtr(roci.dvoidp).TO,
                                 1, flavor='raw')
        tdoptr = lltype.malloc(rffi.CArrayPtr(roci.OCIType).TO,
                               1, flavor='raw')
        nameptr = lltype.malloc(rffi.CArrayPtr(roci.oratext).TO,
                               1, flavor='raw')
        nameptr[0] = rffi.str2charp(attr)
        namelenptr = lltype.malloc(rffi.CArrayPtr(roci.ub4).TO,
                                   1, flavor='raw')
        namelenptr[0] = rffi.cast(roci.ub4, len(attr))

        try:
            status = roci.OCIObjectGetAttr(
                environment.handle,
                environment.errorHandle,
                self.instance,
                self.indicator,
                self.objectType.tdo,
                nameptr, namelenptr, 1,
                lltype.nullptr(roci.Ptr(roci.ub4).TO), 0,
                scalarvalueindicatorptr,
                valueindicatorptr,
                valueptr,
                tdoptr)
            environment.checkForError(
                status, "ExternalObject_GetAttributeValue(): getting value")

            # determine the proper null indicator
            valueIndicator = valueindicatorptr[0]
            if not valueIndicator:
                valueIndicator = rffi.cast(roci.dvoidp,
                                           scalarvalueindicatorptr)
            value = valueptr[0]

            return convertObject(
                space, environment,
                attribute.typeCode,
                value, valueIndicator,
                self, attribute.subType)
        finally:
            lltype.free(scalarvalueindicatorptr, flavor='raw')
            lltype.free(valueindicatorptr, flavor='raw')
            lltype.free(valueptr, flavor='raw')
            lltype.free(tdoptr, flavor='raw')
            rffi.free_charp(nameptr[0])
            lltype.free(nameptr, flavor='raw')
            lltype.free(namelenptr, flavor='raw')

W_ExternalObject.typedef = TypeDef(
    'ExternalObject',
    type = interp_attrproperty('objectType', W_ExternalObject),
    __getattr__ = interp2app(W_ExternalObject.getattr),
    )

def convertObject(space, environment, typeCode,
                  value, indicator, var, subtype):

    # null values returned as None
    if (rffi.cast(lltype.Signed,
                  rffi.cast(roci.Ptr(roci.OCIInd),
                            indicator)[0])
        ==
        rffi.cast(lltype.Signed, roci.OCI_IND_NULL)):
        return space.w_None

    if typeCode in (roci.OCI_TYPECODE_CHAR,
                    roci.OCI_TYPECODE_VARCHAR,
                    roci.OCI_TYPECODE_VARCHAR2):
        strValue = rffi.cast(roci.Ptr(roci.OCIString), value)[0]
        ptr = roci.OCIStringPtr(environment.handle, strValue)
        size = roci.OCIStringSize(environment.handle, strValue)
        return config.w_string(space, ptr, rffi.cast(lltype.Signed, size))
    elif typeCode == roci.OCI_TYPECODE_NUMBER:
        return transform.OracleNumberToPythonFloat(
            environment,
            rffi.cast(roci.Ptr(roci.OCINumber), value))
    elif typeCode == roci.OCI_TYPECODE_DATE:
        dateValue = rffi.cast(roci.Ptr(roci.OCIDate), value)
        return transform.OracleDateToPythonDateTime(environment, dateValue)
    elif typeCode == roci.OCI_TYPECODE_TIMESTAMP:
        dateValue = rffi.cast(roci.Ptr(roci.OCIDateTime), value)
        return transform.OracleTimestampToPythonDate(environment, dateValue)
    elif typeCode == roci.OCI_TYPECODE_OBJECT:
        return space.wrap(W_ExternalObject(var, subtype, value, indicator,
                                           isIndependent=False))
    elif typeCode == roci.OCI_TYPECODE_NAMEDCOLLECTION:
        return convertCollection(space, environment, value, var, subtype)

    raise OperationError(
        get(space).w_NotSupportedError,
        space.wrap(
            "ExternalObjectVar_GetAttributeValue(): unhandled data type %d" % (
                typeCode,)))


def convertCollection(space, environment, value, var, objectType):
    "Convert a collection to a Python list"

    result_w = []

    iterptr = lltype.malloc(rffi.CArrayPtr(roci.OCIIter).TO, 1, flavor='raw')
    try:
        # create the iterator
        status = roci.OCIIterCreate(
            environment.handle,
            environment.errorHandle,
            value,
            iterptr)
        environment.checkForError(
            status, "ExternalObjectVar_ConvertCollection(): creating iterator")

        try:
            # create the result list
            valueptr = lltype.malloc(rffi.CArrayPtr(roci.dvoidp).TO,
                                     1, flavor='raw')
            indicatorptr = lltype.malloc(rffi.CArrayPtr(roci.dvoidp).TO,
                                         1, flavor='raw')
            eofptr = lltype.malloc(rffi.CArrayPtr(roci.boolean).TO,
                                   1, flavor='raw')
            try:
                while True:
                    status = roci.OCIIterNext(
                        environment.handle,
                        environment.errorHandle,
                        iterptr[0],
                        valueptr,
                        indicatorptr,
                        eofptr)
                    environment.checkForError(
                        status,
                        "ExternalObjectVar_ConvertCollection(): get next")

                    if rffi.cast(lltype.Signed, eofptr[0]):
                        break
                    element = convertObject(
                        space, environment,
                        objectType.elementTypeCode,
                        valueptr[0], indicatorptr[0],
                        var, objectType.elementType)
                    result_w.append(element)
            finally:
                lltype.free(valueptr, flavor='raw')
                lltype.free(indicatorptr, flavor='raw')
                lltype.free(eofptr, flavor='raw')

        finally:
            roci.OCIIterDelete(
                environment.handle,
                environment.errorHandle,
                iterptr)
    finally:
        lltype.free(iterptr, flavor='raw')

    return space.newlist(result_w)

