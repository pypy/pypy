"""
Implementation of a part of the standard Python opcodes.
The rest, dealing with variables in optimized ways, is in
pyfastscope.py and pynestedscope.py.
"""

from pypy.interpreter.baseobjspace import OperationError, NoValue
from pypy.interpreter.eval import UNDEFINED
from pypy.interpreter import baseobjspace, pyframe, gateway, function
from pypy.interpreter.miscutils import InitializedClass


class unaryoperation:
    def __init__(self, operationname):
        self.operationname = operationname
    def __call__(self, f):
        operation = getattr(f.space, self.operationname)
        w_1 = f.valuestack.pop()
        w_result = operation(w_1)
        f.valuestack.push(w_result)

class binaryoperation:
    def __init__(self, operationname):
        self.operationname = operationname
    def __call__(self, f):
        operation = getattr(f.space, self.operationname)
        w_2 = f.valuestack.pop()
        w_1 = f.valuestack.pop()
        w_result = operation(w_1, w_2)
        f.valuestack.push(w_result)


class PyInterpFrame(pyframe.PyFrame):
    """A PyFrame that knows about interpretation of standard Python opcodes
    minus the ones related to nested scopes."""
    
    ### opcode dispatch ###

    # 'dispatch_table' is a class attribute: a list of functions.
    # Currently, it is always created by setup_dispatch_table in pyopcode.py
    # but it could be a custom table.

    def dispatch(self):
        opcode = self.nextop()
        fn = self.dispatch_table[opcode]
        if fn.has_arg:
            oparg = self.nextarg()
            fn(self, oparg)

        else:
            fn(self)

    def nextop(self):
        c = self.code.co_code[self.next_instr]
        self.next_instr += 1
        return ord(c)

    def nextarg(self):
        lo = self.nextop()
        hi = self.nextop()
        return (hi<<8) + lo

    ### accessor functions ###

    def getlocalvarname(self, index):
        return self.code.co_varnames[index]

    def getconstant(self, index):
        return self.code.co_consts[index]

    def getname(self, index):
        return self.code.co_names[index]


    ################################################################
    ##  Implementation of the "operational" opcodes
    ##  See also pyfastscope.py and pynestedscope.py for the rest.
    ##
    
    #  the 'self' argument of opcode implementations is called 'f'
    #  for historical reasons

    def LOAD_FAST(f, varindex):
        # access a local variable directly
        w_value = f.fastlocals_w[varindex]
        if w_value is UNDEFINED:
            varname = f.getlocalvarname(varindex)
            message = "local variable '%s' referenced before assignment" % varname
            raise OperationError(f.space.w_UnboundLocalError, f.space.wrap(message))
        f.valuestack.push(w_value)

    def LOAD_CONST(f, constindex):
        w_const = f.space.wrap(f.getconstant(constindex))
        f.valuestack.push(w_const)

    def STORE_FAST(f, varindex):
        w_newvalue = f.valuestack.pop()
        f.fastlocals_w[varindex] = w_newvalue
        #except:
        #    print "exception: got index error"
        #    print " varindex:", varindex
        #    print " len(locals_w)", len(f.locals_w)
        #    import dis
        #    print dis.dis(f.code)
        #    print "co_varnames", f.code.co_varnames
        #    print "co_nlocals", f.code.co_nlocals
        #    raise

    def POP_TOP(f):
        f.valuestack.pop()

    def ROT_TWO(f):
        w_1 = f.valuestack.pop()
        w_2 = f.valuestack.pop()
        f.valuestack.push(w_1)
        f.valuestack.push(w_2)

    def ROT_THREE(f):
        w_1 = f.valuestack.pop()
        w_2 = f.valuestack.pop()
        w_3 = f.valuestack.pop()
        f.valuestack.push(w_1)
        f.valuestack.push(w_3)
        f.valuestack.push(w_2)

    def ROT_FOUR(f):
        w_1 = f.valuestack.pop()
        w_2 = f.valuestack.pop()
        w_3 = f.valuestack.pop()
        w_4 = f.valuestack.pop()
        f.valuestack.push(w_1)
        f.valuestack.push(w_4)
        f.valuestack.push(w_3)
        f.valuestack.push(w_2)

    def DUP_TOP(f):
        w_1 = f.valuestack.top()
        f.valuestack.push(w_1)

    def DUP_TOPX(f, itemcount):
        assert 1 <= itemcount <= 5, "limitation of the current interpreter"
        for i in range(itemcount):
            w_1 = f.valuestack.top(itemcount-1)
            f.valuestack.push(w_1)

    UNARY_POSITIVE = unaryoperation("pos")
    UNARY_NEGATIVE = unaryoperation("neg")
    UNARY_NOT      = unaryoperation("not_")
    UNARY_CONVERT  = unaryoperation("repr")
    UNARY_INVERT   = unaryoperation("invert")

    def BINARY_POWER(f):
        w_2 = f.valuestack.pop()
        w_1 = f.valuestack.pop()
        w_result = f.space.pow(w_1, w_2, f.space.w_None)
        f.valuestack.push(w_result)

    BINARY_MULTIPLY = binaryoperation("mul")
    BINARY_TRUE_DIVIDE  = binaryoperation("truediv")
    BINARY_FLOOR_DIVIDE = binaryoperation("floordiv")
    BINARY_DIVIDE       = binaryoperation("div")
    BINARY_MODULO       = binaryoperation("mod")
    BINARY_ADD      = binaryoperation("add")
    BINARY_SUBTRACT = binaryoperation("sub")
    BINARY_SUBSCR   = binaryoperation("getitem")
    BINARY_LSHIFT   = binaryoperation("lshift")
    BINARY_RSHIFT   = binaryoperation("rshift")
    BINARY_AND = binaryoperation("and_")
    BINARY_XOR = binaryoperation("xor")
    BINARY_OR  = binaryoperation("or_")

    def INPLACE_POWER(f):
        w_2 = f.valuestack.pop()
        w_1 = f.valuestack.pop()
        w_result = f.space.inplace_pow(w_1, w_2, f.space.w_None)
        f.valuestack.push(w_result)

    INPLACE_MULTIPLY = binaryoperation("inplace_mul")
    INPLACE_TRUE_DIVIDE  = binaryoperation("inplace_truediv")
    INPLACE_FLOOR_DIVIDE = binaryoperation("inplace_floordiv")
    INPLACE_DIVIDE       = binaryoperation("inplace_div")
    INPLACE_MODULO       = binaryoperation("inplace_mod")
    INPLACE_ADD      = binaryoperation("inplace_add")
    INPLACE_SUBTRACT = binaryoperation("inplace_sub")
    INPLACE_LSHIFT   = binaryoperation("inplace_lshift")
    INPLACE_RSHIFT   = binaryoperation("inplace_rshift")
    INPLACE_AND = binaryoperation("inplace_and")
    INPLACE_XOR = binaryoperation("inplace_xor")
    INPLACE_OR  = binaryoperation("inplace_or")

    def slice(f, w_start, w_end):
        w_slice = f.space.newslice(w_start, w_end, None)
        w_obj = f.valuestack.pop()
        w_result = f.space.getitem(w_obj, w_slice)
        f.valuestack.push(w_result)

    def SLICE_0(f):
        f.slice(None, None)

    def SLICE_1(f):
        w_start = f.valuestack.pop()
        f.slice(w_start, None)

    def SLICE_2(f):
        w_end = f.valuestack.pop()
        f.slice(None, w_end)

    def SLICE_3(f):
        w_end = f.valuestack.pop()
        w_start = f.valuestack.pop()
        f.slice(w_start, w_end)

    def storeslice(f, w_start, w_end):
        w_slice = f.space.newslice(w_start, w_end, None)
        w_obj = f.valuestack.pop()
        w_newvalue = f.valuestack.pop()
        f.space.setitem(w_obj, w_slice, w_newvalue)

    def STORE_SLICE_0(f):
        f.storeslice(None, None)

    def STORE_SLICE_1(f):
        w_start = f.valuestack.pop()
        f.storeslice(w_start, None)

    def STORE_SLICE_2(f):
        w_end = f.valuestack.pop()
        f.storeslice(None, w_end)

    def STORE_SLICE_3(f):
        w_end = f.valuestack.pop()
        w_start = f.valuestack.pop()
        f.storeslice(w_start, w_end)

    def deleteslice(f, w_start, w_end):
        w_slice = f.space.newslice(w_start, w_end, None)
        w_obj = f.valuestack.pop()
        f.space.delitem(w_obj, w_slice)

    def DELETE_SLICE_0(f):
        f.deleteslice(None, None)

    def DELETE_SLICE_1(f):
        w_start = f.valuestack.pop()
        f.deleteslice(w_start, None)

    def DELETE_SLICE_2(f):
        w_end = f.valuestack.pop()
        f.deleteslice(None, w_end)

    def DELETE_SLICE_3(f):
        w_end = f.valuestack.pop()
        w_start = f.valuestack.pop()
        f.deleteslice(w_start, w_end)

    def STORE_SUBSCR(f):
        "obj[subscr] = newvalue"
        w_subscr = f.valuestack.pop()
        w_obj = f.valuestack.pop()
        w_newvalue = f.valuestack.pop()
        f.space.setitem(w_obj, w_subscr, w_newvalue)

    def DELETE_SUBSCR(f):
        "del obj[subscr]"
        w_subscr = f.valuestack.pop()
        w_obj = f.valuestack.pop()
        f.space.delitem(w_obj, w_subscr)

    def PRINT_EXPR(f):
        w_expr = f.valuestack.pop()
        print_expr(f.space, w_expr)

    def PRINT_ITEM_TO(f):
        w_stream = f.valuestack.pop()
        w_item = f.valuestack.pop()
        print_item_to(f.space, w_item, w_stream)

    def PRINT_ITEM(f):
        w_item = f.valuestack.pop()
        print_item_to(f.space, w_item, sys_stdout(f.space))

    def PRINT_NEWLINE_TO(f):
        w_stream = f.valuestack.pop()
        print_newline_to(f.space, w_stream)

    def PRINT_NEWLINE(f):
        print_newline_to(f.space, sys_stdout(f.space))

    def BREAK_LOOP(f):
        raise pyframe.SBreakLoop

    def CONTINUE_LOOP(f, startofloop):
        raise pyframe.SContinueLoop(startofloop)

    def RAISE_VARARGS(f, nbargs):
        # we use the .app.py file to prepare the exception/value/traceback
        # but not to actually raise it, because we cannot use the 'raise'
        # statement to implement RAISE_VARARGS
        w_type = w_value = w_traceback = f.space.w_None
        if nbargs >= 3: w_traceback = f.valuestack.pop()
        if nbargs >= 2: w_value     = f.valuestack.pop()
        if nbargs >= 1: w_type      = f.valuestack.pop()
        w_resulttuple = prepare_raise(f.space, w_type, w_value, w_traceback)
        w_type, w_value, w_traceback = f.space.unpacktuple(w_resulttuple, 3)
        # XXX the three-arguments 'raise' is not supported yet
        raise OperationError(w_type, w_value)

    def LOAD_LOCALS(f):
        f.valuestack.push(f.w_locals)

    def RETURN_VALUE(f):
        w_returnvalue = f.valuestack.pop()
        raise pyframe.SReturnValue(w_returnvalue)

    def EXEC_STMT(f):
        w_locals  = f.valuestack.pop()
        w_globals = f.valuestack.pop()
        w_prog    = f.valuestack.pop()
        w_resulttuple = f.prepare_exec(w_prog, w_globals, w_locals)
        w_prog, w_globals, w_locals = f.space.unpacktuple(w_resulttuple)

        plain = f.space.is_true(f.space.is_(w_locals, f.w_locals))
        if plain:
            w_locals = f.getdictscope()
        pycode = f.space.unwrap(w_prog)
        pycode.exec_code(f.space, w_globals, w_locals)
        if plain:
            f.setdictscope(w_locals)

    def app_prepare_exec(f, prog, globals, locals):
        """Manipulate parameters to exec statement to (codeobject, dict, dict).
        """
        # XXX INCOMPLETE
        if (globals is None and locals is None and
            isinstance(prog, tuple) and
            (len(prog) == 2 or len(prog) == 3)):
            globals = prog[1]
            if len(prog) == 3:
                locals = prog[2]
            prog = prog[0]
        if globals is None:
            globals = f.f_globals
            if locals is None:
                locals = f.f_locals
        if locals is None:
            locals = globals
        if not isinstance(globals, dict):
            raise TypeError("exec: arg 2 must be a dictionary or None")
        elif not globals.has_key('__builtins__'):
            globals['__builtins__'] = f.f_builtins
        if not isinstance(locals, dict):
            raise TypeError("exec: arg 3 must be a dictionary or None")
        # XXX - HACK to check for code object
        co = compile('1','<string>','eval')
        if isinstance(prog, type(co)):
            return (prog, globals, locals)
        if not isinstance(prog, str):
    ##     if not (isinstance(prog, types.StringTypes) or
    ##             isinstance(prog, types.FileType)):
            raise TypeError("exec: arg 1 must be a string, file, or code object")
    ##     if isinstance(prog, types.FileType):
    ##         flags = 0
    ##         ## XXX add in parent flag merging
    ##         co = compile(prog.read(),prog.name,'exec',flags,1)
    ##         return (co,globals,locals)
        else: # prog is a string
            flags = 0
            ## XXX add in parent flag merging
            co = compile(prog,'<string>','exec',flags,1)
            return (co, globals, locals)

    def POP_BLOCK(f):
        block = f.blockstack.pop()
        block.cleanup(f)  # the block knows how to clean up the value stack

    def END_FINALLY(f):
        # unlike CPython, when we reach this opcode the value stack has
        # always been set up as follows (topmost first):
        #   [exception type  or None]
        #   [exception value or None]
        #   [wrapped stack unroller ]
        f.valuestack.pop()   # ignore the exception type
        f.valuestack.pop()   # ignore the exception value
        unroller = f.space.unwrap(f.valuestack.pop())
        if unroller is not None:
            raise unroller   # re-raise the unroller, if any

    def BUILD_CLASS(f):
        w_methodsdict = f.valuestack.pop()
        w_bases       = f.valuestack.pop()
        w_name        = f.valuestack.pop()
        w_metaclass = find_metaclass(f.space, w_bases,
                                     w_methodsdict, f.w_globals)
        w_newclass = f.space.call_function(w_metaclass, w_name,
                                           w_bases, w_methodsdict)
        f.valuestack.push(w_newclass)

    def STORE_NAME(f, varindex):
        varname = f.getname(varindex)
        w_varname = f.space.wrap(varname)
        w_newvalue = f.valuestack.pop()
        f.space.setitem(f.w_locals, w_varname, w_newvalue)

    def DELETE_NAME(f, varindex):
        varname = f.getname(varindex)
        w_varname = f.space.wrap(varname)
        try:
            f.space.delitem(f.w_locals, w_varname)
        except OperationError, e:
            # catch KeyErrors and turn them into NameErrors
            if not e.match(f.space, f.space.w_KeyError):
                raise
            message = "name '%s' is not defined" % varname
            raise OperationError(f.space.w_NameError, f.space.wrap(message))

    def UNPACK_SEQUENCE(f, itemcount):
        w_iterable = f.valuestack.pop()
        try:
            items = f.space.unpackiterable(w_iterable, itemcount)
        except ValueError, e:
            raise OperationError(f.space.w_ValueError, f.space.wrap(str(e)))
        items.reverse()
        for item in items:
            f.valuestack.push(item)

    def STORE_ATTR(f, nameindex):
        "obj.attributename = newvalue"
        attributename = f.getname(nameindex)
        w_attributename = f.space.wrap(attributename)
        w_obj = f.valuestack.pop()
        w_newvalue = f.valuestack.pop()
        f.space.setattr(w_obj, w_attributename, w_newvalue)

    def DELETE_ATTR(f, nameindex):
        "del obj.attributename"
        attributename = f.getname(nameindex)
        w_attributename = f.space.wrap(attributename)
        w_obj = f.valuestack.pop()
        f.space.delattr(w_obj, w_attributename)

    def STORE_GLOBAL(f, nameindex):
        varname = f.getname(nameindex)
        w_varname = f.space.wrap(varname)
        w_newvalue = f.valuestack.pop()
        f.space.setitem(f.w_globals, w_varname, w_newvalue)

    def DELETE_GLOBAL(f, nameindex):
        varname = f.getname(nameindex)
        w_varname = f.space.wrap(varname)
        f.space.delitem(f.w_globals, w_varname)

    def LOAD_NAME(f, nameindex):
        varname = f.getname(nameindex)
        w_varname = f.space.wrap(varname)

        if f.w_globals is f.w_locals:
            try_list_w = [f.w_globals, f.w_builtins]

        else:
            try_list_w = [f.w_locals, f.w_globals, f.w_builtins]

        w_value = None
        for wrapped in try_list_w:
            try:
                w_value = f.space.getitem(wrapped, w_varname)
                f.valuestack.push(w_value)
                return

            except OperationError, e:
                if not e.match(f.space, f.space.w_KeyError):
                    raise
        # rxe Why global???
        #message = "global name '%s' is not defined" % varname
        message = "name '%s' is not defined" % varname
        w_exc_type = f.space.w_NameError
        w_exc_value = f.space.wrap(message)
        raise OperationError(w_exc_type, w_exc_value)


        # XXX the implementation can be pushed back into app-space as an
        # when exception handling begins to behave itself.  For now, it
        # was getting on my nerves -- mwh
        #    w_value = f.load_name(w_varname)
        #    f.valuestack.push(w_value)

    def LOAD_GLOBAL(f, nameindex):
        assert f.w_globals is not None
        varname = f.getname(nameindex)
        w_varname = f.space.wrap(varname)
        try:
            w_value = f.space.getitem(f.w_globals, w_varname)
        except OperationError, e:
            # catch KeyErrors
            if not e.match(f.space, f.space.w_KeyError):
                raise
            # we got a KeyError, now look in the built-ins
            try:
                w_value = f.space.getitem(f.w_builtins, w_varname)
            except OperationError, e:
                # catch KeyErrors again
                if not e.match(f.space, f.space.w_KeyError):
                    raise
                message = "global name '%s' is not defined" % varname
                w_exc_type = f.space.w_NameError
                w_exc_value = f.space.wrap(message)
                raise OperationError(w_exc_type, w_exc_value)
        f.valuestack.push(w_value)

    def DELETE_FAST(f, varindex):
        if f.fastlocals_w[varindex] is UNDEFINED:
            varname = f.getlocalvarname(varindex)
            message = "local variable '%s' referenced before assignment" % varname
            raise OperationError(f.space.w_UnboundLocalError, f.space.wrap(message))
        f.fastlocals_w[varindex] = UNDEFINED

    def BUILD_TUPLE(f, itemcount):
        items = [f.valuestack.pop() for i in range(itemcount)]
        items.reverse()
        w_tuple = f.space.newtuple(items)
        f.valuestack.push(w_tuple)

    def BUILD_LIST(f, itemcount):
        items = [f.valuestack.pop() for i in range(itemcount)]
        items.reverse()
        w_list = f.space.newlist(items)
        f.valuestack.push(w_list)

    def BUILD_MAP(f, zero):
        if zero != 0:
            raise pyframe.BytecodeCorruption
        w_dict = f.space.newdict([])
        f.valuestack.push(w_dict)

    def LOAD_ATTR(f, nameindex):
        "obj.attributename"
        attributename = f.getname(nameindex)
        w_attributename = f.space.wrap(attributename)
        w_obj = f.valuestack.pop()
        w_value = f.space.getattr(w_obj, w_attributename)
        f.valuestack.push(w_value)

    def cmp_lt(f, w_1, w_2):  return f.space.lt(w_1, w_2)
    def cmp_le(f, w_1, w_2):  return f.space.le(w_1, w_2)
    def cmp_eq(f, w_1, w_2):  return f.space.eq(w_1, w_2)
    def cmp_ne(f, w_1, w_2):  return f.space.ne(w_1, w_2)
    def cmp_gt(f, w_1, w_2):  return f.space.gt(w_1, w_2)
    def cmp_ge(f, w_1, w_2):  return f.space.ge(w_1, w_2)

    def cmp_in(f, w_1, w_2):
        return f.space.contains(w_2, w_1)
    def cmp_not_in(f, w_1, w_2):
        return f.space.not_(f.space.contains(w_2, w_1))
    def cmp_is(f, w_1, w_2):
        return f.space.is_(w_1, w_2)
    def cmp_is_not(f, w_1, w_2):
        return f.space.not_(f.space.is_(w_1, w_2))
    def cmp_exc_match(f, w_1, w_2):
        return f.space.newbool(f.space.exception_match(w_1, w_2))

    compare_dispatch_table = {
        0: cmp_lt,   # "<"
        1: cmp_le,   # "<="
        2: cmp_eq,   # "=="
        3: cmp_ne,   # "!="
        4: cmp_gt,   # ">"
        5: cmp_ge,   # ">="
        6: cmp_in,
        7: cmp_not_in,
        8: cmp_is,
        9: cmp_is_not,
        10: cmp_exc_match,
        }
    def COMPARE_OP(f, testnum):
        w_2 = f.valuestack.pop()
        w_1 = f.valuestack.pop()
        try:
            testfn = f.compare_dispatch_table[testnum]
        except KeyError:
            raise pyframe.BytecodeCorruption, "bad COMPARE_OP oparg"
        w_result = testfn(f, w_1, w_2)
        f.valuestack.push(w_result)

    def IMPORT_NAME(f, nameindex):
        space = f.space
        modulename = f.getname(nameindex)
        w_fromlist = f.valuestack.pop()
        try:
            w_import = space.getitem(f.w_builtins, space.wrap("__import__"))
        except OperationError, e:
            if not e.match(space, space.w_KeyError):
                raise
            raise OperationError(space.w_ImportError,
                                 space.wrap("__import__ not found"))
        w_obj = space.call_function(w_import, space.wrap(modulename),
                                    f.w_globals, f.w_locals, w_fromlist)
        f.valuestack.push(w_obj)

    def IMPORT_STAR(f):
        w_module = f.valuestack.pop()
        w_locals = f.getdictscope()
        import_all_from(f.space, w_module, w_locals)
        f.setdictscope(w_locals)

    def IMPORT_FROM(f, nameindex):
        name = f.getname(nameindex)
        w_name = f.space.wrap(name)
        w_module = f.valuestack.top()
        w_obj = import_from(f.space, w_module, w_name)
        f.valuestack.push(w_obj)

    def JUMP_FORWARD(f, stepby):
        f.next_instr += stepby

    def JUMP_IF_FALSE(f, stepby):
        w_cond = f.valuestack.top()
        if not f.space.is_true(w_cond):
            f.next_instr += stepby

    def JUMP_IF_TRUE(f, stepby):
        w_cond = f.valuestack.top()
        if f.space.is_true(w_cond):
            f.next_instr += stepby

    def JUMP_ABSOLUTE(f, jumpto):
        f.next_instr = jumpto

    def GET_ITER(f):
        w_iterable = f.valuestack.pop()
        w_iterator = f.space.iter(w_iterable)
        f.valuestack.push(w_iterator)

    def FOR_ITER(f, jumpby):
        w_iterator = f.valuestack.top()
        try:
            w_nextitem = f.space.next(w_iterator)
        except NoValue:
            # iterator exhausted
            f.valuestack.pop()
            f.next_instr += jumpby
        else:
            f.valuestack.push(w_nextitem)

    def FOR_LOOP(f, oparg):
        raise pyframe.BytecodeCorruption, "old opcode, no longer in use"

    def SETUP_LOOP(f, offsettoend):
        block = pyframe.LoopBlock(f, f.next_instr + offsettoend)
        f.blockstack.push(block)

    def SETUP_EXCEPT(f, offsettoend):
        block = pyframe.ExceptBlock(f, f.next_instr + offsettoend)
        f.blockstack.push(block)

    def SETUP_FINALLY(f, offsettoend):
        block = pyframe.FinallyBlock(f, f.next_instr + offsettoend)
        f.blockstack.push(block)

    def call_function_extra(f, oparg, with_varargs, with_varkw):
        n_arguments = oparg & 0xff
        n_keywords = (oparg>>8) & 0xff
        if with_varkw:
            w_varkw = f.valuestack.pop()
        if with_varargs:
            w_varargs = f.valuestack.pop()
        keywords = []
        for i in range(n_keywords):
            w_value = f.valuestack.pop()
            w_key   = f.valuestack.pop()
            keywords.append((w_key, w_value))
        arguments = [f.valuestack.pop() for i in range(n_arguments)]
        arguments.reverse()
        w_function  = f.valuestack.pop()
        w_arguments = f.space.newtuple(arguments)
        w_keywords  = f.space.newdict(keywords)
        if with_varargs:
            w_arguments = f.update_star_args(w_arguments, w_varargs)
        if with_varkw:
            w_keywords  = f.update_keyword_args(w_keywords, w_varkw)
        w_result = f.space.call(w_function, w_arguments, w_keywords)
        f.valuestack.push(w_result)

    def app_update_star_args(f, args, extra_args):
        return args + tuple(extra_args)

    def app_update_keyword_args(f, kw, extra_kw):
        if not isinstance(extra_kw, dict):
            raise TypeError, "argument after ** must be a dictionary"
        result = kw.copy()
        for key, value in extra_kw.items():
            if key in result:
                # XXX should mention the function name in error message
                raise TypeError, ("got multiple values "
                                  "for keyword argument '%s'" % key)
            result[key] = value
        return result

    def CALL_FUNCTION(f, oparg):
        f.call_function_extra(oparg, False, False)

    def CALL_FUNCTION_VAR(f, oparg):
        f.call_function_extra(oparg, True,  False)

    def CALL_FUNCTION_KW(f, oparg):
        f.call_function_extra(oparg, False, True)

    def CALL_FUNCTION_VAR_KW(f, oparg):
        f.call_function_extra(oparg, True,  True)

    def MAKE_FUNCTION(f, numdefaults):
        w_codeobj = f.valuestack.pop()
        codeobj = f.space.unwrap(w_codeobj)   
        defaultarguments = [f.valuestack.pop() for i in range(numdefaults)]
        defaultarguments.reverse()
        fn = function.Function(f.space, codeobj, f.w_globals, defaultarguments)
        f.valuestack.push(f.space.wrap(fn))

    def BUILD_SLICE(f, numargs):
        if numargs == 3:
            w_step = f.valuestack.pop()
        elif numargs == 2:
            w_step = None
        else:
            raise pyframe.BytecodeCorruption
        w_end   = f.valuestack.pop()
        w_start = f.valuestack.pop()
        w_slice = f.space.newslice(w_start, w_end, w_step)
        f.valuestack.push(w_slice)

    def SET_LINENO(f, lineno):
        pass

    def EXTENDED_ARG(f, oparg):
        opcode = f.nextop()
        oparg = oparg<<16 | f.nextarg()
        fn = self.dispatch_table[opcode]
        if not fn.has_arg:
            raise pyframe.BytecodeCorruption
        fn(f, oparg)

    def MISSING_OPCODE(f, oparg=None):
        raise pyframe.BytecodeCorruption, "unknown opcode"

    ### dispatch_table ###

    # 'dispatch_table' is a class attribute: a list of functions
    # it is created by 'cls.setup_dispatch_table()'.

    __metaclass__ = InitializedClass
    def __initclass__(cls):
        # create the 'cls.dispatch_table' attribute
        import dis
        dispatch_table = []
        missing_opcode = cls.MISSING_OPCODE
        for i in range(256):
            opname = dis.opname[i].replace('+', '_')
            fn = getattr(cls, opname, missing_opcode)
            fn = getattr(fn, 'im_func',fn)
            fn.has_arg = i >= dis.HAVE_ARGUMENT
            #if fn is missing_opcode and not opname.startswith('<') and i>0:
            #    import warnings
            #    warnings.warn("* Warning, missing opcode %s" % opname)
            dispatch_table.append(fn)
        cls.dispatch_table = dispatch_table


    gateway.importall(locals())   # app_xxx() -> xxx()


### helpers written at the application-level ###
# Some of these functions are expected to be generally useful if other
# parts of the code needs to do the same thing as a non-trivial opcode,
# like finding out which metaclass a new class should have.
# This is why they are not methods of PyInterpFrame.
# There are also a couple of helpers that are methods, defined in the
# class above.

def app_print_expr(x):
    import sys
    try:
        displayhook = sys.displayhook
    except AttributeError:
        raise RuntimeError("lost sys.displayhook")
    displayhook(x)

def app_file_softspace(file, newflag):
    try:
        softspace = file.softspace
    except AttributeError:
        softspace = 0
    try:
        file.softspace = newflag
    except AttributeError:
        pass
    return softspace

def app_sys_stdout():
    import sys
    try:
        return sys.stdout
    except AttributeError:
        raise RuntimeError("lost sys.stdout")

def app_print_item_to(x, stream):
    if file_softspace(stream, False):
        stream.write(" ")
    stream.write(str(x))
    # add a softspace unless we just printed a string which ends in a '\t'
    # or '\n' -- or more generally any whitespace character but ' '
    #    if isinstance(x, str) and len(x) and x[-1].isspace() and x[-1]!=' ':
    #        return
    # XXX add unicode handling
    file_softspace(stream, True)

def app_print_newline_to(stream):
    stream.write("\n")
    file_softspace(stream, False)

def app_prepare_raise(etype, value, traceback):
    # careful if 'import types' is added here!
    # we get an infinite loop if this import fails:
    #    import types -> IMPORT_NAME -> import_name -> raise ImportError
    #    -> RAISE_VARARGS -> prepare_raise -> import types ...
    if etype is None:
        # reraise
        # XXX this means that "raise" is equivalent to "raise None"
        #     which is not the case in CPython, but well
        import sys
        etype, value, traceback = sys.exc_info()
    #if not isinstance(traceback, (types.NoneType, types.TracebackType)):
    #    raise TypeError, "raise: arg 3 must be traceback or None"
    while isinstance(etype, tuple):
        etype = etype[0]
    if type(etype) is str:
        # XXX warn
        pass
    elif isinstance(etype, Exception):
        if value is not None:
            raise TypeError("instance exception may not have a separate value")
        value = etype
        etype = value.__class__
    elif isinstance(etype, type) and issubclass(etype, Exception):
        if value is None:
            value = ()
        elif not isinstance(value, tuple):
            value = (value,)
        value = etype(*value)
    else:
        raise TypeError("exceptions must be instances or subclasses of "
                        "Exception or strings (deprecated), not %s" %
                        (type(etype).__name__,))
    return etype, value, traceback

def app_find_metaclass(bases, namespace, globals):
    if '__metaclass__' in namespace:
        return namespace['__metaclass__']
    elif len(bases) > 0:
        base = bases[0]
        if hasattr(base, '__class__'):
            return base.__class__
        else:
            return type(base)
    elif '__metaclass__' in globals:
        return globals['__metaclass__']
    else:
        return type

def app_import_all_from(module, into_locals):
    try:
        all = module.__all__
    except AttributeError:
        try:
            dict = module.__dict__
        except AttributeError:
            raise ImportError("from-import-* object has no __dict__ "
                              "and no __all__")
        all = dict.keys()
        skip_leading_underscores = True
    else:
        skip_leading_underscores = False
    for name in all:
        if skip_leading_underscores and name[0]=='_':
            continue
        into_locals[name] = getattr(module, name)

def app_import_from(module, name):
    try:
        return getattr(module, name)
    except AttributeError:
        raise ImportError("cannot import name '%s'" % name)


gateway.importall(globals())   # app_xxx() -> xxx()
