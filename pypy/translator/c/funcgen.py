from __future__ import generators
from pypy.translator.c.support import USESLOTS # set to False if necessary while refactoring
from pypy.translator.c.support import cdecl, ErrorValue
from pypy.translator.c.support import llvalue_from_constant, gen_assignments
from pypy.objspace.flow.model import Variable, Constant, Block
from pypy.objspace.flow.model import c_last_exception
from pypy.rpython.lltypesystem.lltype import Ptr, PyObject, Void, Bool, Signed
from pypy.rpython.lltypesystem.lltype import Unsigned, SignedLongLong
from pypy.rpython.lltypesystem.lltype import UnsignedLongLong, Char, UniChar
from pypy.rpython.lltypesystem.lltype import pyobjectptr
from pypy.rpython.lltypesystem.lltype import Struct, Array, FixedSizeArray

PyObjPtr = Ptr(PyObject)
LOCALVAR = 'l_%s'

class FunctionCodeGenerator(object):
    """
    Collects information about a function which we have to generate
    from a flow graph.
    """

    if USESLOTS:
        __slots__ = """graph db gcpolicy
                       cpython_exc
                       more_ll_values
                       vars
                       lltypes
                       functionname
                       currentblock
                       blocknum""".split()

    def __init__(self, graph, db, cpython_exc=False, functionname=None):
        self.graph = graph
        self.db = db
        self.gcpolicy = db.gcpolicy
        self.cpython_exc = cpython_exc
        self.functionname = functionname
        # apply the exception transformation
        if self.db.exctransformer:
            self.db.exctransformer.create_exception_handling(self.graph)
        # apply the gc transformation
        self.db.gctransformer.transform_graph(self.graph)
        #self.graph.show()
        
        self.blocknum = {}
        #
        # collect all variables and constants used in the body,
        # and get their types now
        #
        # NOTE: cannot use dictionaries with Constants as keys, because
        #       Constants may hash and compare equal but have different lltypes
        mix = [self.graph.getreturnvar()]
        self.more_ll_values = []
        for block in graph.iterblocks():
            self.blocknum[block] = len(self.blocknum)
            mix.extend(block.inputargs)
            for op in block.operations:
                mix.extend(op.args)
                mix.append(op.result)
            for link in block.exits:
                mix.extend(link.getextravars())
                mix.extend(link.args)
                if hasattr(link, 'llexitcase'):
                    self.more_ll_values.append(link.llexitcase)
                elif link.exitcase is not None:
                    mix.append(Constant(link.exitcase))
        if cpython_exc:
            v, exc_cleanup_ops = graph.exc_cleanup
            mix.append(v)
            for cleanupop in exc_cleanup_ops:
                mix.extend(cleanupop.args)
                mix.append(cleanupop.result)
             
        uniquemix = []
        seen = {}
        for v in mix:
            if id(v) not in seen:
                uniquemix.append(v)
                seen[id(v)] = True
            T = getattr(v, 'concretetype', PyObjPtr)
            db.gettype(T)  # force the type to be considered by the database
        self.vars = uniquemix
        self.lltypes = None

    def name(self, cname):  #virtual
        return cname

    def implementation_begin(self):
        db = self.db
        lltypes = {}
        for v in self.vars:
            T = getattr(v, 'concretetype', PyObjPtr)
            typename = db.gettype(T)
            lltypes[id(v)] = T, typename
        self.lltypes = lltypes

    def implementation_end(self):
        self.lltypes = None

    def argnames(self):
        return [LOCALVAR % v.name for v in self.graph.getargs()]

    def allvariables(self):
        return [v for v in self.vars if isinstance(v, Variable)]

    def allconstants(self):
        return [c for c in self.vars if isinstance(c, Constant)]

    def allconstantvalues(self):
        for c in self.vars:
            if isinstance(c, Constant):
                yield llvalue_from_constant(c)
        for llvalue in self.more_ll_values:
            yield llvalue

    def lltypemap(self, v):
        T, typename = self.lltypes[id(v)]
        return T

    def lltypename(self, v):
        T, typename = self.lltypes[id(v)]
        return typename

    def expr(self, v, special_case_void=True):
        if isinstance(v, Variable):
            if self.lltypemap(v) is Void and special_case_void:
                return '/* nothing */'
            else:
                return LOCALVAR % v.name
        elif isinstance(v, Constant):
            value = llvalue_from_constant(v)
            if value is None and not special_case_void:
                return 'nothing'
            else:
                return self.db.get(value)
        else:
            raise TypeError, "expr(%r)" % (v,)

    def error_return_value(self):
        returnlltype = self.lltypemap(self.graph.getreturnvar())
        return self.db.get(ErrorValue(returnlltype))

    def return_with_error(self):
        if self.cpython_exc:
            assert self.lltypemap(self.graph.getreturnvar()) == PyObjPtr
            v, exc_cleanup_ops = self.graph.exc_cleanup
            vanishing_exc_value = self.expr(v)
            yield 'RPyConvertExceptionToCPython(%s);' % vanishing_exc_value
            for cleanupop in exc_cleanup_ops:
                for line in self.gen_op(cleanupop):
                    yield line
        yield 'return %s; ' % self.error_return_value()

    # ____________________________________________________________

    def cfunction_declarations(self):
        # declare the local variables, excluding the function arguments
        seen = {}
        for a in self.graph.getargs():
            seen[a.name] = True

        result_by_name = []
        for v in self.allvariables():
            name = v.name
            if name not in seen:
                seen[name] = True
                result = cdecl(self.lltypename(v), LOCALVAR % name) + ';'
                if self.lltypemap(v) is Void:
                    continue  #result = '/*%s*/' % result
                result_by_name.append((v._name, result))
        result_by_name.sort()
        return [result for name, result in result_by_name]

    # ____________________________________________________________

    def cfunction_body(self):
        graph = self.graph

        # generate the body of each block
        for block in graph.iterblocks():
            self.currentblock = block
            myblocknum = self.blocknum[block]
            yield ''
            yield 'block%d:' % myblocknum
            for i, op in enumerate(block.operations):
                for line in self.gen_op(op):
                    yield line
            if len(block.exits) == 0:
                assert len(block.inputargs) == 1
                # regular return block
                if self.cpython_exc:
                    assert self.lltypemap(self.graph.getreturnvar()) == PyObjPtr
                    yield 'if (RPyExceptionOccurred()) {'
                    yield '\tRPyConvertExceptionToCPython();'
                    yield '\treturn NULL;'
                    yield '}'
                retval = self.expr(block.inputargs[0])
                yield 'return %s;' % retval
                continue
            elif block.exitswitch is None:
                # single-exit block
                assert len(block.exits) == 1
                for op in self.gen_link(block.exits[0]):
                    yield op
                yield ''
            else:
                assert block.exitswitch != c_last_exception
                # block ending in a switch on a value
                TYPE = self.lltypemap(block.exitswitch)
                if TYPE in (Bool, PyObjPtr):
                    expr = self.expr(block.exitswitch)
                    for link in block.exits[:-1]:
                        assert link.exitcase in (False, True)
                        if TYPE == Bool:
                            if not link.exitcase:
                                expr = '!' + expr
                        elif TYPE == PyObjPtr:
                            yield 'assert(%s == Py_True || %s == Py_False);' % (
                                expr, expr)
                            if link.exitcase:
                                expr = '%s == Py_True' % expr
                            else:
                                expr = '%s == Py_False' % expr
                        yield 'if (%s) {' % expr
                        for op in self.gen_link(link):
                            yield '\t' + op
                        yield '}'
                    link = block.exits[-1]
                    assert link.exitcase in (False, True)
                    #yield 'assert(%s == %s);' % (self.expr(block.exitswitch),
                    #                       self.genc.nameofvalue(link.exitcase, ct))
                    for op in self.gen_link(block.exits[-1]):
                        yield op
                    yield ''
                elif TYPE in (Signed, Unsigned, SignedLongLong,
                              UnsignedLongLong, Char, UniChar):
                    defaultlink = None
                    expr = self.expr(block.exitswitch)
                    yield 'switch (%s) {' % self.expr(block.exitswitch)
                    for link in block.exits:
                        if link.exitcase is 'default':
                            defaultlink = link
                            continue
                        yield 'case %s:' % self.db.get(link.llexitcase)
                        for op in self.gen_link(link):
                            yield '\t' + op
                        yield 'break;'
                        
                    # ? Emit default case
                    if defaultlink is None:
                        raise TypeError('switches must have a default case.')
                    yield 'default:'
                    for op in self.gen_link(defaultlink):
                        yield '\t' + op

                    yield '}'
                else:
                    raise TypeError("exitswitch type not supported"
                                    "  Got %r" % (TYPE,))

    def gen_link(self, link, linklocalvars=None):
        "Generate the code to jump across the given Link."
        is_alive = {}
        linklocalvars = linklocalvars or {}
        assignments = []
        for a1, a2 in zip(link.args, link.target.inputargs):
            a2type, a2typename = self.lltypes[id(a2)]
            if a2type is Void:
                continue
            if a1 in linklocalvars:
                src = linklocalvars[a1]
            else:
                src = self.expr(a1)
            dest = LOCALVAR % a2.name
            assignments.append((a2typename, dest, src))
        for line in gen_assignments(assignments):
            yield line
        yield 'goto block%d;' % self.blocknum[link.target]

    def gen_op(self, op):
        macro = 'OP_%s' % op.opname.upper()
        if op.opname.startswith('gc_'):
            meth = getattr(self.gcpolicy, macro, None)
            if meth:
                line = meth(self, op)
        else:
            meth = getattr(self, macro, None)
            if meth:
                line = meth(op)
        if meth is None:
            lst = [self.expr(v) for v in op.args]
            lst.append(self.expr(op.result))
            line = '%s(%s);' % (macro, ', '.join(lst))
        if "\n" not in line:
            yield line
        else:
            for line in line.splitlines():
                yield line

    # ____________________________________________________________

    # the C preprocessor cannot handle operations taking a variable number
    # of arguments, so here are Python methods that do it
    
    def OP_NEWLIST(self, op):
        args = [self.expr(v) for v in op.args]
        r = self.expr(op.result)
        if len(args) == 0:
            return 'OP_NEWLIST0(%s);' % (r, )
        else:
            args.insert(0, '%d' % len(args))
            return 'OP_NEWLIST((%s), %s);' % (', '.join(args), r)

    def OP_NEWDICT(self, op):
        args = [self.expr(v) for v in op.args]
        r = self.expr(op.result)
        if len(args) == 0:
            return 'OP_NEWDICT0(%s);' % (r, )
        else:
            assert len(args) % 2 == 0
            args.insert(0, '%d' % (len(args)//2))
            return 'OP_NEWDICT((%s), %s);' % (', '.join(args), r)

    def OP_NEWTUPLE(self, op):
        args = [self.expr(v) for v in op.args]
        r = self.expr(op.result)
        args.insert(0, '%d' % len(args))
        return 'OP_NEWTUPLE((%s), %s);' % (', '.join(args), r)

    def OP_SIMPLE_CALL(self, op):
        args = [self.expr(v) for v in op.args]
        r = self.expr(op.result)
        args.append('NULL')
        return 'OP_SIMPLE_CALL((%s), %s);' % (', '.join(args), r)

    def OP_CALL_ARGS(self, op):
        args = [self.expr(v) for v in op.args]
        r = self.expr(op.result)
        return 'OP_CALL_ARGS((%s), %s);' % (', '.join(args), r)

    def OP_DIRECT_CALL(self, op):
        # skip 'void' arguments
        args = [self.expr(v) for v in op.args if self.lltypemap(v) is not Void]
        line = '%s(%s);' % (args[0], ', '.join(args[1:]))
        if self.lltypemap(op.result) is not Void:
            # skip assignment of 'void' return value
            r = self.expr(op.result)
            line = '%s = %s' % (r, line)
        check = self.check_directcall_result(op)
        if check:
            return line + '\n' + check
        return line

    # the following works since the extra arguments that indirect_call has
    # is of type Void, which is removed by OP_DIRECT_CALL
    OP_INDIRECT_CALL = OP_DIRECT_CALL

    def check_directcall_result(self, op):
        return None

    # low-level operations
    def generic_get(self, op, sourceexpr):
        T = self.lltypemap(op.result)
        newvalue = self.expr(op.result, special_case_void=False)
        result = ['%s = %s;' % (newvalue, sourceexpr)]
        result = '\n'.join(result)
        if T is Void:
            result = '/* %s */' % result
        return result

    def generic_set(self, op, targetexpr):
        newvalue = self.expr(op.args[2], special_case_void=False)
        result = ['%s = %s;' % (targetexpr, newvalue)]
        T = self.lltypemap(op.args[2])
        result = '\n'.join(result)
        if T is Void:
            result = '/* %s */' % result
        return result

    def OP_GETFIELD(self, op, ampersand=''):
        assert isinstance(op.args[1], Constant)
        STRUCT = self.lltypemap(op.args[0]).TO
        structdef = self.db.gettypedefnode(STRUCT)
        fieldname = structdef.c_struct_field_name(op.args[1].value)
        return self.generic_get(op, '%s%s->%s' % (ampersand,
                                                  self.expr(op.args[0]),
                                                  fieldname))

    def OP_SETFIELD(self, op):
        assert isinstance(op.args[1], Constant)
        STRUCT = self.lltypemap(op.args[0]).TO
        structdef = self.db.gettypedefnode(STRUCT)
        fieldname = structdef.c_struct_field_name(op.args[1].value)
        return self.generic_set(op, '%s->%s' % (self.expr(op.args[0]),
                                                fieldname))

    def OP_GETSUBSTRUCT(self, op):
        return self.OP_GETFIELD(op, ampersand='&')

    def OP_GETARRAYSIZE(self, op):
        ARRAY = self.lltypemap(op.args[0]).TO
        if isinstance(ARRAY, FixedSizeArray):
            return '%s = %d;' % (self.expr(op.result),
                                 ARRAY.length)
        else:
            return '%s = %s->length;' % (self.expr(op.result),
                                         self.expr(op.args[0]))

    def OP_GETARRAYITEM(self, op):
        ARRAY = self.lltypemap(op.args[0]).TO
        items = self.expr(op.args[0])
        if isinstance(ARRAY, FixedSizeArray):
            items = '(*%s)' % (items,)
        else:
            items += '->items'
        return self.generic_get(op, '%s[%s]' % (items,
                                                self.expr(op.args[1])))

    def OP_SETARRAYITEM(self, op):
        ARRAY = self.lltypemap(op.args[0]).TO
        items = self.expr(op.args[0])
        if isinstance(ARRAY, FixedSizeArray):
            items = '(*%s)' % (items,)
        else:
            items += '->items'
        return self.generic_set(op, '%s[%s]' % (items,
                                                self.expr(op.args[1])))

    def OP_GETARRAYSUBSTRUCT(self, op):
        ARRAY = self.lltypemap(op.args[0]).TO
        items = self.expr(op.args[0])
        if isinstance(ARRAY, FixedSizeArray):
            items = '*%s' % (items,)
        else:
            items += '->items'
        return '%s = %s + %s;' % (self.expr(op.result),
                                  items,
                                  self.expr(op.args[1]))

    def OP_PTR_NONZERO(self, op):
        return '%s = (%s != NULL);' % (self.expr(op.result),
                                       self.expr(op.args[0]))
    def OP_PTR_ISZERO(self, op):
        return '%s = (%s == NULL);' % (self.expr(op.result),
                                       self.expr(op.args[0]))
    
    def OP_PTR_EQ(self, op):
        return '%s = (%s == %s);' % (self.expr(op.result),
                                     self.expr(op.args[0]),
                                     self.expr(op.args[1]))

    def OP_PTR_NE(self, op):
        return '%s = (%s != %s);' % (self.expr(op.result),
                                     self.expr(op.args[0]),
                                     self.expr(op.args[1]))

    def OP_MALLOC(self, op):
        TYPE = self.lltypemap(op.result).TO
        typename = self.db.gettype(TYPE)
        eresult = self.expr(op.result)
        esize = 'sizeof(%s)' % cdecl(typename, '')

        return self.gcpolicy.zero_malloc(TYPE, esize, eresult)

    def OP_MALLOC_VARSIZE(self, op):
        TYPE = self.lltypemap(op.result).TO
        typename = self.db.gettype(TYPE)
        lenfld = 'length'
        nodedef = self.db.gettypedefnode(TYPE)
        if isinstance(TYPE, Struct):
            arfld = TYPE._arrayfld
            lenfld = "%s.length" % nodedef.c_struct_field_name(arfld)
            VARPART = TYPE._flds[TYPE._arrayfld]
        else:
            VARPART = TYPE
        assert isinstance(VARPART, Array)
        itemtypename = self.db.gettype(VARPART.OF)
        elength = self.expr(op.args[1])
        eresult = self.expr(op.result)
        if VARPART.OF is Void:    # strange
            esize = 'sizeof(%s)' % (cdecl(typename, ''),)
            result = ''
        else:
            itemtype = cdecl(itemtypename, '')
            result = 'OP_MAX_VARSIZE(%s, %s);\n' % (
                elength,
                itemtype)
            esize = 'sizeof(%s)-sizeof(%s)+%s*sizeof(%s)' % (
                cdecl(typename, ''),
                itemtype,
                elength,
                itemtype)
        result += self.gcpolicy.zero_malloc(TYPE, esize, eresult)

        # ctypes Arrays have no length field
        if not VARPART._hints.get('nolength', False):
            result += '\n%s->%s = %s;' % (eresult, lenfld, elength)
        return result

    def OP_FLAVORED_MALLOC(self, op):
        TYPE = self.lltypemap(op.result).TO
        typename = self.db.gettype(TYPE)
        eresult = self.expr(op.result)
        esize = 'sizeof(%s)' % cdecl(typename, '')
        flavor = op.args[0].value
        if flavor == "raw": 
            return "OP_RAW_MALLOC(%s, %s);" % (esize, eresult) 
        elif flavor == "stack": 
            return "OP_STACK_MALLOC(%s, %s);" % (esize, eresult) 
        else:
            raise NotImplementedError

    def OP_FLAVORED_FREE(self, op):
        flavor = op.args[0].value
        if flavor == "raw":
            return "OP_RAW_FREE(%s, %s)" % (self.expr(op.args[1]),
                                            self.expr(op.result))
        else:
            raise NotImplementedError

    def OP_CAST_POINTER(self, op):
        TYPE = self.lltypemap(op.result)
        typename = self.db.gettype(TYPE)
        result = []
        result.append('%s = (%s)%s;' % (self.expr(op.result),
                                        cdecl(typename, ''),
                                        self.expr(op.args[0])))
        assert TYPE != PyObjPtr
        return '\t'.join(result)

    OP_CAST_PTR_TO_ADR = OP_CAST_POINTER
    OP_CAST_ADR_TO_PTR = OP_CAST_POINTER

    def OP_CAST_INT_TO_PTR(self, op):
        TYPE = self.lltypemap(op.result)
        typename = self.db.gettype(TYPE)
        return "%s = (%s)%s;" % (self.expr(op.result), cdecl(typename, ""), 
                                 self.expr(op.args[0]))

    def OP_SAME_AS(self, op):
        result = []
        TYPE = self.lltypemap(op.result)
        assert self.lltypemap(op.args[0]) == TYPE
        if TYPE is not Void:
            result.append('%s = %s;' % (self.expr(op.result),
                                        self.expr(op.args[0])))
        return '\t'.join(result)

    def OP_HINT(self, op):
        hints = op.args[1].value
        return '%s\t/* hint: %r */' % (self.OP_SAME_AS(op), hints)

    def OP_KEEPALIVE(self, op): # xxx what should be the sematics consequences of this
        return "/* kept alive: %s */ ;" % self.expr(op.args[0], special_case_void=False)

    #address operations
    def OP_RAW_STORE(self, op):
       addr = self.expr(op.args[0])
       TYPE = op.args[1].value
       offset = self.expr(op.args[2])
       value = self.expr(op.args[3])
       typename = self.db.gettype(TYPE).replace("@", "*") #XXX help! is this the way to do it?
       return "*(((%(typename)s) %(addr)s ) + %(offset)s) = %(value)s;" % locals()

    def OP_RAW_LOAD(self, op):
        addr = self.expr(op.args[0])
        TYPE = op.args[1].value
        offset = self.expr(op.args[2])
        result = self.expr(op.result)
        typename = self.db.gettype(TYPE).replace("@", "*") #XXX see above
        return "%(result)s = *(((%(typename)s) %(addr)s ) + %(offset)s);" % locals()



assert not USESLOTS or '__dict__' not in dir(FunctionCodeGenerator)
