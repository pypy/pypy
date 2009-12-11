from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.gateway import ObjSpace, W_Root, NoneNotWrapped
from pypy.interpreter.argument import Arguments
from pypy.interpreter.typedef import TypeDef, GetSetProperty
from pypy.interpreter.typedef import interp_attrproperty, interp_attrproperty_w
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.error import OperationError
from pypy.rpython.lltypesystem import rffi, lltype

from pypy.module.oracle import roci, interp_error
from pypy.module.oracle.config import w_string, string_w, StringBuffer
from pypy.module.oracle import interp_variable
from pypy.module.oracle.interp_error import get

# XXX are those "assert isinstance(xxx, interp_variable.W_Variable)" necessary?
# the bindList should annotate to SomeList(SomeInstance(W_Variable))

class W_Cursor(Wrappable):
    def __init__(self, space, connection):
        self.connection = connection
        self.environment = connection.environment

        self.w_statement = None
        self.statementType = -1
        self.handle = lltype.nullptr(roci.OCIStmt.TO)
        self.isOpen = True
        self.isOwned = False

        self.setInputSizes = False
        self.arraySize = 50
        self.fetchArraySize = 50
        self.bindArraySize = 1
        self.bindList = None
        self.bindDict = None
        self.numbersAsStrings = False
        self.outputSize = -1
        self.outputSizeColumn = -1

        self.w_inputTypeHandler = None
        self.w_outputTypeHandler = None
        self.w_rowFactory = None

    def execute(self, space, w_stmt, __args__):
        args_w, kw_w = __args__.unpack()

        if space.is_w(w_stmt, space.w_None):
            w_stmt = None

        if len(args_w) > 1:
            raise OperationError(
                space.w_TypeError,
                space.wrap("Too many arguments"))
        elif len(args_w) == 1:
            if len(kw_w) > 0:
                raise OperationError(
                    interp_error.get(space).w_InterfaceError,
                    space.wrap(
                        "expecting argument or keyword arguments, not both"))
            w_vars = args_w[0]
        elif len(kw_w) > 0:
            w_vars = space.newdict()
            for key, w_value in kw_w.iteritems():
                space.setitem(w_vars, space.wrap(key), w_value)
        else:
            w_vars = None

        # make sure the cursor is open
        self._checkOpen(space)

        return self._execute(space, w_stmt, w_vars)
    execute.unwrap_spec = ['self', ObjSpace, W_Root, Arguments]

    def prepare(self, space, w_stmt, w_tag=None):
        # make sure the cursor is open
        self._checkOpen(space)

        # prepare the statement
        self._internalPrepare(space, w_stmt, w_tag)
    prepare.unwrap_spec = ['self', ObjSpace, W_Root, W_Root]

    def _execute(self, space, w_stmt, w_vars):

        # prepare the statement, if applicable
        self._internalPrepare(space, w_stmt, None)

        # perform binds
        if w_vars is None:
            pass
        elif space.is_true(space.isinstance(w_vars, space.w_dict)):
            self._setBindVariablesByName(space, w_vars, 1, 0, 0)
        else:
            self._setBindVariablesByPos(space, w_vars, 1, 0, 0)
        self._performBind(space)

        # execute the statement
        isQuery = self.statementType == roci.OCI_STMT_SELECT
        if isQuery:
            numIters = 0
        else:
            numIters = 1
        self._internalExecute(space, numIters=numIters)

        # perform defines, if necessary
        if isQuery and self.fetchVariables is None:
            self._performDefine()

        # reset the values of setoutputsize()
        self.outputSize = -1
        self.outputSizeColumn = -1

        # for queries, return the cursor for convenience
        if isQuery:
            return space.wrap(self)

        # for all other statements, simply return None
        return space.w_None

    def executemany(self, space, w_stmt, w_list_of_args):
        if space.is_w(w_stmt, space.w_None):
            w_stmt = None
        if not space.is_true(space.isinstance(w_list_of_args, space.w_list)):
            raise OperationError(
                space.w_TypeError,
                space.wrap("list expected"))

        # make sure the cursor is open
        self._checkOpen(space)

        # prepare the statement
        self._internalPrepare(space, w_stmt, None)

        # queries are not supported as the result is undefined
        if self.statementType == roci.OCI_STMT_SELECT:
            raise OperationError(
                get(space).w_NotSupportedError,
                space.wrap("queries not supported: results undefined"))

        # perform binds
        args_w = space.listview(w_list_of_args)
        numrows = len(args_w)
        for i in range(numrows):
            w_arguments = args_w[i]
            deferred = i < numrows - 1
            if space.is_true(space.isinstance(w_arguments, space.w_dict)):
                self._setBindVariablesByName(
                    space, w_arguments, numrows, i, deferred)
            else:
                self._setBindVariablesByPos(
                    space, w_arguments, numrows, i, deferred)
        self._performBind(space)

        # execute the statement, but only if the number of rows is greater than
        # zero since Oracle raises an error otherwise
        if numrows > 0:
            self._internalExecute(space, numIters=numrows)
    executemany.unwrap_spec = ['self', ObjSpace, W_Root, W_Root]

    def close(self, space):
        # make sure we are actually open
        self._checkOpen(space)

        # close the cursor
        self.freeHandle(space, raiseError=True)

        self.isOpen = False
        self.handle = lltype.nullptr(roci.OCIStmt.TO)
    close.unwrap_spec = ['self', ObjSpace]

    def callfunc(self, space, name, w_returnType, w_parameters=None):
        retvar = interp_variable.newVariableByType(space, self, w_returnType, 1)
        if space.is_w(w_parameters, space.w_None):
            w_parameters = None

        self._call(space, name, retvar, w_parameters)

        # determine the results
        return retvar.getValue(space, 0)
    callfunc.unwrap_spec = ['self', ObjSpace, str, W_Root, W_Root]

    def callproc(self, space, name, w_parameters=None):
        if space.is_w(w_parameters, space.w_None):
            w_parameters = None

        self._call(space, name, None, w_parameters)

        # create the return value
        ret_w = []
        if self.bindList:
            for v in self.bindList:
                assert isinstance(v, interp_variable.W_Variable)
                ret_w.append(v.getValue(space, 0))
        return space.newlist(ret_w)

    callproc.unwrap_spec = ['self', ObjSpace, str, W_Root]

    def _call(self, space, name, retvar, w_args):
        # determine the number of arguments passed
        if w_args:
            numArguments = space.int_w(space.len(w_args))
        else:
            numArguments = 0

        # make sure we are actually open
        self._checkOpen(space)

        # add the return value, if applicable
        if retvar:
            offset = 1
            w_vars = space.newlist([retvar])
            if w_args:
                space.call_method(w_vars, "extend", w_args)
        else:
            offset = 0
            w_vars = w_args

        # build up the statement
        args = ', '.join([':%d' % (i + offset + 1,)
                          for i in range(numArguments)])
        if retvar:
            stmt = "begin :1 := %s(%s); end;" % (name, args)
        else:
            stmt = "begin %s(%s); end;" % (name, args)

        self._execute(space, space.wrap(stmt), w_vars)

    def _checkOpen(self, space):
        if not self.isOpen:
            raise OperationError(
                interp_error.get(space).w_InterfaceError,
                space.wrap("not open"))

    def allocateHandle(self):
        handleptr = lltype.malloc(rffi.CArrayPtr(roci.OCIStmt).TO,
                                  1, flavor='raw')
        try:
            status = roci.OCIHandleAlloc(
                self.environment.handle,
                handleptr, roci.OCI_HTYPE_STMT, 0,
                lltype.nullptr(rffi.CArray(roci.dvoidp)))
            self.environment.checkForError(
                status, "Cursor_New()")
            self.handle = handleptr[0]
        finally:
            lltype.free(handleptr, flavor='raw')
        self.isOwned = True

    def freeHandle(self, space, raiseError=True):
        if not self.handle:
            return
        if self.isOwned:
            roci.OCIHandleFree(self.handle, roci.OCI_HTYPE_STMT)
        elif self.connection.handle:
            tagBuffer = StringBuffer()
            tagBuffer.fill(space, self.w_statementTag)
            try:
                status = roci.OCIStmtRelease(
                    self.handle, self.environment.errorHandle,
                    tagBuffer.ptr, tagBuffer.size,
                    roci.OCI_DEFAULT)
                self.environment.checkForError(
                    status, "Cursor_FreeHandle()")
            finally:
                tagBuffer.clear()

    def _internalPrepare(self, space, w_stmt, w_tag):
        # make sure we don't get a situation where nothing is to be executed
        if w_stmt is None and self.w_statement is None:
            raise OperationError(
                interp_error.get(space).w_ProgrammingError,
                space.wrap("no statement specified "
                           "and no prior statement prepared"))

        # nothing to do if the statement is identical to the one already stored
        # but go ahead and prepare anyway for create, alter and drop statments
        if w_stmt is None or w_stmt == self.w_statement:
            if self.statementType not in (roci.OCI_STMT_CREATE,
                                          roci.OCI_STMT_DROP,
                                          roci.OCI_STMT_ALTER):
                return
            w_stmt = self.w_statement
        else:
            self.w_statement = w_stmt

        # release existing statement, if necessary
        self.w_statementTag = w_tag
        self.freeHandle(space)

        # prepare statement
        self.isOwned = False
        handleptr = lltype.malloc(roci.Ptr(roci.OCIStmt).TO,
                                  1, flavor='raw')
        stmtBuffer = StringBuffer()
        tagBuffer = StringBuffer()
        stmtBuffer.fill(space, w_stmt)
        tagBuffer.fill(space, w_tag)
        try:
            status = roci.OCIStmtPrepare2(
                self.connection.handle, handleptr,
                self.environment.errorHandle,
                stmtBuffer.ptr, stmtBuffer.size,
                tagBuffer.ptr, tagBuffer.size,
                roci.OCI_NTV_SYNTAX, roci.OCI_DEFAULT)

            self.environment.checkForError(
                status, "Connection_InternalPrepare(): prepare")
            self.handle = handleptr[0]
        finally:
            lltype.free(handleptr, flavor='raw')
            stmtBuffer.clear()
            tagBuffer.clear()

        # clear bind variables, if applicable
        if not self.setInputSizes:
            self.bindList = None
            self.bindDict = None

        # clear row factory, if applicable
        self.rowFactory = None

        # determine if statement is a query
        self._getStatementType()

    def _setErrorOffset(self, space, e):
        if e.match(space, get(space).w_DatabaseError):
            attrptr = lltype.malloc(rffi.CArrayPtr(roci.ub4).TO, 1, flavor='raw')
            try:
                status = roci.OCIAttrGet(
                    self.handle, roci.OCI_HTYPE_STMT,
                    rffi.cast(roci.dvoidp, attrptr),
                    lltype.nullptr(roci.Ptr(roci.ub4).TO),
                    roci.OCI_ATTR_PARSE_ERROR_OFFSET,
                    self.environment.errorHandle)
                e.offset = attrptr[0]
            finally:
                lltype.free(attrptr, flavor='raw')

    def _internalExecute(self, space, numIters):
        if self.connection.autocommit:
            mode = roci.OCI_COMMIT_ON_SUCCESS
        else:
            mode = roci.OCI_DEFAULT

        status = roci.OCIStmtExecute(
            self.connection.handle,
            self.handle,
            self.environment.errorHandle,
            numIters, 0,
            lltype.nullptr(roci.OCISnapshot.TO),
            lltype.nullptr(roci.OCISnapshot.TO),
            mode)
        try:
            self.environment.checkForError(
                status, "Cursor_InternalExecute()")
        except OperationError, e:
            self._setErrorOffset(space, e)
            raise
        finally:
            self._setRowCount()

    def _getStatementType(self):
        attrptr = lltype.malloc(rffi.CArrayPtr(roci.ub2).TO, 1, flavor='raw')
        try:
            status = roci.OCIAttrGet(
                self.handle, roci.OCI_HTYPE_STMT,
                rffi.cast(roci.dvoidp, attrptr),
                lltype.nullptr(roci.Ptr(roci.ub4).TO),
                roci.OCI_ATTR_STMT_TYPE,
                self.environment.errorHandle)

            self.environment.checkForError(
                status, "Cursor_GetStatementType()")
            self.statementType = rffi.cast(lltype.Signed, attrptr[0])
        finally:
            lltype.free(attrptr, flavor='raw')

        self.fetchVariables = None

    def getDescription(space, self):
        "Return a list of 7-tuples consisting of the description of "
        "the define variables"

        # make sure the cursor is open
        self._checkOpen(space)

        # fixup bound cursor, if necessary
        self._fixupBoundCursor()

        # if not a query, return None
        if self.statementType != roci.OCI_STMT_SELECT:
            return

        # determine number of items in select-list
        attrptr = lltype.malloc(rffi.CArrayPtr(roci.ub1).TO, 1, flavor='raw')
        try:
            status = roci.OCIAttrGet(
                self.handle, roci.OCI_HTYPE_STMT,
                rffi.cast(roci.dvoidp, attrptr),
                lltype.nullptr(roci.Ptr(roci.ub4).TO),
                roci.OCI_ATTR_PARAM_COUNT,
                self.environment.errorHandle)
            self.environment.checkForError(
                status,
                "Cursor_GetDescription()")
            numItems = attrptr[0]
        finally:
            lltype.free(attrptr, flavor='raw')

        return space.newlist(
            [space.newtuple(self._itemDescription(space, i + 1))
             for i in range(numItems)])

    def _itemDescription(self, space, pos):
        "Return a tuple describing the item at the given position"

        # acquire parameter descriptor
        paramptr = lltype.malloc(roci.Ptr(roci.OCIParam).TO,
                                 1, flavor='raw')
        try:
            status = roci.OCIParamGet(
                self.handle, roci.OCI_HTYPE_STMT,
                self.environment.errorHandle,
                rffi.cast(roci.dvoidpp, paramptr),
                pos)
            self.environment.checkForError(
                status,
                "Cursor_GetDescription(): parameter")
            param = paramptr[0]
        finally:
            lltype.free(paramptr, flavor='raw')

        try:
            # acquire usable type of item
            varType = interp_variable.typeByOracleDescriptor(
                param, self.environment)

            # acquire internal size of item
            attrptr = lltype.malloc(rffi.CArrayPtr(roci.ub2).TO, 1,
                                    flavor='raw')
            try:
                status = roci.OCIAttrGet(
                    param, roci.OCI_HTYPE_DESCRIBE,
                    rffi.cast(roci.dvoidp, attrptr),
                    lltype.nullptr(roci.Ptr(roci.ub4).TO),
                    roci.OCI_ATTR_DATA_SIZE,
                    self.environment.errorHandle)
                self.environment.checkForError(
                    status,
                    "Cursor_ItemDescription(): internal size")
                internalSize = rffi.cast(lltype.Signed, attrptr[0])
            finally:
                lltype.free(attrptr, flavor='raw')

            # acquire name of item
            nameptr = lltype.malloc(rffi.CArrayPtr(roci.oratext).TO, 1,
                                    flavor='raw')
            lenptr = lltype.malloc(rffi.CArrayPtr(roci.ub4).TO, 1,
                                    flavor='raw')
            try:
                status = roci.OCIAttrGet(
                    param, roci.OCI_HTYPE_DESCRIBE,
                    rffi.cast(roci.dvoidp, nameptr),
                    lenptr,
                    roci.OCI_ATTR_NAME,
                    self.environment.errorHandle)
                self.environment.checkForError(
                    status,
                    "Cursor_ItemDescription(): name")
                name = rffi.charpsize2str(nameptr[0], lenptr[0])
            finally:
                lltype.free(nameptr, flavor='raw')
                lltype.free(lenptr, flavor='raw')

            # lookup precision and scale
            if varType is interp_variable.VT_Float:
                attrptr = lltype.malloc(rffi.CArrayPtr(roci.sb1).TO, 1,
                                        flavor='raw')
                try:
                    status = roci.OCIAttrGet(
                        param, roci.OCI_HTYPE_DESCRIBE,
                        rffi.cast(roci.dvoidp, attrptr),
                        lltype.nullptr(roci.Ptr(roci.ub4).TO),
                        roci.OCI_ATTR_SCALE,
                        self.environment.errorHandle)
                    self.environment.checkForError(
                        status,
                        "Cursor_ItemDescription(): scale")
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
                        self.environment.errorHandle)
                    self.environment.checkForError(
                        status,
                        "Cursor_ItemDescription(): precision")
                    precision = rffi.cast(lltype.Signed, attrptr[0])
                finally:
                    lltype.free(attrptr, flavor='raw')
            else:
                scale = 0
                precision = 0

            # lookup whether null is permitted for the attribute
            attrptr = lltype.malloc(rffi.CArrayPtr(roci.ub1).TO, 1,
                                    flavor='raw')
            try:
                status = roci.OCIAttrGet(
                    param, roci.OCI_HTYPE_DESCRIBE,
                    rffi.cast(roci.dvoidp, attrptr),
                    lltype.nullptr(roci.Ptr(roci.ub4).TO),
                    roci.OCI_ATTR_IS_NULL,
                    self.environment.errorHandle)
                self.environment.checkForError(
                    status,
                    "Cursor_ItemDescription(): nullable")
                nullable = rffi.cast(lltype.Signed, attrptr[0]) != 0
            finally:
                lltype.free(attrptr, flavor='raw')

            # set display size based on data type
            if varType is interp_variable.VT_String:
                displaySize = internalSize
            elif varType is interp_variable.VT_NationalCharString:
                displaySize = internalSize / 2
            elif varType is interp_variable.VT_Binary:
                displaySize = internalSize
            elif varType is interp_variable.VT_FixedChar:
                displaySize = internalSize
            elif varType is interp_variable.VT_FixedNationalChar:
                displaySize = internalSize / 2
            elif varType is interp_variable.VT_Float:
                if precision:
                    displaySize = precision + 1
                    if scale > 0:
                        displaySize += scale + 1
                else:
                    displaySize = 127
            elif varType is interp_variable.VT_DateTime:
                displaySize = 23
            else:
                displaySize = -1

            # return the tuple
            return [space.wrap(name), space.gettypeobject(varType.typedef),
                    space.wrap(displaySize), space.wrap(internalSize),
                    space.wrap(precision), space.wrap(scale),
                    space.wrap(nullable)]

        finally:
            roci.OCIDescriptorFree(param, roci.OCI_DTYPE_PARAM)

    def _setBindVariablesByPos(self, space,
                               w_vars, numElements, arrayPos, defer):
        "handle positional binds"
        # make sure positional and named binds are not being intermixed
        if self.bindDict is not None:
            raise OperationError(
                get(space).w_ProgrammingError,
                space.wrap("positional and named binds cannot be intermixed"))

        if self.bindList is None:
            self.bindList = []

        vars_w = space.fixedview(w_vars)
        for i in range(len(vars_w)):
            w_value = vars_w[i]
            if i < len(self.bindList):
                origVar = self.bindList[i]
                if space.is_w(origVar, space.w_None):
                    origVar = None
            else:
                origVar = None
            newVar = self._setBindVariableHelper(space, w_value, origVar,
                                                 numElements, arrayPos, defer)
            if newVar:
                if i < len(self.bindList):
                    self.bindList[i] = newVar
                else:
                    assert i == len(self.bindList)
                    self.bindList.append(newVar)

    def _setBindVariablesByName(self, space,
                                w_vars, numElements, arrayPos, defer):
        "handle named binds"
        # make sure positional and named binds are not being intermixed
        if self.bindList is not None:
            raise OperationError(
                get(space).w_ProgrammingError,
                space.wrap("positional and named binds cannot be intermixed"))

        if self.bindDict is None:
            self.bindDict = space.newdict()

        items = space.fixedview(space.call_method(w_vars, "iteritems"))
        for item in items:
            w_key, w_value = space.fixedview(item, 2)
            origVar = space.finditem(self.bindDict, w_key)
            newVar = self._setBindVariableHelper(space, w_value, origVar,
                                                 numElements, arrayPos, defer)
            if newVar:
                space.setitem(self.bindDict, w_key, newVar)

    def _setBindVariableHelper(self, space, w_value, origVar,
                               numElements, arrayPos, defer):

        valueIsVariable = space.is_true(space.isinstance(w_value, get(space).w_Variable))
        newVar = None

        # handle case where variable is already bound
        if origVar:
            assert isinstance(origVar, interp_variable.W_Variable)

            # if the value is a variable object, rebind it if necessary
            if valueIsVariable:
                newVar = space.interp_w(interp_variable.W_Variable, w_value)
                assert isinstance(newVar, interp_variable.W_Variable)
                if newVar == origVar:
                    newVar = None

            # if the number of elements has changed, create a new variable
            # this is only necessary for executemany() since execute() always
            # passes a value of 1 for the number of elements
            elif numElements > origVar.allocatedElements:
                newVar = origVar.clone(
                    self, numElements, origVar.size)
                assert isinstance(newVar, interp_variable.W_Variable)
                newVar.setValue(space, arrayPos, w_value)

            # otherwise, attempt to set the value
            else:
                try:
                    origVar.setValue(space, arrayPos, w_value)
                except OperationError, e:
                    # executemany() should simply fail after the first element
                    if arrayPos > 0:
                        raise
                    # anything other than IndexError or TypeError should fail
                    if (not e.match(space, space.w_IndexError) and
                        not e.match(space, space.w_TypeError)):
                        raise
                    # catch the exception and try to create a new variable
                    origVar = None

        if not origVar:
            # if the value is a variable object, bind it directly
            if valueIsVariable:
                newVar = space.interp_w(interp_variable.W_Variable, w_value)
                assert isinstance(newVar, interp_variable.W_Variable)
                newVar.boundPos = 0
                newVar.boundName = None

            # otherwise, create a new variable, unless the value is None and
            # we wish to defer type assignment
            elif not space.is_w(w_value, space.w_None) or not defer:
                newVar = interp_variable.newVariableByValue(space, self,
                                                            w_value,
                                                            numElements)
                assert isinstance(newVar, interp_variable.W_Variable)
                newVar.setValue(space, arrayPos, w_value)

        assert newVar is None or isinstance(newVar, interp_variable.W_Variable)
        return newVar

    def _performBind(self, space):
        # set values and perform binds for all bind variables
        if self.bindList:
            for i in range(len(self.bindList)):
                var = self.bindList[i]
                assert isinstance(var, interp_variable.W_Variable)
                var.bind(space, self, None, i + 1)
        if self.bindDict:
            items_w = space.fixedview(
                space.call_method(self.bindDict, "iteritems"))
            for w_item in items_w:
                w_key, var = space.fixedview(w_item, 2)
                assert isinstance(var, interp_variable.W_Variable)
                var.bind(space, self, w_key, 0)

        # ensure that input sizes are reset
        self.setInputSizes = False

    def _setRowCount(self):
        if self.statementType == roci.OCI_STMT_SELECT:
            self.rowCount = 0
            self.actualRows = -1
            self.rowNum = 0
        elif self.statementType in (roci.OCI_STMT_INSERT,
                                    roci.OCI_STMT_UPDATE,
                                    roci.OCI_STMT_DELETE):
            attrptr = lltype.malloc(rffi.CArrayPtr(roci.ub4).TO,
                                    1, flavor='raw')
            try:
                status = roci.OCIAttrGet(
                    self.handle, roci.OCI_HTYPE_STMT,
                    rffi.cast(roci.dvoidp, attrptr),
                    lltype.nullptr(roci.Ptr(roci.ub4).TO),
                    roci.OCI_ATTR_ROW_COUNT,
                    self.environment.errorHandle)

                self.environment.checkForError(
                    status, "Cursor_SetRowCount()")
                self.rowCount = rffi.cast(lltype.Signed, attrptr[0])
            finally:
                lltype.free(attrptr, flavor='raw')
        else:
            self.rowCount = -1

    def _performDefine(self):
        # determine number of items in select-list
        attrptr = lltype.malloc(rffi.CArrayPtr(roci.ub4).TO,
                                1, flavor='raw')
        try:
            status = roci.OCIAttrGet(
                self.handle, roci.OCI_HTYPE_STMT,
                rffi.cast(roci.dvoidp, attrptr),
                lltype.nullptr(roci.Ptr(roci.ub4).TO),
                roci.OCI_ATTR_PARAM_COUNT,
                self.environment.errorHandle)

            self.environment.checkForError(
                status, "Cursor_PerformDefine()")
            numParams = attrptr[0]
        finally:
            lltype.free(attrptr, flavor='raw')

        self.fetchVariables = []

        # define a variable for each select-item
        self.fetchArraySize = self.arraySize
        for i in range(numParams):
            var = interp_variable.define(self, i+1, self.fetchArraySize)
            assert isinstance(var, interp_variable.W_Variable)
            self.fetchVariables.append(var)

    def _verifyFetch(self, space):
        # make sure the cursor is open
        self._checkOpen(space)

        # fixup bound cursor, if necessary
        self._fixupBoundCursor()

        # make sure the cursor is for a query
        if self.statementType != roci.OCI_STMT_SELECT:
            raise OperationError(
                get(space).w_InterfaceError,
                space.wrap("not a query"))

    def _fixupBoundCursor(self):
        if self.handle and self.statementType < 0:
            self._getStatementType()
            if self.statementType == roci.OCI_STMT_SELECT:
                self._performDefine()
            self._setRowCount()

    def fetchone(self, space):
        # verify fetch can be performed
        self._verifyFetch(space)

        # setup return value
        if self._moreRows(space):
            return self._createRow(space)

        return space.w_None
    fetchone.unwrap_spec = ['self', ObjSpace]

    def fetchmany(self, space, w_numRows=NoneNotWrapped):
        if w_numRows is not None:
            numRows = space.int_w(w_numRows)
        else:
            numRows = self.arraySize

        # verify fetch can be performed
        self._verifyFetch(space)

        return self._multiFetch(space, limit=numRows)
    fetchmany.unwrap_spec = ['self', ObjSpace, W_Root]

    def fetchall(self, space):
        # verify fetch can be performed
        self._verifyFetch(space)

        return self._multiFetch(space, limit=0)
    fetchall.unwrap_spec = ['self', ObjSpace]

    def descr_iter(self, space):
        self._verifyFetch(space)
        return space.wrap(self)
    descr_iter.unwrap_spec = ['self', ObjSpace]

    def descr_next(self, space):
        # verify fetch can be performed
        self._verifyFetch(space)

        # setup return value
        if self._moreRows(space):
            return self._createRow(space)

        raise OperationError(space.w_StopIteration, space.w_None)
    descr_next.unwrap_spec = ['self', ObjSpace]

    def _moreRows(self, space):
        if self.rowNum < self.actualRows:
            return True
        if self.actualRows < 0 or self.actualRows == self.fetchArraySize:
            self._internalFetch(space, self.fetchArraySize)
        if self.rowNum < self.actualRows:
            return True

        return False

    def _internalFetch(self, space, numRows):
        if not self.fetchVariables:
            raise OperationError(
                get(space).w_InterfaceError,
                space.wrap("query not executed"))

        status = roci.OCIStmtFetch(
            self.handle,
            self.environment.errorHandle,
            numRows,
            roci.OCI_FETCH_NEXT,
            roci.OCI_DEFAULT)

        if status != roci.OCI_NO_DATA:
            self.environment.checkForError(
                status,
                "Cursor_InternalFetch(): fetch")

        for var in self.fetchVariables:
            assert isinstance(var, interp_variable.W_Variable)
            var.internalFetchNum += 1

        attrptr = lltype.malloc(rffi.CArrayPtr(roci.ub4).TO,
                                1, flavor='raw')
        try:
            status = roci.OCIAttrGet(
                self.handle, roci.OCI_HTYPE_STMT,
                rffi.cast(roci.dvoidp, attrptr),
                lltype.nullptr(roci.Ptr(roci.ub4).TO),
                roci.OCI_ATTR_ROW_COUNT,
                self.environment.errorHandle)

            self.environment.checkForError(
                status, "Cursor_InternalFetch(): row count")

            self.actualRows = (rffi.cast(lltype.Signed, attrptr[0])
                               - self.rowCount)
            self.rowNum = 0
        finally:
            lltype.free(attrptr, flavor='raw')

    def _multiFetch(self, space, limit=0):
        results_w = []
        rowNum = 0

        # fetch as many rows as possible
        while limit == 0 or rowNum < limit:
            rowNum += 1
            if not self._moreRows(space):
                break
            w_row = self._createRow(space)
            results_w.append(w_row)
        return space.newlist(results_w)

    def _createRow(self, space):
        items_w = []
        numItems = len(self.fetchVariables)

        # acquire the value for each item
        for var in self.fetchVariables:
            assert isinstance(var, interp_variable.W_Variable)
            w_item = var.getValue(space, self.rowNum)
            items_w.append(w_item)

        # increment row counters
        self.rowNum += 1
        self.rowCount += 1

        w_row = space.newtuple(items_w)

        # if a row factory is defined, call it
        if self.w_rowFactory:
            w_row = space.call(self.w_rowFactory, w_row)

        return w_row

    def _get_bind_info(self, space, numElements):
        # avoid bus errors on 64bit platforms
        numElements = numElements + (rffi.sizeof(roci.dvoidp) -
                                     numElements % rffi.sizeof(roci.dvoidp))
        # initialize the buffers
        bindNames = lltype.malloc(roci.Ptr(roci.oratext).TO,
                                  numElements, flavor='raw')
        bindNameLengths = lltype.malloc(roci.Ptr(roci.ub1).TO,
                                        numElements, flavor='raw')
        indicatorNames = lltype.malloc(roci.Ptr(roci.oratext).TO,
                                       numElements, flavor='raw')
        indicatorNameLengths = lltype.malloc(roci.Ptr(roci.ub1).TO,
                                             numElements, flavor='raw')
        duplicate = lltype.malloc(roci.Ptr(roci.ub1).TO,
                                  numElements, flavor='raw')
        bindHandles = lltype.malloc(roci.Ptr(roci.OCIBind).TO,
                                    numElements, flavor='raw')

        foundElementsPtr = lltype.malloc(roci.Ptr(roci.sb4).TO, 1,
                                         flavor='raw')

        try:
            status = roci.OCIStmtGetBindInfo(
                self.handle,
                self.environment.errorHandle,
                numElements,
                1,
                foundElementsPtr,
                bindNames, bindNameLengths,
                indicatorNames, indicatorNameLengths,
                duplicate, bindHandles)
            if status != roci.OCI_NO_DATA:
                self.environment.checkForError(
                    status, "Cursor_GetBindNames()")

            # Too few elements allocated
            foundElements = rffi.cast(lltype.Signed, foundElementsPtr[0])
            if foundElements < 0:
                return -foundElements, None

            names_w = []
            # process the bind information returned
            for i in range(foundElements):
                if rffi.cast(lltype.Signed, duplicate[i]):
                    continue
                names_w.append(
                    w_string(space,
                             bindNames[i],
                             rffi.cast(lltype.Signed, bindNameLengths[i])))

            return 0, names_w
        finally:
            lltype.free(bindNames, flavor='raw')
            lltype.free(bindNameLengths, flavor='raw')
            lltype.free(indicatorNames, flavor='raw')
            lltype.free(indicatorNameLengths, flavor='raw')
            lltype.free(duplicate, flavor='raw')
            lltype.free(bindHandles, flavor='raw')
            lltype.free(foundElementsPtr, flavor='raw')

    def bindnames(self, space):
        # make sure the cursor is open
        self._checkOpen(space)

        # ensure that a statement has already been prepared
        if not self.w_statement:
            raise OperationError(get(space).w_ProgrammingError,
                                 space.wrap("statement must be prepared first"))

        nbElements, names = self._get_bind_info(space, 8)
        if nbElements:
            _, names = self._get_bind_info(space, nbElements)
        return space.newlist(names)
    bindnames.unwrap_spec = ['self', ObjSpace]

    def var(self, space, w_type, size=0, w_arraysize=None,
            w_inconverter=None, w_outconverter=None):
        if space.is_w(w_arraysize, space.w_None):
            arraySize = self.bindArraySize
        else:
            arraySize = space.int_w(w_arraysize)

        # determine the type of variable
        varType = interp_variable.typeByPythonType(space, self, w_type)
        if varType.isVariableLength and size == 0:
            size = varType.size

        # create the variable
        var = varType(self, arraySize, size)
        var.w_inconverter = w_inconverter
        var.w_outconverter = w_outconverter

        return space.wrap(var)
    var.unwrap_spec = ['self', ObjSpace, W_Root, int, W_Root, W_Root, W_Root]

    def arrayvar(self, space, w_type, w_value, size=0):
        # determine the type of variable
        varType = interp_variable.typeByPythonType(space, self, w_type)
        if varType.isVariableLength and size == 0:
            size = varType.size

        # determine the number of elements to create
        if space.is_true(space.isinstance(w_value, space.w_list)):
            numElements = space.int_w(space.len(w_value))
        elif space.is_true(space.isinstance(w_value, space.w_int)):
            numElements = space.int_w(w_value)
        else:
            raise OperationError(
                get(space).w_NotSupportedError,
                space.wrap("expecting integer or list of values"))

        # create the variable
        var = varType(self, numElements, size)
        var.makeArray(space)

        # set the value, if applicable
        if space.is_true(space.isinstance(w_value, space.w_list)):
            var.setArrayValue(space, w_value)

        return var
    arrayvar.unwrap_spec = ['self', ObjSpace, W_Root, W_Root, int]

    def setinputsizes(self, space, __args__):
        args_w, kw_w = __args__.unpack()

        # only expect keyword arguments or positional arguments, not both
        if args_w and kw_w:
            raise OperationError(
                interp_error.get(space).w_InterfaceError,
                space.wrap(
                    "expecting argument or keyword arguments, not both"))

        # make sure the cursor is open
        self._checkOpen(space)

        # eliminate existing bind variables
        self.bindList = None
        self.bindDict = None

        self.setInputSizes = True

        # process each input
        if kw_w:
            self.bindDict = space.newdict()
            for key, w_value in kw_w.iteritems():
                var = interp_variable.newVariableByType(
                    space, self, w_value, self.bindArraySize)
                space.setitem(self.bindDict, space.wrap(key), var)
            return self.bindDict
        else:
            self.bindList = [None] * len(args_w)
            for i in range(len(args_w)):
                w_value = args_w[i]
                if space.is_w(w_value, space.w_None):
                    var = None
                else:
                    var = interp_variable.newVariableByType(
                        space, self, w_value, self.bindArraySize)
                self.bindList[i] = var
            return space.newlist(self.bindList)
    setinputsizes.unwrap_spec = ['self', ObjSpace, Arguments]

    def setoutputsize(self, space, outputSize, outputSizeColumn=-1):
        self.outputSize = outputSize
        self.outputSizeColumn = outputSizeColumn
    setoutputsize.unwrap_spec = ['self', ObjSpace, int, int]


    def arraysize_get(space, self):
        return space.wrap(self.arraySize)
    def arraysize_set(space, self, w_value):
        self.arraySize = space.int_w(w_value)

    def bindarraysize_get(space, self):
        return space.wrap(self.bindArraySize)
    def bindarraysize_set(space, self, w_value):
        self.bindArraySize = space.int_w(w_value)

    def bindvars_get(space, self):
        if self.bindList:
            return space.newlist(self.bindList)
        if self.bindDict:
            return self.bindDict

    def fetchvars_get(space, self):
        return space.newlist(self.fetchVariables)

W_Cursor.typedef = TypeDef(
    'Cursor',
    execute = interp2app(W_Cursor.execute),
    executemany = interp2app(W_Cursor.executemany),
    prepare = interp2app(W_Cursor.prepare),
    fetchone = interp2app(W_Cursor.fetchone),
    fetchmany = interp2app(W_Cursor.fetchmany),
    fetchall = interp2app(W_Cursor.fetchall),
    close = interp2app(W_Cursor.close),
    bindnames = interp2app(W_Cursor.bindnames),
    callfunc = interp2app(W_Cursor.callfunc),
    callproc = interp2app(W_Cursor.callproc),
    var = interp2app(W_Cursor.var),
    arrayvar = interp2app(W_Cursor.arrayvar),
    setinputsizes = interp2app(W_Cursor.setinputsizes),
    setoutputsize = interp2app(W_Cursor.setoutputsize),

    __iter__ = interp2app(W_Cursor.descr_iter),
    next = interp2app(W_Cursor.descr_next),

    arraysize = GetSetProperty(W_Cursor.arraysize_get,
                               W_Cursor.arraysize_set),
    bindarraysize = GetSetProperty(W_Cursor.bindarraysize_get,
                                   W_Cursor.bindarraysize_set),
    rowcount = interp_attrproperty('rowCount', W_Cursor),
    statement = interp_attrproperty_w('w_statement', W_Cursor),
    bindvars = GetSetProperty(W_Cursor.bindvars_get),
    fetchvars = GetSetProperty(W_Cursor.fetchvars_get),
    description = GetSetProperty(W_Cursor.getDescription),
)
