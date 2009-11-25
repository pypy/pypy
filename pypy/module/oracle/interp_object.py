from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.typedef import TypeDef, interp_attrproperty
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.module.oracle import roci

class W_ObjectType(Wrappable):
    def __init__(self, connection, param):
        self.environment = connection.environment
        self.isCollection = False
        self.initialize(connection, param)

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
            self.schema = rffi.charpsize2str(nameptr[0], lenptr[0])

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
            self.name = rffi.charpsize2str(nameptr[0], lenptr[0])
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
            pass
            #self.describe(connection, describeHandle)
        finally:
            roci.OCIHandleFree(describeHandle, roci.OCI_HTYPE_DESCRIBE)
W_ObjectType.typedef = TypeDef(
    'ObjectType',
    schema = interp_attrproperty('schema', W_ObjectType),
    name = interp_attrproperty('name', W_ObjectType),
    )

class W_ExternalObject(Wrappable):
    def __init__(self, ref, type, instance, indicator, isIndependent=True):
        self.ref = ref
        self.type = type
        self.instance = instance
        self.indicator = indicator
        self.isIndependent = isIndependent
W_ExternalObject.typedef = TypeDef(
    'ExternalObject',
    type = interp_attrproperty('type', W_ExternalObject),
    )
