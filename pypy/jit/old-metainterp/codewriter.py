from pypy.annotation import model as annmodel
from pypy.rpython.lltypesystem import lltype, llmemory, rstr
from pypy.objspace.flow.model import Variable, Constant, Link, c_last_exception
from pypy.rlib import objectmodel
from pypy.rlib.objectmodel import we_are_translated
from pypy.jit.metainterp.history import Const, getkind, getkind_num
from pypy.jit.metainterp import heaptracker, support, history

import py
from pypy.tool.ansi_print import ansi_log
log = py.log.Producer('jitcodewriter')
py.log.setconsumer('jitcodewriter', ansi_log)

MAX_MAKE_NEW_VARS = 16


class BuiltinDescr(history.AbstractValue):
    pass

class ListDescr(BuiltinDescr):
    def __init__(self, getfunc, setfunc, malloc_func, append_func,
                 pop_func, insert_func, len_func, nonzero_func, tp):
        self.setfunc      = setfunc
        self.getfunc      = getfunc
        self.malloc_func  = malloc_func
        self.append_func  = append_func
        self.insert_func  = insert_func
        self.pop_func     = pop_func
        self.len_func     = len_func
        self.nonzero_func = nonzero_func
        self.tp           = tp
    
    def equals(self, other):
        if isinstance(other, ListDescr):
            return True
        return False

class JitCode(history.AbstractValue):
    def __init__(self, name):
        self.name = name

    def setup(self, code, constants):
        self.code = code
        self.constants = constants

    def __repr__(self):
        return '<JitCode %r>' % (getattr(self, 'name', '?'),)

    def dump(self, file=None):
        import dump
        dump.dump_bytecode(self, file=file)
        print >> file


class IndirectCallset(history.AbstractValue):
    def __init__(self, codewriter, graphs):
        keys = []
        values = []
        for graph in graphs:
            fnptr = codewriter.rtyper.getcallable(graph)
            keys.append(llmemory.cast_ptr_to_adr(fnptr))
            values.append(codewriter.get_jitcode(graph))

        def bytecode_for_address(fnaddress):
            if we_are_translated():
                if self.dict is None:
                    # Build the dictionary at run-time.  This is needed
                    # because the keys are function addresses, so they
                    # can change from run to run.
                    self.dict = {}
                    for i in range(len(keys)):
                        self.dict[keys[i]] = values[i]
                return self.dict[fnaddress]
            else:
                for i in range(len(keys)):
                    if fnaddress == keys[i]:
                        return values[i]
                raise KeyError(fnaddress)
        self.bytecode_for_address = bytecode_for_address
        self.dict = None

# ____________________________________________________________


class CodeWriter(object):

    def __init__(self, metainterp, policy):
        self.all_prebuilt_values = {}
        self.all_graphs = {}
        self.all_indirectcallsets = {}
        self.all_listdescs = {}
        self.unfinished_graphs = []
        self.metainterp = metainterp
        self.rtyper = metainterp.cpu.rtyper
        self.cpu = metainterp.cpu
        self.policy = policy
        self.list_cache = {}

    def make_portal_bytecode(self, graph):
        log.info("making JitCodes...")
        jitcode = self.make_one_bytecode(graph, True)
        while self.unfinished_graphs:
            graph = self.unfinished_graphs.pop()
            self.make_one_bytecode(graph, False)
        log.info("there are %d JitCode instances." % len(self.all_graphs))
        return jitcode

    def make_one_bytecode(self, graph, portal):
        maker = BytecodeMaker(self, graph, portal)
        if not hasattr(maker.bytecode, 'code'):
            maker.assemble()
        return maker.bytecode

    def get_jitcode(self, graph):
        if graph in self.all_graphs:
            return self.all_graphs[graph]
        bytecode = JitCode(graph.name)      # 'graph.name' is for dump()
        self.all_graphs[graph] = bytecode
        self.unfinished_graphs.append(graph)
        return bytecode

    def get_indirectcallset(self, graphs):
        key = tuple(sorted(graphs))
        try:
            result = self.all_indirectcallsets[key]
        except KeyError:
            result = self.all_indirectcallsets[key] = \
                                  IndirectCallset(self, graphs)
        return result

    def get_list_desc(self, LIST):
        try:
            return self.all_listdescs[LIST]
        except KeyError:
            import vlist
            listdesc = vlist.ListClassDesc(self, LIST)
            self.all_listdescs[LIST] = listdesc
            return listdesc

    def register_list_op(self, llfunc, oopspec_name, LIST):
        metainterp = self.metainterp
        if llfunc._obj not in metainterp.builtins_seen:
            metainterp.builtins_seen[llfunc._obj] = True
            key = llmemory.cast_ptr_to_adr(llfunc)
            value = (oopspec_name.replace('.', '_'), self.get_list_desc(LIST))
            metainterp.builtins_keys.append(key)
            metainterp.builtins_values.append(value)


    def list_descr_for_tp(self, TP):
        try:
            return self.list_cache[TP.TO]
        except KeyError:
            if isinstance(TP.TO, lltype.GcStruct):
                OF = TP.TO.items.TO.OF
            else:
                OF = TP.TO.OF
            rtyper = self.rtyper
            args = [TP, lltype.Signed, OF]
            setfunc, _ = support.builtin_func_for_spec(rtyper, 'list.setitem',
                                                       args, lltype.Void)
            getfunc, _ = support.builtin_func_for_spec(rtyper, 'list.getitem',
                                                       args[:-1], OF)
            malloc_func, _ = support.builtin_func_for_spec(rtyper, 'newlist',
                                                           [lltype.Signed], TP)
            len_func, _ = support.builtin_func_for_spec(rtyper, 'list.len',
                                                        [TP], lltype.Signed)
            nonzero_func, _ = support.builtin_func_for_spec(rtyper,
                                                            'list.nonzero',
                                                            [TP], lltype.Bool)

            if isinstance(TP.TO, lltype.GcStruct):
                append_func, _ = support.builtin_func_for_spec(rtyper,
                                                               'list.append',
                                                        [TP, OF], lltype.Void)
                pop_func, _ = support.builtin_func_for_spec(rtyper, 'list.pop',
                                                            [TP], OF)
                insert_func, _ = support.builtin_func_for_spec(rtyper,
                      'list.insert', [TP, lltype.Signed, OF], lltype.Void)
            if isinstance(OF, lltype.Number):
                tp = "int"
            else:
                tp = "ptr"
            if isinstance(TP.TO, lltype.GcStruct):
                ld = ListDescr(history.ConstAddr(getfunc.value, self.cpu),
                               history.ConstAddr(setfunc.value, self.cpu),
                               history.ConstAddr(malloc_func.value, self.cpu),
                               history.ConstAddr(append_func.value, self.cpu),
                               history.ConstAddr(pop_func.value, self.cpu),
                               history.ConstAddr(insert_func.value, self.cpu),
                               history.ConstAddr(len_func.value, self.cpu),
                               history.ConstAddr(nonzero_func.value, self.cpu),
                               tp)
            else:
                ld = ListDescr(history.ConstAddr(getfunc.value, self.cpu),
                               history.ConstAddr(setfunc.value, self.cpu),
                               history.ConstAddr(malloc_func.value, self.cpu),
                               None, None, None,
                               history.ConstAddr(len_func.value, self.cpu),
                               history.ConstAddr(nonzero_func.value, self.cpu),
                               tp)
            self.list_cache[TP.TO] = ld
            return ld

    

class BytecodeMaker(object):
    debug = True
    
    def __init__(self, codewriter, graph, portal):
        self.codewriter = codewriter
        self.cpu = codewriter.metainterp.cpu
        self.graph = graph
        self.portal = portal
        self.bytecode = self.codewriter.get_jitcode(self.graph)

    def assemble(self):
        """Assemble the opcodes for self.bytecode."""
        self.assembler = []
        self.constants = []
        self.positions = {}
        self.blocks = {}
        self.seen_blocks = {}
        self.dont_minimize_variables = 0
        self.pending_exception_handlers = []
        self.make_bytecode_block(self.graph.startblock)
        while self.pending_exception_handlers:
            self.make_exception_handler(self.pending_exception_handlers.pop())

        labelpos = {}
        code = assemble(labelpos, self.codewriter.metainterp, self.assembler)
        self.bytecode.setup(code, self.constants)

        self.bytecode._source = self.assembler
        self.bytecode._metainterp = self.codewriter.metainterp
        self.bytecode._labelpos = labelpos
        if self.debug:
            self.bytecode.dump()

    def const_position(self, constvalue):
        """Generate a constant of the given value.
        Returns its index in the list self.positions[].
        """
        const = Const._new(constvalue, self.cpu)
        return self.get_position(const)

    def get_position(self, x):
        """'x' must be an instance of Const or one of the special
        subclasses of AbstractValue like JitCode.  Returns its
        index in the list self.positions[].
        """
        x = self.codewriter.all_prebuilt_values.setdefault(x, x)
        try:
            result = self.positions[x]
        except KeyError:
            result = self.positions[x] = len(self.constants)
            self.constants.append(x)
        return result

    def make_bytecode_block(self, block):
        if block.exits == ():
            if len(block.inputargs) == 1:
                # return from function
                returnvar, = block.inputargs
                if returnvar.concretetype is lltype.Void:
                    self.emit("void_return")
                else:
                    self.emit("return")
            elif len(block.inputargs) == 2:
                # exception block, raising an exception from a function
                self.emit("raise")
            else:
                raise Exception("?")
            return
        if block in self.seen_blocks:
            self.emit("goto")
            self.emit(tlabel(block))
            return
        # inserting a goto not necessary, falling through
        self.seen_blocks[block] = True
        self.free_vars = 0
        self.var_positions = {}
        for arg in block.inputargs:
            self.register_var(arg, verbose=False)
        self.emit(label(block))
        #self.make_prologue(block)

        operations = block.operations
        if block.exitswitch == c_last_exception:
            operations = operations[:-1]

        for i, op in enumerate(operations):
            self.current_position = block, i
            self.serialize_op(op)

        if block.exitswitch == c_last_exception:
            i = len(operations)
            op = block.operations[i]
            self.current_position = block, i
            self.serialize_setup_exception_block(block.exits[1:])
            self.serialize_op(op)
            self.serialize_teardown_exception_block()

        self.current_position = block, len(block.operations)
        self.insert_exits(block)

    def insert_exits(self, block):
        if len(block.exits) == 1 or block.exitswitch == c_last_exception:
            link = block.exits[0]
            assert link.exitcase is None
            self.emit(*self.insert_renaming(link.args))
            self.make_bytecode_block(link.target)
        elif (len(block.exits) == 2
              and block.exitswitch.concretetype == lltype.Bool):
            self.minimize_variables()
            linkfalse, linktrue = block.exits
            if linkfalse.llexitcase == True:
                linkfalse, linktrue = linktrue, linkfalse
            truerenaming = self.insert_renaming(linktrue.args)
            falserenaming = self.insert_renaming(linkfalse.args)
            self.emit("goto_if_not",
                      self.var_position(block.exitswitch),
                      tlabel(linkfalse))
            self.emit(*truerenaming)
            self.make_bytecode_block(linktrue.target)
            self.emit(label(linkfalse))
            self.emit(*falserenaming)
            self.make_bytecode_block(linkfalse.target)
        else:
            self.minimize_variables()
            switches = [link for link in block.exits
                        if link.exitcase != 'default']
            renamings = [self.insert_renaming(link.args)
                         for link in switches]
            self.emit("switch",
                      self.var_position(block.exitswitch))
            self.emit_list([link.llexitcase for link in switches])
            self.emit_list([tlabel(link) for link in switches])
            if block.exits[-1].exitcase == 'default':
                link = block.exits[-1]
                self.emit(*self.insert_renaming(link.args))
                self.make_bytecode_block(link.target)
            for renaming, link in zip(renamings, switches):
                self.emit(label(link))
                self.emit(*renaming)
                self.make_bytecode_block(link.target)

    def serialize_setup_exception_block(self, exception_exits):
        self.minimize_variables()
        self.dont_minimize_variables += 1
        handler = object()
        renamings = []
        for link in exception_exits:
            args_without_last_exc = [v for v in link.args
                                       if (v is not link.last_exception and
                                           v is not link.last_exc_value)]
            renamings.append(self.insert_renaming(args_without_last_exc))
        self.pending_exception_handlers.append((handler, exception_exits,
                                                renamings))
        self.emit("setup_exception_block",
                  tlabel(handler))

    def serialize_teardown_exception_block(self):
        self.emit("teardown_exception_block")
        self.dont_minimize_variables -= 1

    def make_exception_handler(self, (handler, exception_exits, renamings)):
        self.emit(label(handler))
        if not exception_exits:
            self.emit("reraise")
            return
        nexthandler = object()
        link = exception_exits[0]
        if link.exitcase is not Exception:
            self.emit("goto_if_exception_mismatch",
                      self.const_position(link.llexitcase),
                      tlabel(nexthandler))
            self.pending_exception_handlers.append((nexthandler,
                                                    exception_exits[1:],
                                                    renamings[1:]))
        assert link.last_exception is not None
        assert link.last_exc_value is not None
        self.emit(*renamings[0])
        for i, v in enumerate(link.args):
            if v is link.last_exception:
                self.emit("put_last_exception", i)
            if v is link.last_exc_value:
                self.emit("put_last_exc_value", i)
        self.make_bytecode_block(link.target)

    def insert_renaming(self, args):
        args = [v for v in args if v.concretetype is not lltype.Void]
        if len(args) >= MAX_MAKE_NEW_VARS:
            code = ["make_new_vars", len(args)]
        else:
            code = ["make_new_vars_%d" % len(args)]
        for v in args:
            code.append(self.var_position(v))
        return code

    def minimize_variables(self):
        if self.dont_minimize_variables:
            return
        block, index = self.current_position
        vars = self.vars_alive_through_op(block, index)
        self.emit(*self.insert_renaming(vars))
        self.free_vars = 0
        self.var_positions.clear()
        for v in vars:
            self.register_var(v, verbose=False)

    def vars_alive_through_op(self, block, index):
        """Returns the list of variables that are really used by or after
        the operation at 'index'.
        """
        result = []
        seen = {}
        def see(v):
            if isinstance(v, Variable) and v not in seen:
                result.append(v)
                seen[v] = True
        # don't include the variables produced by the current or future
        # operations
        for op in block.operations[index:]:
            seen[op.result] = True
        # but include the variables consumed by the current or any future
        # operation
        for op in block.operations[index:]:
            for v in op.args:
                see(v)
        see(block.exitswitch)
        for link in block.exits:
            for v in link.args:
                if v not in (link.last_exception, link.last_exc_value):
                    see(v)
        return result

    def serialize_op(self, op):
        specialcase = getattr(self, "serialize_op_%s" % (op.opname, ),
                              self.default_serialize_op)
        specialcase(op)

    def default_serialize_op(self, op, opname=None):
        self.emit(opname or op.opname)
        for arg in op.args:
            self.emit(self.var_position(arg))
        self.register_var(op.result)

    # ----------

    def serialize_op_same_as(self, op):
        if op.args[0].concretetype is not lltype.Void:
            self.var_positions[op.result] = self.var_position(op.args[0])

    serialize_op_cast_pointer = serialize_op_same_as
    serialize_op_cast_int_to_char = serialize_op_same_as
    serialize_op_cast_char_to_int = serialize_op_same_as
    serialize_op_cast_bool_to_int = serialize_op_same_as

    def serialize_op_char_eq(self, op):
        self.default_serialize_op(op, 'int_eq')

    def serialize_op_char_ne(self, op):
        self.default_serialize_op(op, 'int_ne')

    serialize_op_unichar_eq = serialize_op_char_eq
    serialize_op_unichar_ne = serialize_op_char_ne

    def serialize_op_hint(self, op):
        hints = op.args[1].value
        if hints.get('promote') and op.args[0].concretetype is not lltype.Void:
            self.minimize_variables()
            self.emit('guard_value', self.var_position(op.args[0]))
            self.register_var(op.result)
        else:
            xxx

    def serialize_op_int_is_true(self, op):
        if isinstance(op.args[0], Constant):
            if op.args[0].value is objectmodel.malloc_zero_filled:
                self.var_positions[op.result] = self.var_position(Constant(1))
                return
        self.emit('int_is_true', self.var_position(op.args[0]))
        self.register_var(op.result)

    def serialize_op_malloc(self, op):
        assert op.args[1].value == {'flavor': 'gc'}
        STRUCT = op.args[0].value
        vtable = heaptracker.get_vtable_for_gcstruct(self.cpu, STRUCT)
        if vtable:
            # store the vtable as an address -- that's fine, because the
            # GC doesn't need to follow them
            self.emit('new_with_vtable',
                      self.cpu.sizeof(STRUCT),
                      self.const_position(vtable))
        else:
            self.emit('new', self.cpu.sizeof(STRUCT))
        self.register_var(op.result)

    def serialize_op_malloc_varsize(self, op):
        # XXX strings only for now
        assert op.args[0].value == rstr.STR
        assert op.args[1].value == {'flavor': 'gc'}
        self.emit('newstr', self.var_position(op.args[2]))
        self.register_var(op.result)

    def serialize_op_zero_gc_pointers_inside(self, op):
        pass   # XXX assume Boehm for now

    def serialize_op_getfield(self, op):
        if self.is_typeptr_getset(op):
            self.handle_getfield_typeptr(op)
            return
        # check for deepfrozen structures that force constant-folding
        #pure = self.codewriter.is_green_var(op.result)
        if op.args[0].concretetype.TO._hints.get('immutable'):
            opname = 'getfield_pure'
        else:
            opname = 'getfield'
        # turn the flow graph 'getfield' operation into our own version
        [v_inst, c_fieldname] = op.args
        RESULT = op.result.concretetype
        if RESULT is lltype.Void:
            return
        argname = v_inst.concretetype.TO._gckind
        self.emit('%s_%s' % (opname, argname))
        self.emit(self.var_position(v_inst))
        offset = self.cpu.fielddescrof(v_inst.concretetype.TO,
                                       c_fieldname.value)
        self.emit(offset)
        self.register_var(op.result)
        self._eventualy_builtin(op.result)

    def serialize_op_setfield(self, op):
        if self.is_typeptr_getset(op):
            # ignore the operation completely -- instead, it's done by 'new'
            return
        # turn the flow graph 'setfield' operation into our own version
        [v_inst, c_fieldname, v_value] = op.args
        RESULT = v_value.concretetype
        if RESULT is lltype.Void:
            return
        argname = v_inst.concretetype.TO._gckind
        self.emit('setfield_%s' % (argname,))
        self.emit(self.var_position(v_inst))
        offset = self.cpu.fielddescrof(v_inst.concretetype.TO,
                                       c_fieldname.value)
        self.emit(offset)
        self.emit(self.var_position(v_value))

    def is_typeptr_getset(self, op):
        return (op.args[1].value == 'typeptr' and
                op.args[0].concretetype.TO._hints.get('typeptr'))

    def handle_getfield_typeptr(self, op):
        # special-casing for getting the typeptr of an object
        self.minimize_variables()
        self.emit('guard_class', self.var_position(op.args[0]))
        self.register_var(op.result)

    def serialize_op_getinteriorarraysize(self, op):
        # XXX only supports strings for now
        assert op.args[0].concretetype == lltype.Ptr(rstr.STR)
        assert len(op.args) == 2
        assert op.args[1].value == 'chars'
        self.emit("strlen", self.var_position(op.args[0]))
        self.register_var(op.result)

    def serialize_op_getinteriorfield(self, op):
        # XXX only supports strings for now
        assert op.args[0].concretetype == lltype.Ptr(rstr.STR)
        assert len(op.args) == 3
        assert op.args[1].value == 'chars'
        self.emit("strgetitem", self.var_position(op.args[0]),
                                self.var_position(op.args[2]))
        self.register_var(op.result)

    def serialize_op_setinteriorfield(self, op):
        # XXX only supports strings for now
        assert op.args[0].concretetype == lltype.Ptr(rstr.STR)
        assert len(op.args) == 4
        assert op.args[1].value == 'chars'
        self.emit("strsetitem", self.var_position(op.args[0]),
                                self.var_position(op.args[2]),
                                self.var_position(op.args[3]))

    def serialize_op_jit_marker(self, op):
        assert self.portal, "jit_marker in non-main graph!"
        if op.args[0].value == 'jit_merge_point':
            self.emit('jit_merge_point')
            assert ([self.var_position(i) for i in op.args[2:]] ==
                    range(0, 2*(len(op.args) - 2), 2))
            for i in range(2, len(op.args)):
                arg = op.args[i]
                self._eventualy_builtin(arg)
            
        elif op.args[0].value == 'can_enter_jit':
            self.emit('can_enter_jit')
            self.emit_varargs(op.args[2:])

    def _eventualy_builtin(self, arg, need_length=True):
        if isinstance(arg.concretetype, lltype.Ptr):
            # XXX very complex logic for getting all things
            # that are pointers, but not objects
            is_list = False
            if isinstance(arg.concretetype.TO, lltype.GcArray):
                is_list = True
            if isinstance(arg.concretetype.TO, lltype.GcStruct):
                if arg.concretetype.TO._hints.get('list'):
                    is_list = True
            if is_list:
                descr = self.codewriter.list_descr_for_tp(arg.concretetype)
                self.emit('guard_builtin', self.var_position(arg),
                          self.get_position(descr))
                if need_length:
                    self.emit('guard_len', self.var_position(arg),
                              self.get_position(descr))

    #def serialize_op_direct_call(self, op):
    #    color = support.guess_call_kind(self.codewriter.hannotator, op)
    #    return getattr(self, 'handle_%s_call' % color)(op)

    def serialize_op_direct_call(self, op):
        self.minimize_variables()
        color = self.codewriter.policy.guess_call_kind(op)
        return getattr(self, 'handle_%s_call' % color)(op)

    def handle_regular_call(self, op):
        [targetgraph] = self.codewriter.policy.graphs_from(op)
        jitbox = self.codewriter.get_jitcode(targetgraph)
        self.emit('call')
        self.emit(self.get_position(jitbox))
        self.emit_varargs([x for x in op.args[1:]
                           if x.concretetype is not lltype.Void])
        self.register_var(op.result)

#     def handle_green_call(self, op):
#         assert op.result.concretetype is not lltype.Void
#         self.emit('green_call_%s' % getkind_num(self.cpu,
#                                                 op.result.concretetype))
#         self.emit_varargs([x for x in op.args
#                              if x.concretetype is not lltype.Void])
#         self.register_var(op.result)

    def handle_residual_call(self, op):
        self.emit('residual_call_%s' % getkind_num(self.cpu,
                                                   op.result.concretetype))
        self.emit_varargs([x for x in op.args
                             if x.concretetype is not lltype.Void])
        self.register_var(op.result)

    def handle_builtin_call(self, op):
        oopspec_name, args = support.decode_builtin_call(op)
        ll_args = [v.concretetype for v in args]
        c_func, TP = support.builtin_func_for_spec(self.codewriter.rtyper,
                                                   oopspec_name, ll_args,
                                                   op.result.concretetype)
        if oopspec_name.startswith('list') or oopspec_name == 'newlist':
            if oopspec_name.startswith('list.getitem'):
                opname = oopspec_name[len('list.'):]
            elif oopspec_name.startswith('list.setitem'):
                opname = oopspec_name[len('list.'):]
            elif oopspec_name == 'newlist':
                opname = 'newlist'
            elif oopspec_name == 'list.append':
                opname = 'append'
            elif oopspec_name == 'list.pop':
                opname = 'pop'
            elif oopspec_name == 'list.len':
                opname = 'len'
            elif oopspec_name == 'list.insert':
                opname = 'insert'
            elif oopspec_name == 'list.nonzero':
                opname = 'listnonzero'
            else:
                raise NotImplementedError("not supported %s" % oopspec_name)
            self.emit(opname)
            ld = self.codewriter.list_descr_for_tp(TP)
            self.emit(self.get_position(ld))
            self.emit_varargs(args)
            self.register_var(op.result)
            if opname == 'newlist':
                self._eventualy_builtin(op.result, False)
            return
        if oopspec_name.endswith('_foldable'):
            opname = 'green_call_%s'
        else:
            opname = 'residual_call_%s'
        self.emit(opname % getkind_num(self.cpu, op.result.concretetype))
        self.emit_varargs([c_func] + args)
        self.register_var(op.result)

#     def serialize_op_indirect_call(self, op):
#         xxx
#         color = support.guess_call_kind(self.codewriter.hannotator, op)
#         return getattr(self, 'handle_%s_indirect_call' % color)(op)

#     def handle_red_indirect_call(self, op):
#         # indirect_call to a red function pointer
#         # XXX for now, this is handled as a residual call
#         self.handle_residual_indirect_call(op)

#     def handle_direct_indirect_call(self, op):
#         # indirect_call to a green function pointer
#         self.minimize_variables()
#         targets = support.graphs_from(self.codewriter.hannotator, op)
#         indirectcallset = self.codewriter.get_indirectcallset(targets)
#         self.emit('direct_indirect_call')
#         self.emit(self.get_position(indirectcallset))
#         self.emit(self.var_position(op.args[0]))
#         self.emit_varargs([x for x in op.args[1:-1]
#                              if x.concretetype is not lltype.Void])
#         self.register_var(op.result)

    def serialize_op_indirect_call(self, op):
        self.minimize_variables()
        targets = self.codewriter.policy.graphs_from(op)
        indirectcallset = self.codewriter.get_indirectcallset(targets)
        self.emit('indirect_call')
        self.emit(self.get_position(indirectcallset))
        self.emit(self.var_position(op.args[0]))
        self.emit_varargs([x for x in op.args[1:-1]
                             if x.concretetype is not lltype.Void])
        self.register_var(op.result)
        
    def serialize_op_debug_assert(self, op):
        pass     # for now

    def serialize_op_promote_virtualizable(self, op):
        STRUCTTYPE = op.args[0].concretetype.TO
        argname = op.args[1].value
        FIELDTYPE = getattr(STRUCTTYPE, argname)
        if FIELDTYPE != lltype.Void:
            TOPSTRUCT = heaptracker.cast_vable_type(STRUCTTYPE)
            metainterp = self.codewriter.metainterp
            try:
                virtualizabledesc = metainterp._virtualizabledescs[TOPSTRUCT]
            except KeyError:
                from pypy.jit.metainterp import virtualizable
                virtualizabledesc = virtualizable.VirtualizableDesc(
                    self.cpu, TOPSTRUCT)
                virtualizabledesc.hash = len(metainterp._virtualizabledescs)
                metainterp._virtualizabledescs[TOPSTRUCT] = virtualizabledesc
                metainterp._can_have_virtualizables = virtualizabledesc
                #             ^^^ stays None if this code is never seen
            guard_field = self.cpu.fielddescrof(STRUCTTYPE, argname)
            self.emit('guard_nonvirtualized')
            self.emit(self.var_position(op.args[0]))
            self.emit(self.get_position(virtualizabledesc))
            self.emit(guard_field)

    # ----------

    def register_var(self, arg, verbose=True):
        """Register a variable 'arg' as just created.  This records the
        variable in self.var_positions[].
        """
        assert arg not in self.var_positions
        if arg.concretetype is not lltype.Void:
            where = self.free_vars
            self.free_vars += 1
            if verbose:
                self.emit('# => r%d' % (where,))
            self.var_positions[arg] = where * 2

    def var_position(self, v):
        """Return an integer uniquely identifying a Box or Const 'v'.
        It is even for Boxes and uneven for Consts.
        """
        if isinstance(v, Constant):
            i = self.const_position(v.value)
            return i * 2 + 1
        else:
            return self.var_positions[v]

    def emit(self, *stuff):
        self.assembler.extend(stuff)

    def emit_varargs(self, varargs):
        self.emit_list(map(self.var_position, varargs))

    def emit_list(self, l):
        self.emit(len(l))
        self.emit(*l)

# ____________________________________________________________

class label(object):
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return "label(%r)" % (self.name, )

class tlabel(object):
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return "tlabel(%r)" % (self.name, )

def encode_int(index):
    assert index >= 0
    result = []
    while True:
        byte = index & 0x7F
        index >>= 7
        result.append(chr(byte + 0x80 * bool(index)))
        if not index:
            break
    return result

def assemble(labelpos, metainterp, assembler):
    result = []
    for arg in assembler:
        if isinstance(arg, str):
            if arg.startswith('#'):     # skip comments
                continue
            #if arg == 'green':
            #    XXX should be removed and transformed into a list constant
            opcode = metainterp.find_opcode(arg)
            result.append(chr(opcode))
        elif isinstance(arg, bool):
            result.append(chr(int(arg)))
        elif isinstance(arg, int):
            result.extend(encode_int(arg))
        elif isinstance(arg, label):
            labelpos[arg.name] = len(result)
        elif isinstance(arg, tlabel):
            result.extend((arg, None, None))
        else:
            assert "don't know how to emit %r" % (arg, )
    for i in range(len(result)):
        b = result[i]
        if isinstance(b, tlabel):
            for j in range(1, 3):
                assert result[i + j] is None
            index = labelpos[b.name]
            assert 0 <= index <= 0xFFFFFF
            result[i + 0] = chr((index >> 16) & 0xff)
            result[i + 1] = chr((index >>  8) & 0xff)
            result[i + 2] = chr(index & 0xff)
    return "".join(result)
