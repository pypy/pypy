import sys
from pypy.translator.c.support import USESLOTS # set to False if necessary while refactoring
from pypy.translator.c.support import cdecl
from pypy.translator.c.support import llvalue_from_constant, gen_assignments
from pypy.translator.c.support import c_string_constant, barebonearray
from pypy.objspace.flow.model import Variable, Constant, Block
from pypy.objspace.flow.model import c_last_exception, copygraph
from pypy.rpython.lltypesystem.lltype import Ptr, PyObject, Void, Bool, Signed
from pypy.rpython.lltypesystem.lltype import Unsigned, SignedLongLong, Float
from pypy.rpython.lltypesystem.lltype import UnsignedLongLong, Char, UniChar
from pypy.rpython.lltypesystem.lltype import pyobjectptr, ContainerType
from pypy.rpython.lltypesystem.lltype import Struct, Array, FixedSizeArray
from pypy.rpython.lltypesystem.lltype import ForwardReference, FuncType
from pypy.rpython.lltypesystem.llmemory import Address
from pypy.translator.backendopt.ssa import SSI_to_SSA
from pypy.translator.backendopt.innerloop import find_inner_loops
from pypy.tool.identity_dict import identity_dict


PyObjPtr = Ptr(PyObject)
LOCALVAR = 'l_%s'

KEEP_INLINED_GRAPHS = False

class FunctionCodeGenerator(object):
    """
    Collects information about a function which we have to generate
    from a flow graph.
    """

    if USESLOTS:
        __slots__ = """graph db gcpolicy
                       exception_policy
                       more_ll_values
                       vars all_cached_consts 
                       illtypes
                       functionname
                       blocknum
                       innerloops
                       oldgraph""".split()

    def __init__(self, graph, db, exception_policy=None, functionname=None):
        graph._seen_by_the_backend = True
        self.graph = graph
        self.db = db
        self.gcpolicy = db.gcpolicy
        self.exception_policy = exception_policy
        self.functionname = functionname
        # apply the stackless transformation
        if db.stacklesstransformer:
            db.stacklesstransformer.transform_graph(graph)
        # apply the exception transformation
        if self.db.exctransformer:
            self.db.exctransformer.create_exception_handling(self.graph)
        # apply the gc transformation
        if self.db.gctransformer:
            self.db.gctransformer.transform_graph(self.graph)
        #self.graph.show()
        self.collect_var_and_types()

        for v in self.vars:
            T = getattr(v, 'concretetype', PyObjPtr)
            # obscure: skip forward references and hope for the best
            # (needed for delayed function pointers)
            if isinstance(T, Ptr) and T.TO.__class__ == ForwardReference:
                continue
            db.gettype(T)  # force the type to be considered by the database
       
        self.illtypes = None

    def collect_var_and_types(self):
        #
        # collect all variables and constants used in the body,
        # and get their types now
        #
        # NOTE: cannot use dictionaries with Constants as keys, because
        #       Constants may hash and compare equal but have different lltypes
        self.all_cached_consts = None # will be filled after implementation_end
        mix = [self.graph.getreturnvar()]
        self.more_ll_values = []
        for block in self.graph.iterblocks():
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
        if self.exception_policy == "CPython":
            v, exc_cleanup_ops = self.graph.exc_cleanup
            mix.append(v)
            for cleanupop in exc_cleanup_ops:
                mix.extend(cleanupop.args)
                mix.append(cleanupop.result)
             
        uniquemix = []
        seen = identity_dict()
        for v in mix:
            if v not in seen:
                uniquemix.append(v)
                seen[v] = True
        self.vars = uniquemix

    def name(self, cname):  #virtual
        return cname

    def patch_graph(self, copy_graph):
        graph = self.graph
        if self.db.gctransformer and self.db.gctransformer.inline:
            if copy_graph:
                graph = copygraph(graph, shallow=True)
            self.db.gctransformer.inline_helpers(graph)
        return graph

    def implementation_begin(self):
        self.oldgraph = self.graph
        self.graph = self.patch_graph(copy_graph=True)
        SSI_to_SSA(self.graph)
        self.collect_var_and_types()
        self.blocknum = {}
        for block in self.graph.iterblocks():
            self.blocknum[block] = len(self.blocknum)
        db = self.db
        lltypes = identity_dict()
        for v in self.vars:
            T = getattr(v, 'concretetype', PyObjPtr)
            typename = db.gettype(T)
            lltypes[v] = T, typename
        self.illtypes = lltypes
        self.innerloops = {}    # maps the loop's header block to a Loop()
        for loop in find_inner_loops(self.graph, Bool):
            self.innerloops[loop.headblock] = loop

    def graphs_to_patch(self):
        yield self.graph

    def implementation_end(self):
        self.all_cached_consts = list(self.allconstantvalues())
        self.illtypes = None
        self.vars = None
        self.blocknum = None
        self.innerloops = None
        self.graph = self.oldgraph
        del self.oldgraph

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
        T, typename = self.illtypes[v]
        return T

    def lltypename(self, v):
        T, typename = self.illtypes[v]
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
        yield 'goto block0;'    # to avoid a warning "this label is not used"

        # generate the body of each block
        for block in graph.iterblocks():
            myblocknum = self.blocknum[block]
            yield ''
            yield 'block%d:' % myblocknum
            for i, op in enumerate(block.operations):
                for line in self.gen_op(op):
                    yield line
            if len(block.exits) == 0:
                assert len(block.inputargs) == 1
                # regular return block
                if self.exception_policy == "CPython":
                    assert self.lltypemap(self.graph.getreturnvar()) == PyObjPtr
                    yield 'if (RPyExceptionOccurred()) {'
                    yield '\tRPyConvertExceptionToCPython();'
                    yield '\treturn NULL;'
                    yield '}'
                retval = self.expr(block.inputargs[0])
                if self.exception_policy != "exc_helper":
                    yield 'RPY_DEBUG_RETURN();'
                yield 'return %s;' % retval
                continue
            elif block.exitswitch is None:
                # single-exit block
                assert len(block.exits) == 1
                for op in self.gen_link(block.exits[0]):
                    yield op
            elif block in self.innerloops:
                for line in self.gen_while_loop_hack(block):
                    yield line
            else:
                assert block.exitswitch != c_last_exception
                # block ending in a switch on a value
                TYPE = self.lltypemap(block.exitswitch)
                if TYPE in (Bool, PyObjPtr):
                    expr = self.expr(block.exitswitch)
                    for link in block.exits[:0:-1]:
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
                    link = block.exits[0]
                    assert link.exitcase in (False, True)
                    #yield 'assert(%s == %s);' % (self.expr(block.exitswitch),
                    #                       self.genc.nameofvalue(link.exitcase, ct))
                    for op in self.gen_link(link):
                        yield op
                elif TYPE in (Signed, Unsigned, SignedLongLong,
                              UnsignedLongLong, Char, UniChar):
                    defaultlink = None
                    expr = self.expr(block.exitswitch)
                    yield 'switch (%s) {' % self.expr(block.exitswitch)
                    for link in block.exits:
                        if link.exitcase == 'default':
                            defaultlink = link
                            continue
                        yield 'case %s:' % self.db.get(link.llexitcase)
                        for op in self.gen_link(link):
                            yield '\t' + op
                        # 'break;' not needed, as gen_link ends in a 'goto'
                        
                    # Emit default case
                    yield 'default:'
                    if defaultlink is None:
                        yield '\tassert(!"bad switch!!");'
                    else:
                        for op in self.gen_link(defaultlink):
                            yield '\t' + op

                    yield '}'
                else:
                    raise TypeError("exitswitch type not supported"
                                    "  Got %r" % (TYPE,))

    def gen_link(self, link):
        "Generate the code to jump across the given Link."
        assignments = []
        for a1, a2 in zip(link.args, link.target.inputargs):
            a2type, a2typename = self.illtypes[a2]
            if a2type is Void:
                continue
            src = self.expr(a1)
            dest = LOCALVAR % a2.name
            assignments.append((a2typename, dest, src))
        for line in gen_assignments(assignments):
            yield line
        label = 'block%d' % self.blocknum[link.target]
        if link.target in self.innerloops:
            loop = self.innerloops[link.target]
            if link is loop.links[-1]:   # link that ends a loop
                label += '_back'
        yield 'goto %s;' % label

    def gen_op(self, op):
        macro = 'OP_%s' % op.opname.upper()
        line = None
        if op.opname.startswith('gc_'):
            meth = getattr(self.gcpolicy, macro, None)
            if meth:
                line = meth(self, op)
        else:
            meth = getattr(self, macro, None)
            if meth:
                line = meth(op)
        if line is None:
            lst = [self.expr(v) for v in op.args]
            lst.append(self.expr(op.result))
            line = '%s(%s);' % (macro, ', '.join(lst))
        if "\n" not in line:
            yield line
        else:
            for line in line.splitlines():
                yield line

    def gen_while_loop_hack(self, headblock):
        # a GCC optimization hack: generate 'while' statement in the
        # source to convince the C compiler that it is really dealing
        # with loops.  For the head of a loop (i.e. the block where the
        # decision is) we produce code like this:
        #
        #             headblock:
        #               ...headblock operations...
        #               while (cond) {
        #                   goto firstbodyblock;
        #                 headblock_back:
        #                   ...headblock operations...
        #               }
        #
        # The real body of the loop is not syntactically within the
        # scope of { }, but apparently this doesn't matter to GCC as
        # long as it is within the { } via the chain of goto's starting
        # at firstbodyblock: and ending at headblock_back:.  We need to
        # duplicate the operations of headblock, though, because the
        # chain of gotos entering the loop must arrive outside the
        # while() at the headblock: label and the chain of goto's that
        # close the loop must arrive inside the while() at the
        # headblock_back: label.

        looplinks = self.innerloops[headblock].links
        enterlink = looplinks[0]
        assert len(headblock.exits) == 2
        assert isinstance(headblock.exits[0].exitcase, bool)
        assert isinstance(headblock.exits[1].exitcase, bool)
        i = list(headblock.exits).index(enterlink)
        exitlink = headblock.exits[1 - i]

        expr = self.expr(headblock.exitswitch)
        if enterlink.exitcase == False:
            expr = '!' + expr
        yield 'while (%s) {' % expr
        for op in self.gen_link(enterlink):
            yield '\t' + op
        # the semicolon after the colon is needed in case no operation
        # produces any code after the label
        yield '\t  block%d_back: ;' % self.blocknum[headblock]
        if headblock.operations:
            for i, op in enumerate(headblock.operations):
                for line in self.gen_op(op):
                    yield '\t' + line
        yield '}'
        for op in self.gen_link(exitlink):
            yield op

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

    def generic_call(self, FUNC, fnexpr, args_v, v_result, targets=None):
        args = []
        assert len(args_v) == len(FUNC.TO.ARGS)
        for v, ARGTYPE in zip(args_v, FUNC.TO.ARGS):
            if ARGTYPE is Void:
                continue    # skip 'void' argument
            args.append(self.expr(v))
            # special case for rctypes: by-value container args:
            # XXX is this still needed now that rctypes is gone
            if isinstance(ARGTYPE, ContainerType):
                args[-1] = '*%s' % (args[-1],)

        line = '%s(%s);' % (fnexpr, ', '.join(args))
        if self.lltypemap(v_result) is not Void:
            # skip assignment of 'void' return value
            r = self.expr(v_result)
            line = '%s = %s' % (r, line)
        if targets:
            for graph in targets:
                if getattr(graph, 'inhibit_tail_call', False):
                    line += '\nPYPY_INHIBIT_TAIL_CALL();'
                    break
        return line

    def OP_DIRECT_CALL(self, op):
        fn = op.args[0]
        try:
            targets = [fn.value._obj.graph]
        except AttributeError:
            targets = None
        return self.generic_call(fn.concretetype, self.expr(fn),
                                 op.args[1:], op.result, targets)

    def OP_INDIRECT_CALL(self, op):
        fn = op.args[0]
        return self.generic_call(fn.concretetype, self.expr(fn),
                                 op.args[1:-1], op.result, op.args[-1].value)

    def OP_ADR_CALL(self, op):
        ARGTYPES = [v.concretetype for v in op.args[1:]]
        RESTYPE = op.result.concretetype
        FUNC = Ptr(FuncType(ARGTYPES, RESTYPE))
        typename = self.db.gettype(FUNC)
        fnaddr = op.args[0]
        fnexpr = '((%s)%s)' % (cdecl(typename, ''), self.expr(fnaddr))
        return self.generic_call(FUNC, fnexpr, op.args[1:], op.result)

    # low-level operations
    def generic_get(self, op, sourceexpr):
        T = self.lltypemap(op.result)
        newvalue = self.expr(op.result, special_case_void=False)
        result = '%s = %s;' % (newvalue, sourceexpr)
        if T is Void:
            result = '/* %s */' % result
        return result

    def generic_set(self, op, targetexpr):
        newvalue = self.expr(op.args[-1], special_case_void=False)
        result = '%s = %s;' % (targetexpr, newvalue)
        T = self.lltypemap(op.args[-1])
        if T is Void:
            result = '/* %s */' % result
        return result

    def OP_GETFIELD(self, op, ampersand=''):
        assert isinstance(op.args[1], Constant)
        STRUCT = self.lltypemap(op.args[0]).TO
        structdef = self.db.gettypedefnode(STRUCT)
        baseexpr_is_const = isinstance(op.args[0], Constant)
        expr = ampersand + structdef.ptr_access_expr(self.expr(op.args[0]),
                                                     op.args[1].value,
                                                     baseexpr_is_const)
        return self.generic_get(op, expr)

    def OP_BARE_SETFIELD(self, op):
        assert isinstance(op.args[1], Constant)
        STRUCT = self.lltypemap(op.args[0]).TO
        structdef = self.db.gettypedefnode(STRUCT)
        baseexpr_is_const = isinstance(op.args[0], Constant)
        expr = structdef.ptr_access_expr(self.expr(op.args[0]),
                                         op.args[1].value,
                                         baseexpr_is_const)
        return self.generic_set(op, expr)

    def OP_GETSUBSTRUCT(self, op):
        RESULT = self.lltypemap(op.result).TO
        if isinstance(RESULT, FixedSizeArray):
            return self.OP_GETFIELD(op, ampersand='')
        else:
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
        ptr = self.expr(op.args[0])
        index = self.expr(op.args[1])
        arraydef = self.db.gettypedefnode(ARRAY)
        return self.generic_get(op, arraydef.itemindex_access_expr(ptr, index))

    def OP_SETARRAYITEM(self, op):
        ARRAY = self.lltypemap(op.args[0]).TO
        ptr = self.expr(op.args[0])
        index = self.expr(op.args[1])
        arraydef = self.db.gettypedefnode(ARRAY)
        return self.generic_set(op, arraydef.itemindex_access_expr(ptr, index))
    OP_BARE_SETARRAYITEM = OP_SETARRAYITEM

    def OP_GETARRAYSUBSTRUCT(self, op):
        ARRAY = self.lltypemap(op.args[0]).TO
        ptr = self.expr(op.args[0])
        index = self.expr(op.args[1])
        arraydef = self.db.gettypedefnode(ARRAY)
        return '%s = &%s;' % (self.expr(op.result),
                              arraydef.itemindex_access_expr(ptr, index))

    def interior_expr(self, args, rettype=False):
        TYPE = args[0].concretetype.TO
        expr = self.expr(args[0])
        for i, arg in enumerate(args[1:]):
            defnode = self.db.gettypedefnode(TYPE)
            if arg.concretetype is Void:
                fieldname = arg.value
                if i == 0:
                    expr = defnode.ptr_access_expr(expr, fieldname)
                else:
                    expr = defnode.access_expr(expr, fieldname)
                if isinstance(TYPE, FixedSizeArray):
                    TYPE = TYPE.OF
                else:
                    TYPE = getattr(TYPE, fieldname)
            else:
                indexexpr = self.expr(arg)
                if i == 0:
                    expr = defnode.itemindex_access_expr(expr, indexexpr)
                else:
                    expr = defnode.access_expr_varindex(expr, indexexpr)
                TYPE = TYPE.OF
        if rettype:
            return expr, TYPE
        else:
            return expr

    def OP_GETINTERIORFIELD(self, op):
        return self.generic_get(op, self.interior_expr(op.args))

    def OP_BARE_SETINTERIORFIELD(self, op):
        return self.generic_set(op, self.interior_expr(op.args[:-1]))

    def OP_GETINTERIORARRAYSIZE(self, op):
        expr, ARRAY = self.interior_expr(op.args, True)
        if isinstance(ARRAY, FixedSizeArray):
            return '%s = %d;'%(self.expr(op.result), ARRAY.length)
        else:
            assert isinstance(ARRAY, Array)
            return '%s = %s.length;'%(self.expr(op.result), expr)



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

    def OP_BOEHM_MALLOC(self, op):
        return 'OP_BOEHM_ZERO_MALLOC(%s, %s, void*, 0, 0);' % (self.expr(op.args[0]),
                                                               self.expr(op.result))

    def OP_BOEHM_MALLOC_ATOMIC(self, op):
        return 'OP_BOEHM_ZERO_MALLOC(%s, %s, void*, 1, 0);' % (self.expr(op.args[0]),
                                                               self.expr(op.result))

    def OP_BOEHM_REGISTER_FINALIZER(self, op):
        return 'GC_REGISTER_FINALIZER(%s, (GC_finalization_proc)%s, NULL, NULL, NULL);' \
               % (self.expr(op.args[0]), self.expr(op.args[1]))

    def OP_RAW_MALLOC(self, op):
        eresult = self.expr(op.result)
        esize = self.expr(op.args[0])
        return "OP_RAW_MALLOC(%s, %s, void *);" % (esize, eresult)

    def OP_STACK_MALLOC(self, op):
        eresult = self.expr(op.result)
        esize = self.expr(op.args[0])
        return "OP_STACK_MALLOC(%s, %s, void *);" % (esize, eresult)

    def OP_DIRECT_FIELDPTR(self, op):
        return self.OP_GETFIELD(op, ampersand='&')

    def OP_DIRECT_ARRAYITEMS(self, op):
        ARRAY = self.lltypemap(op.args[0]).TO
        items = self.expr(op.args[0])
        if not isinstance(ARRAY, FixedSizeArray) and not barebonearray(ARRAY):
            items += '->items'
        return '%s = %s;' % (self.expr(op.result), items)

    def OP_DIRECT_PTRADD(self, op):
        ARRAY = self.lltypemap(op.args[0]).TO
        if ARRAY._hints.get("render_as_void"):
            return '%s = (char *)%s + %s;' % (
                self.expr(op.result), 
                self.expr(op.args[0]),
                self.expr(op.args[1]))
        else:
            return '%s = %s + %s;' % (
                self.expr(op.result),
                self.expr(op.args[0]),
                self.expr(op.args[1]))

    def OP_CAST_POINTER(self, op):
        TYPE = self.lltypemap(op.result)
        typename = self.db.gettype(TYPE)
        result = []
        result.append('%s = (%s)%s;' % (self.expr(op.result),
                                        cdecl(typename, ''),
                                        self.expr(op.args[0])))
        return '\t'.join(result)

    OP_CAST_PTR_TO_ADR = OP_CAST_POINTER
    OP_CAST_ADR_TO_PTR = OP_CAST_POINTER
    OP_CAST_OPAQUE_PTR = OP_CAST_POINTER

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
        v = op.args[0]
        TYPE = self.lltypemap(v)
        if TYPE is Void:
            return "/* kept alive: void */"
        if isinstance(TYPE, Ptr) and TYPE.TO._gckind == 'gc':
            meth = getattr(self.gcpolicy, 'GC_KEEPALIVE', None)
            if meth:
                return meth(self, v)
        return "/* kept alive: %s */" % self.expr(v)

    #address operations
    def OP_RAW_STORE(self, op):
        addr = self.expr(op.args[0])
        TYPE = op.args[1].value
        offset = self.expr(op.args[2])
        value = self.expr(op.args[3])
        typename = cdecl(self.db.gettype(TYPE).replace('@', '*@'), '')
        return "*(((%(typename)s) %(addr)s ) + %(offset)s) = %(value)s;" % locals()

    def OP_RAW_LOAD(self, op):
        addr = self.expr(op.args[0])
        TYPE = op.args[1].value
        offset = self.expr(op.args[2])
        result = self.expr(op.result)
        typename = cdecl(self.db.gettype(TYPE).replace('@', '*@'), '')
        return "%(result)s = *(((%(typename)s) %(addr)s ) + %(offset)s);" % locals()

    def OP_CAST_PRIMITIVE(self, op):
        TYPE = self.lltypemap(op.result)
        val =  self.expr(op.args[0])
        ORIG = self.lltypemap(op.args[0])
        if ORIG is Char:
            val = "(unsigned char)%s" % val
        elif ORIG is UniChar:
            val = "(unsigned long)%s" % val
        result = self.expr(op.result)
        typename = cdecl(self.db.gettype(TYPE), '')        
        return "%(result)s = (%(typename)s)(%(val)s);" % locals()

    OP_FORCE_CAST = OP_CAST_PRIMITIVE   # xxx the same logic works

    def OP_RESUME_POINT(self, op):
        return '/* resume point %s */'%(op.args[0],)

    def OP_DEBUG_PRINT(self, op):
        # XXX
        from pypy.rpython.lltypesystem.rstr import STR
        format = []
        argv = []
        free_line = ""
        for arg in op.args:
            T = arg.concretetype
            if T == Ptr(STR):
                if isinstance(arg, Constant):
                    format.append(''.join(arg.value.chars).replace('%', '%%'))
                else:
                    format.append('%s')
                    argv.append('RPyString_AsCharP(%s)' % self.expr(arg))
                    free_line = "RPyString_FreeCache();"
                continue
            elif T == Signed:
                format.append('%ld')
            elif T == Unsigned:
                format.append('%lu')
            elif T == Float:
                format.append('%f')
            elif isinstance(T, Ptr) or T == Address:
                format.append('%p')
            elif T == Char:
                if isinstance(arg, Constant):
                    format.append(arg.value.replace('%', '%%'))
                    continue
                format.append('%c')
            elif T == Bool:
                format.append('%s')
                argv.append('(%s) ? "True" : "False"' % self.expr(arg))
                continue
            elif T == SignedLongLong:
                if sys.platform == 'win32':
                    format.append('%I64d')
                else:
                    format.append('%lld')
            elif T == UnsignedLongLong:
                if sys.platform == 'win32':
                    format.append('%I64u')
                else:
                    format.append('%llu')
            else:
                raise Exception("don't know how to debug_print %r" % (T,))
            argv.append(self.expr(arg))
        argv.insert(0, c_string_constant(' '.join(format) + '\n'))
        return (
            "if (PYPY_HAVE_DEBUG_PRINTS) { fprintf(PYPY_DEBUG_FILE, %s); %s}"
            % (', '.join(argv), free_line))

    def _op_debug(self, opname, arg):
        if isinstance(arg, Constant):
            string_literal = c_string_constant(''.join(arg.value.chars))
            return "%s(%s);" % (opname, string_literal)
        else:
            x = "%s(RPyString_AsCharP(%s));\n" % (opname, self.expr(arg))
            x += "RPyString_FreeCache();"
            return x

    def OP_DEBUG_START(self, op):
        return self._op_debug('PYPY_DEBUG_START', op.args[0])

    def OP_DEBUG_STOP(self, op):
        return self._op_debug('PYPY_DEBUG_STOP', op.args[0])

    def OP_DEBUG_ASSERT(self, op):
        return 'RPyAssert(%s, %s);' % (self.expr(op.args[0]),
                                       c_string_constant(op.args[1].value))

    def OP_DEBUG_FATALERROR(self, op):
        # XXX
        from pypy.rpython.lltypesystem.rstr import STR
        msg = op.args[0]
        assert msg.concretetype == Ptr(STR)
        if isinstance(msg, Constant):
            msg = c_string_constant(''.join(msg.value.chars))
        else:
            msg = 'RPyString_AsCharP(%s)' % self.expr(msg)

        return 'fprintf(stderr, "%%s\\n", %s); abort();' % msg

    def OP_DEBUG_LLINTERPCALL(self, op):
        result = 'abort();  /* debug_llinterpcall should be unreachable */'
        TYPE = self.lltypemap(op.result)
        if TYPE is not Void:
            typename = self.db.gettype(TYPE)
            result += '\n%s = (%s)0;' % (self.expr(op.result),
                                         cdecl(typename, ''))
        return result

    def OP_INSTRUMENT_COUNT(self, op):
        counter_label = op.args[1].value
        self.db.instrument_ncounter = max(self.db.instrument_ncounter,
                                          counter_label+1)
        counter_label = self.expr(op.args[1])
        return 'INSTRUMENT_COUNT(%s);' % counter_label
            
    def OP_IS_EARLY_CONSTANT(self, op):
        return self.expr(op.result)  + ' = 0;' # Allways false

    def OP_JIT_MARKER(self, op):
        return '/* JIT_MARKER %s */' % op

    def OP_JIT_FORCE_VIRTUALIZABLE(self, op):
        return '/* JIT_FORCE_VIRTUALIZABLE %s */' % op

    def OP_JIT_FORCE_VIRTUAL(self, op):
        return '%s = %s; /* JIT_FORCE_VIRTUAL */' % (self.expr(op.result),
                                                     self.expr(op.args[0]))

    def OP_JIT_FORCE_QUASI_IMMUTABLE(self, op):
        return '/* JIT_FORCE_QUASI_IMMUTABLE %s */' % op

    def OP_GET_GROUP_MEMBER(self, op):
        typename = self.db.gettype(op.result.concretetype)
        return '%s = (%s)_OP_GET_GROUP_MEMBER(%s, %s);' % (
            self.expr(op.result),
            cdecl(typename, ''),
            self.expr(op.args[0]),
            self.expr(op.args[1]))

    def OP_GET_NEXT_GROUP_MEMBER(self, op):
        typename = self.db.gettype(op.result.concretetype)
        return '%s = (%s)_OP_GET_NEXT_GROUP_MEMBER(%s, %s, %s);' % (
            self.expr(op.result),
            cdecl(typename, ''),
            self.expr(op.args[0]),
            self.expr(op.args[1]),
            self.expr(op.args[2]))

    def getdebugfunctionname(self):
        name = self.functionname
        if not name:
            return "?"
        if name.startswith('pypy_g_'):
            name = name[7:]
        return name

    def OP_DEBUG_RECORD_TRACEBACK(self, op):
        #if self.functionname is None, we print "?" as the argument */
        return 'PYPY_DEBUG_RECORD_TRACEBACK("%s");' % (
            self.getdebugfunctionname(),)

    def OP_DEBUG_CATCH_EXCEPTION(self, op):
        gottype = self.expr(op.args[0])
        exprs = []
        for c_limited_type in op.args[1:]:
            exprs.append('%s == %s' % (gottype, self.expr(c_limited_type)))
        return 'PYPY_DEBUG_CATCH_EXCEPTION("%s", %s, %s);' % (
            self.getdebugfunctionname(), gottype, ' || '.join(exprs))

    def OP_INT_BETWEEN(self, op):
        if (isinstance(op.args[0], Constant) and
            isinstance(op.args[2], Constant) and
            op.args[2].value - op.args[0].value == 1):
            # (a <= b < a+1) ----> (b == a)
            return '%s = (%s == %s);  /* was INT_BETWEEN */' % (
                self.expr(op.result),
                self.expr(op.args[1]),
                self.expr(op.args[0]))
        else:
            return None    # use the default

assert not USESLOTS or '__dict__' not in dir(FunctionCodeGenerator)
