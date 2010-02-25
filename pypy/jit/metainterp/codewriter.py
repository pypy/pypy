from pypy.annotation import model as annmodel
from pypy.rpython.lltypesystem import lltype, llmemory, rstr, rclass
from pypy.rpython.ootypesystem import ootype
from pypy.rpython import rlist
from pypy.objspace.flow.model import Variable, Constant, Link, c_last_exception
from pypy.rlib import objectmodel
from pypy.rlib.objectmodel import we_are_translated
from pypy.rlib.jit import _we_are_jitted
from pypy.jit.metainterp.history import Const, getkind, dict_equal_consts
from pypy.jit.metainterp import heaptracker, support, history
from pypy.tool.udir import udir
from pypy.translator.simplify import get_funcobj, get_functype
from pypy.translator.backendopt.canraise import RaiseAnalyzer
from pypy.translator.backendopt.writeanalyze import ReadWriteAnalyzer
from pypy.jit.metainterp.typesystem import deref, arrayItem, fieldType
from pypy.jit.metainterp.effectinfo import effectinfo_from_writeanalyze
from pypy.jit.metainterp.effectinfo import VirtualizableAnalyzer

import py, sys
from pypy.tool.ansi_print import ansi_log
log = py.log.Producer('jitcodewriter')
py.log.setconsumer('jitcodewriter', ansi_log)

MAX_MAKE_NEW_VARS = 16


class JitCode(history.AbstractValue):
    def __init__(self, name, cfnptr=None, calldescr=None, called_from=None,
                 graph=None):
        self.name = name
        self.cfnptr = cfnptr
        self.calldescr = calldescr
        self.called_from = called_from
        self.graph = graph

    def setup(self, code, constants):
        self.code = code
        self.constants = constants

    def __repr__(self):
        return '<JitCode %r>' % (getattr(self, 'name', '?'),)

    def dump(self, file=None):
        import dump
        dump.dump_bytecode(self, file=file)
        print >> file

class SwitchDict(history.AbstractValue):
    "Get a 'dict' attribute mapping integer values to bytecode positions."

# ____________________________________________________________


class CodeWriter(object):
    portal_graph = None

    def __init__(self, rtyper):
        self.rtyper = rtyper
        self.candidate_graphs = None
        self.all_prebuilt_values = dict_equal_consts()
        self.all_indirect_call_targets = {}
        self.all_graphs = {}
        self.all_methdescrs = {}
        self.all_listdescs = {}
        self.unfinished_graphs = []
        self.counter = 0
        self.class_sizes = []
        self._class_sizes_seen = {}
        self.list_of_addr2name = []
        self._functions_addr_seen = {}

        # set later with .start()
        self.metainterp_sd = None
        self.cpu = None
        self.portal_runner_ptr = None
        self.raise_analyzer = None
        self.jitdriver = None

    def find_all_graphs(self, portal_graph, leave_graph,
                        policy, supports_floats):
        from pypy.translator.simplify import get_graph
        def is_candidate(graph):
            return policy.look_inside_graph(graph)
        policy.set_supports_floats(supports_floats)
        
        todo = [portal_graph]
        if leave_graph is not None:
            todo.append(leave_graph)        
        self.candidate_graphs = seen = set(todo)

        def callers():
            graph = top_graph
            print graph
            while graph in coming_from:
                graph = coming_from[graph]
                print '<-', graph
        coming_from = {}

        while todo:
            top_graph = todo.pop()
            for _, op in top_graph.iterblockops():
                if op.opname not in ("direct_call", "indirect_call", "oosend"):
                    continue
                kind = self.guess_call_kind(op, is_candidate)
                # use callers() to view the calling chain in pdb
                if kind != "regular":
                    continue
                for graph in self.graphs_from(op, is_candidate):
                    if graph in seen:
                        continue
                    assert is_candidate(graph)
                    todo.append(graph)
                    seen.add(graph)
                    coming_from[graph] = top_graph
        return self.candidate_graphs

    def graphs_from(self, op, is_candidate=None):
        if is_candidate is None:
            is_candidate = self.is_candidate
        if op.opname == 'direct_call':
            funcobj = get_funcobj(op.args[0].value)
            graph = funcobj.graph
            if is_candidate(graph):
                return [graph]     # common case: look inside this graph
        else:
            assert op.opname in ('indirect_call', 'oosend')
            if op.opname == 'indirect_call':
                graphs = op.args[-1].value
            else:
                v_obj = op.args[1].concretetype
                graphs = v_obj._lookup_graphs(op.args[0].value)
            if graphs is not None:
                result = []
                for graph in graphs:
                    if is_candidate(graph):
                        result.append(graph)
                if result:
                    return result  # common case: look inside these graphs,
                                   # and ignore the others if there are any
            else:
                # special case: handle the indirect call that goes to
                # the 'instantiate' methods.  This check is a bit imprecise
                # but it's not too bad if we mistake a random indirect call
                # for the one to 'instantiate'.
                CALLTYPE = op.args[0].concretetype
                if (op.opname == 'indirect_call' and len(op.args) == 2 and
                    CALLTYPE == rclass.OBJECT_VTABLE.instantiate):
                    return list(self._graphs_of_all_instantiate())
        # residual call case: we don't need to look into any graph
        return None

    def _graphs_of_all_instantiate(self        ):
        for vtable in self.rtyper.lltype2vtable.values():
            if vtable.instantiate:
                yield vtable.instantiate._obj.graph
                
    def guess_call_kind(self, op, is_candidate=None):
        if op.opname == 'direct_call':
            funcptr = op.args[0].value
            if funcptr is self.portal_runner_ptr:
                return 'recursive'
            funcobj = get_funcobj(funcptr)
            if getattr(funcobj, 'graph', None) is None:
                return 'residual'
            targetgraph = funcobj.graph
            if (hasattr(targetgraph, 'func') and
                hasattr(targetgraph.func, 'oopspec')):
                return 'builtin'
        elif op.opname == 'oosend':
            SELFTYPE, methname, opargs = support.decompose_oosend(op)
            if SELFTYPE.oopspec_name is not None:
                return 'builtin'
        if self.graphs_from(op, is_candidate) is None:
            return 'residual'
        return 'regular'

    def is_candidate(self, graph):
        return graph in self.candidate_graphs


    def generate_bytecode(self, metainterp_sd, portal_graph, leave_graph,
                          portal_runner_ptr):
        self._start(metainterp_sd, portal_runner_ptr)
        leave_code = None
        if leave_graph:
            leave_code = self.make_one_bytecode((leave_graph, None), False)
        portal_code = self.make_portal_bytecode(portal_graph)

        self.metainterp_sd.info_from_codewriter(portal_code, leave_code,
                                                self.class_sizes,
                                                self.list_of_addr2name,
                                                portal_runner_ptr)

    def _start(self, metainterp_sd, portal_runner_ptr):
        self.metainterp_sd = metainterp_sd
        self.cpu = metainterp_sd.cpu
        self.portal_runner_ptr = portal_runner_ptr
        translator = self.rtyper.annotator.translator
        self.raise_analyzer = RaiseAnalyzer(translator)
        self.readwrite_analyzer = ReadWriteAnalyzer(translator)
        self.virtualizable_analyzer = VirtualizableAnalyzer(translator)

    def make_portal_bytecode(self, graph):
        log.info("making JitCodes...")
        self.portal_graph = graph
        graph_key = (graph, None)
        jitcode = self.make_one_bytecode(graph_key, True)
        self.finish_making_bytecodes()
        log.info("there are %d JitCode instances." % len(self.all_graphs))
        self.annotation_hacks(jitcode)
        return jitcode

    def finish_making_bytecodes(self):
        while self.unfinished_graphs:
            graph_key, called_from = self.unfinished_graphs.pop()
            self.make_one_bytecode(graph_key, False, called_from)

    def annotation_hacks(self, jitcode):
        if not self.class_sizes:
            if self.rtyper.type_system.name == 'lltypesystem':
                STRUCT = lltype.GcStruct('empty')
                vtable = lltype.malloc(rclass.OBJECT_VTABLE, immortal=True)
                self.register_known_gctype(vtable, STRUCT)
            else:
                TYPE = ootype.Instance('empty', ootype.ROOT)
                cls = ootype.runtimeClass(TYPE)
                self.register_known_ooclass(cls, TYPE)

    def make_one_bytecode(self, graph_key, portal, called_from=None):
        maker = BytecodeMaker(self, graph_key, portal)
        if not hasattr(maker.bytecode, 'code'):
            maker.assemble()
            self.counter += 1
            if not self.counter % 500:
                log.info("Produced %d jitcodes" % self.counter)
        return maker.bytecode

    def get_jitcode(self, graph, called_from=None, oosend_methdescr=None):
        key = (graph, oosend_methdescr)
        if key in self.all_graphs:
            return self.all_graphs[key]
        extra = self.get_jitcode_calldescr(graph, oosend_methdescr)
        bytecode = JitCode(graph.name, *extra, **dict(called_from=called_from,
                                                      graph=graph))
        # 'graph.name' is for dump()
        self.all_graphs[key] = bytecode
        self.unfinished_graphs.append((key, called_from))
        return bytecode

    def get_jitcode_calldescr(self, graph, oosend_methdescr):
        if self.portal_graph is None:
            return ()
        if graph is self.portal_graph:
            fnptr = self.metainterp_sd.warmrunnerdesc.portal_ptr
            FUNC = self.metainterp_sd.warmrunnerdesc.PORTAL_FUNCTYPE
        else:
            fnptr = self.rtyper.getcallable(graph)
            FUNC = get_functype(lltype.typeOf(fnptr))
        if self.rtyper.type_system.name == 'ootypesystem':
            if oosend_methdescr:
                return (None, oosend_methdescr)
            else:
                cfnptr = history.ConstObj(ootype.cast_to_object(fnptr))
        else:
            assert not oosend_methdescr
            cfnptr = history.ConstAddr(llmemory.cast_ptr_to_adr(fnptr),
                                       self.cpu)
        # <hack>
        # these functions come from somewhere and are never called. make sure
        # we never store a pointer to them since they make C explode,
        # need to find out where they come from
        for ARG in FUNC.ARGS:
            if isinstance(ARG, lltype.Ptr) and ARG.TO == lltype.PyObject:
                return ()
        if (isinstance(FUNC.RESULT, lltype.Ptr) and
            FUNC.RESULT.TO == lltype.PyObject):
            return ()
        # </hack>
        NON_VOID_ARGS = [ARG for ARG in FUNC.ARGS if ARG is not lltype.Void]
        calldescr = self.cpu.calldescrof(FUNC, tuple(NON_VOID_ARGS), FUNC.RESULT)
        return (cfnptr, calldescr)

    def register_indirect_call_targets(self, op):
        targets = self.graphs_from(op)
        assert targets is not None
        for graph in targets:
            if graph in self.all_indirect_call_targets:
                continue
            self.all_indirect_call_targets[graph] = True
            fnptr = self.rtyper.getcallable(graph)
            fnaddress = self.cpu.ts.cast_fnptr_to_root(fnptr)
            jitcode = self.get_jitcode(graph)
            self.metainterp_sd._register_indirect_call_target(fnaddress,
                                                              jitcode)

    def get_methdescr(self, SELFTYPE, methname, attach_jitcodes):
        # use the type where the method is actually defined as a key. This way
        # we can reuse the same desc also for subclasses
        SELFTYPE, _ = SELFTYPE._lookup(methname)
        key = (SELFTYPE, methname)
        try:
            result = self.all_methdescrs[key]
        except KeyError:
            result = self.cpu.methdescrof(SELFTYPE, methname)
            self.all_methdescrs[key] = result
        if attach_jitcodes and result.jitcodes is None:
            self.compute_jitcodes_for_methdescr(result, SELFTYPE, methname)
        return result

    def compute_jitcodes_for_methdescr(self, methdescr, INSTANCE, methname):
        jitcodes = {}
        assert isinstance(INSTANCE, ootype.Instance)
        TYPES = INSTANCE._all_subclasses()
        for T in TYPES:
            _, meth = T._lookup(methname)
            if not getattr(meth, 'abstract', False):
                assert meth.graph
                if self.is_candidate(meth.graph):
                    jitcode = self.get_jitcode(meth.graph,
                                               oosend_methdescr=methdescr)
                else:
                    jitcode = None
                oocls = ootype.runtimeClass(T)
                jitcodes[oocls] = jitcode
        methdescr.setup(jitcodes)

    def getcalldescr(self, v_func, args, result, consider_effects_of=None):
        if isinstance(v_func, Constant):
            self.register_known_function(v_func.value)
        non_void_args = [x for x in args if x.concretetype is not lltype.Void]
        NON_VOID_ARGS = [x.concretetype for x in non_void_args]
        RESULT = result.concretetype
        # check the number and type of arguments
        FUNC = get_functype(v_func.concretetype)
        ARGS = FUNC.ARGS
        assert NON_VOID_ARGS == [T for T in ARGS if T is not lltype.Void]
        assert RESULT == FUNC.RESULT
        # ok
        if consider_effects_of is not None:
            effectinfo = effectinfo_from_writeanalyze(
                    self.readwrite_analyzer.analyze(consider_effects_of),
                    self.cpu,
                    self.virtualizable_analyzer.analyze(consider_effects_of))
            calldescr = self.cpu.calldescrof(FUNC, tuple(NON_VOID_ARGS), RESULT, effectinfo)
        else:
            calldescr = self.cpu.calldescrof(FUNC, tuple(NON_VOID_ARGS), RESULT)
        return calldescr, non_void_args

    def register_known_gctype(self, vtable, STRUCT):
        # lltype only
        key = vtable._as_obj()
        if key not in self._class_sizes_seen:
            self._class_sizes_seen[key] = True
            sizedescr = self.cpu.sizeof(STRUCT)
            self.class_sizes.append((vtable, sizedescr))
            vtable_addr = llmemory.cast_ptr_to_adr(vtable)
            self.list_of_addr2name.append((vtable_addr, STRUCT.__name__))

    def register_known_ooclass(self, cls, CLASS):
        # ootype only
        if cls not in self._class_sizes_seen:
            self._class_sizes_seen[cls] = True
            typedescr = self.cpu.typedescrof(CLASS)
            self.class_sizes.append((cls, typedescr))

    def register_known_function(self, func):
        if self.rtyper.type_system.name == 'lltypesystem':
            try:
                obj = func._obj
            except lltype.DelayedPointer:   # probably ll_portal_runner
                return
            if obj not in self._functions_addr_seen:
                self._functions_addr_seen[obj] = True
                func_addr = llmemory.cast_ptr_to_adr(func)
                self.list_of_addr2name.append((func_addr, obj._name))


class BytecodeMaker(object):
    debug = False
    
    def __init__(self, codewriter, graph_key, portal):
        self.codewriter = codewriter
        self.cpu = codewriter.metainterp_sd.cpu
        self.portal = portal
        self.block_start_order = {}
        graph, oosend_methdescr = graph_key
        self.bytecode = self.codewriter.get_jitcode(graph,
                                             oosend_methdescr=oosend_methdescr)
        assert codewriter.is_candidate(graph)
        self.graph = graph

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
            exc_handler = self.pending_exception_handlers.pop()
            self.make_exception_handler(exc_handler)

        labelpos = {}
        code = assemble(labelpos, self.codewriter.metainterp_sd,
                        self.assembler)
        self.resolve_switch_targets(labelpos)
        self.bytecode.setup(code, self.constants)

        self.bytecode._source = self.assembler
        self.bytecode._metainterp_sd = self.codewriter.metainterp_sd
        self.bytecode._labelpos = labelpos
        if self.debug:
            self.bytecode.dump()
        else:
            log.dot()
            dir = udir.ensure("jitcodes", dir=1)
            if self.portal:
                name = "portal_runner"
            else:
                name = self.bytecode.name
            f = dir.join(name).open("w")
            self.bytecode.dump(f)
            f.close()

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
                assert self.force_block_args_order(block) == block.inputargs
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
        self.vable_array_vars = {}
        self.immutable_arrays = {}
        self.vable_flags = {}
        for arg in self.force_block_args_order(block):
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
            self.emit(*self.insert_renaming(link))
            self.make_bytecode_block(link.target)
        elif (len(block.exits) == 2
              and block.exitswitch.concretetype == lltype.Bool):
            linkfalse, linktrue = block.exits
            if linkfalse.llexitcase == True:
                linkfalse, linktrue = linktrue, linkfalse
            vpos = self.var_position(block.exitswitch)
            #
            # constant-fold an exitswitch
            cv = self.get_constant_value(vpos)
            if cv is not None:
                if cv.value:
                    link = linktrue
                else:
                    link = linkfalse
                self.emit(*self.insert_renaming(link))
                self.make_bytecode_block(link.target)
                return
            #
            self.emit("goto_if_not",
                      tlabel(linkfalse),
                      vpos)
            self.minimize_variables(argument_only=True, exitswitch=False)
            truerenaming = self.insert_renaming(linktrue)
            falserenaming = self.insert_renaming(linkfalse)
            # true path:
            self.emit(*truerenaming)
            self.make_bytecode_block(linktrue.target)
            # false path:
            self.emit(label(linkfalse))
            self.emit(*falserenaming)
            self.make_bytecode_block(linkfalse.target)
        else:
            self.minimize_variables()
            switches = [link for link in block.exits
                        if link.exitcase != 'default']
            if len(switches) >= 6 and isinstance(block.exitswitch.concretetype,
                                                 lltype.Primitive):
                switchdict = SwitchDict()
                switchdict._maps = {}
                for link in switches:
                    key = lltype.cast_primitive(lltype.Signed, link.llexitcase)
                    switchdict._maps[key] = link
                self.emit("switch_dict",
                          self.var_position(block.exitswitch),
                          self.get_position(switchdict))
            else:
                self.emit("switch",
                          self.var_position(block.exitswitch))
                self.emit_list([self.const_position(link.llexitcase)
                                for link in switches])
                self.emit_list([tlabel(link) for link in switches])
            renamings = [self.insert_renaming(link)
                         for link in switches]
            if block.exits[-1].exitcase == 'default':
                link = block.exits[-1]
                self.emit(*self.insert_renaming(link))
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
        for i, link in enumerate(exception_exits):
            args = self.force_link_args_order(link)
            args_without_last_exc = [v for v in args
                                       if (v is not link.last_exception and
                                           v is not link.last_exc_value)]
            if (link.exitcase is Exception and
                not args_without_last_exc and link.target.operations == () and
                len(link.target.inputargs) == 2):
                # stop at the catch-and-reraise-every-exception branch, if any
                exception_exits = exception_exits[:i]
                break
            list = self.get_renaming_list(args_without_last_exc)
            renamings.append(self.make_new_vars(list))
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

    def get_renaming_list(self, args):
        args = [v for v in args if v.concretetype is not lltype.Void]
        return [self.var_position(v) for v in args]

    def make_new_vars(self, list):
        if len(list) >= MAX_MAKE_NEW_VARS:
            return ["make_new_vars", len(list)] + list
        else:
            return ["make_new_vars_%d" % len(list)] + list

    def force_block_args_order(self, block):
        non_void = [v for v in block.inputargs
                      if v.concretetype is not lltype.Void]
        if block not in self.block_start_order:
            self.block_start_order[block] = range(len(non_void))
        return [non_void[i] for i in self.block_start_order[block]]

    def force_link_args_order(self, link):
        self.force_block_args_order(link.target)
        non_void = [v for v in link.args
                      if v.concretetype is not lltype.Void]
        return [non_void[i] for i in self.block_start_order[link.target]]

    def insert_renaming(self, link):
        shortcut = False
        list = self.get_renaming_list(link.args)
        if link.target not in self.block_start_order:
            if (sorted(list) == range(0, self.free_vars*2, 2)
                and link.target.operations != ()):
                nlist = [None] * len(list)
                for index, n in enumerate(list):
                    nlist[n/2] = index
                self.block_start_order[link.target] = nlist
                shortcut = True
            else:
                self.force_block_args_order(link.target)
        list = [list[i] for i in self.block_start_order[link.target]]
        if list == range(0, self.free_vars*2, 2):
            return []     # no-op
        assert not shortcut
        return self.make_new_vars(list)

    def minimize_variables(self, argument_only=False, exitswitch=True):
        if self.dont_minimize_variables:
            assert not argument_only
            return
        block, index = self.current_position
        allvars = self.vars_alive_through_op(block, index, exitswitch)
        seen = {}       # {position: unique Variable} without Voids
        unique = {}     # {Variable: unique Variable} without Voids
        for v in allvars:
            if v.concretetype is not lltype.Void:
                pos = self.var_position(v)
                seen.setdefault(pos, v)
                unique[v] = seen[pos]
        vars = seen.items()
        vars.sort()
        vars = [v1 for pos, v1 in vars]
        renaming_list = self.get_renaming_list(vars)
        if argument_only:
            # only generate the list of vars as an arg in a complex operation
            self.emit(len(renaming_list), *renaming_list)
        elif renaming_list != range(0, self.free_vars*2, 2):
            self.emit(*self.make_new_vars(renaming_list))
        self.free_vars = 0
        self.var_positions.clear()
        for v1 in vars:
            self.register_var(v1, verbose=False)
        for v, v1 in unique.items():
            self.var_positions[v] = self.var_positions[v1]

    def vars_alive_through_op(self, block, index, include_exitswitch=True):
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
        if include_exitswitch:
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
    serialize_op_cast_int_to_uint = serialize_op_same_as
    serialize_op_cast_uint_to_int = serialize_op_same_as
    serialize_op_cast_unichar_to_int = serialize_op_same_as
    serialize_op_cast_int_to_unichar = serialize_op_same_as
    serialize_op_resume_point = serialize_op_same_as
    serialize_op_oodowncast = serialize_op_same_as
    serialize_op_ooupcast = serialize_op_same_as

    _defl = default_serialize_op
    def serialize_op_char_eq(self, op): self._defl(op, 'int_eq')
    def serialize_op_char_ne(self, op): self._defl(op, 'int_ne')
    def serialize_op_char_le(self, op): self._defl(op, 'int_le')
    def serialize_op_char_lt(self, op): self._defl(op, 'int_lt')

    def serialize_op_uint_eq(self, op): self._defl(op, 'int_eq')
    def serialize_op_uint_ne(self, op): self._defl(op, 'int_ne')

    def serialize_op_uint_add(self, op): self._defl(op, 'int_add')
    def serialize_op_uint_sub(self, op): self._defl(op, 'int_sub')
    def serialize_op_uint_mul(self, op): self._defl(op, 'int_mul')
    def serialize_op_uint_and(self, op): self._defl(op, 'int_and')
    def serialize_op_uint_or (self, op): self._defl(op, 'int_or')
    def serialize_op_uint_xor(self, op): self._defl(op, 'int_xor')
    def serialize_op_uint_lshift(self, op): self._defl(op, 'int_lshift')

    def serialize_op_cast_bool_to_float(self, op):
        self.default_serialize_op(op, 'cast_int_to_float')

    serialize_op_unichar_eq = serialize_op_char_eq
    serialize_op_unichar_ne = serialize_op_char_ne

    def serialize_op_int_add_nonneg_ovf(self, op):
        self.default_serialize_op(op, 'int_add_ovf')

    def serialize_op_int_mod_zer(self, op):
        self.emit('check_zerodivisionerror', self.var_position(op.args[1]))
        self.default_serialize_op(op, 'int_mod')

    def serialize_op_int_mod_ovf(self, op):
        self.emit('check_div_overflow', self.var_position(op.args[0]),
                                        self.var_position(op.args[1]))
        self.default_serialize_op(op, 'int_mod')

    def serialize_op_int_mod_ovf_zer(self, op):
        self.emit('check_zerodivisionerror', self.var_position(op.args[1]))
        self.emit('check_div_overflow', self.var_position(op.args[0]),
                                        self.var_position(op.args[1]))
        self.default_serialize_op(op, 'int_mod')

    def serialize_op_int_floordiv_zer(self, op):
        self.emit('check_zerodivisionerror', self.var_position(op.args[1]))
        self.default_serialize_op(op, 'int_floordiv')

    def serialize_op_int_floordiv_ovf(self, op):
        self.emit('check_div_overflow', self.var_position(op.args[0]),
                                        self.var_position(op.args[1]))
        self.default_serialize_op(op, 'int_floordiv')

    def serialize_op_int_floordiv_ovf_zer(self, op):
        self.emit('check_zerodivisionerror', self.var_position(op.args[1]))
        self.emit('check_div_overflow', self.var_position(op.args[0]),
                                        self.var_position(op.args[1]))
        self.default_serialize_op(op, 'int_floordiv')

    def serialize_op_int_lshift_ovf(self, op):
        self.default_serialize_op(op, 'int_lshift')
        saved_free_vars = self.free_vars
        renaming_list = range(0, saved_free_vars*2, 2)
        #
        v_tmp1 = Variable()
        v_tmp1.concretetype = lltype.Signed
        self.emit('int_rshift', self.var_position(op.result),
                                self.var_position(op.args[1]))
        self.register_var(v_tmp1)
        #
        v_tmp2 = Variable()
        v_tmp2.concretetype = lltype.Bool
        self.emit('int_ne', self.var_position(v_tmp1),
                            self.var_position(op.args[0]))
        self.register_var(v_tmp2)
        #
        common_case = object()
        self.emit("goto_if_not",
                  tlabel(common_case),
                  self.var_position(v_tmp2),
                  len(renaming_list), *renaming_list)
        #
        self.emit("overflow_error")
        #
        self.emit(label(common_case))
        self.free_vars = saved_free_vars

    def serialize_op_int_neg_ovf(self, op):
        self.emit('int_sub_ovf', self.var_position(Constant(0)),
                                 self.var_position(op.args[0]))
        self.register_var(op.result)

    def serialize_op_hint(self, op):
        hints = op.args[1].value
        if hints.get('promote') and op.args[0].concretetype is not lltype.Void:
            self.minimize_variables()
            from pypy.rpython.lltypesystem.rstr import STR
            assert op.args[0].concretetype != lltype.Ptr(STR)
            self.emit('guard_value', self.var_position(op.args[0]))
            self.register_var(op.result)
        else:
            log.WARNING('ignoring hint %r at %r' % (hints, self.graph))
            self.serialize_op_same_as(op)

    def serialize_op_int_is_true(self, op):
        vpos = self.var_position(op.args[0])
        cv = self.get_constant_value(vpos)
        if cv is not None:
            if cv.value is objectmodel.malloc_zero_filled:
                # always True for now
                warmrunnerdesc = self.codewriter.metainterp_sd.warmrunnerdesc
                if warmrunnerdesc is not None:
                    assert warmrunnerdesc.gcdescr.malloc_zero_filled
                self.var_positions[op.result] = self.var_position(Constant(1))
                return
            if cv.value is _we_are_jitted:
                # always True
                self.var_positions[op.result] = self.var_position(Constant(1))
                return
        self.emit('int_is_true', vpos)
        self.register_var(op.result)

    serialize_op_uint_is_true = serialize_op_int_is_true

    def _serialize_op_ptr_eq(self, op, opname):
        arg0, arg1 = op.args
        if isinstance(arg0, Constant) and not arg0.value:
            self.emit(opname, self.var_position(arg1))
            self.register_var(op.result)
        elif isinstance(arg1, Constant) and not arg1.value:
            self.emit(opname, self.var_position(arg0))
            self.register_var(op.result)
        else:
            self.default_serialize_op(op)

    def serialize_op_ptr_eq(self, op):
        self._serialize_op_ptr_eq(op, 'ooisnull')
    serialize_op_oois = serialize_op_ptr_eq

    def serialize_op_ptr_ne(self, op):
        self._serialize_op_ptr_eq(op, 'oononnull')
    serialize_op_ooisnot = serialize_op_ptr_ne

    def serialize_op_ptr_iszero(self, op):
        self.default_serialize_op(op, 'ooisnull')

    def serialize_op_ptr_nonzero(self, op):
        self.default_serialize_op(op, 'oononnull')

    def serialize_op_malloc(self, op):
        assert op.args[1].value == {'flavor': 'gc'}
        STRUCT = op.args[0].value
        vtable = heaptracker.get_vtable_for_gcstruct(self.cpu, STRUCT)
        if vtable:
            # do we have a __del__?
            try:
                rtti = lltype.getRuntimeTypeInfo(STRUCT)
            except ValueError:
                pass
            else:
                if hasattr(rtti._obj, 'destructor_funcptr'):
                    c_vtable = Constant(vtable, lltype.typeOf(vtable))
                    self._do_builtin_call(op, 'alloc_with_del', [c_vtable])
                    return
            # store the vtable as an address -- that's fine, because the
            # GC doesn't need to follow them
            self.emit('new_with_vtable',
                      self.const_position(vtable))
            self.codewriter.register_known_gctype(vtable, STRUCT)
        else:
            self.emit('new', self.get_position(self.cpu.sizeof(STRUCT)))
        self.register_var(op.result)

    def serialize_op_malloc_varsize(self, op):
        assert op.args[1].value == {'flavor': 'gc'}
        if op.args[0].value == rstr.STR:
            self.emit('newstr', self.var_position(op.args[2]))
        elif op.args[0].value == rstr.UNICODE:
            self.emit('newunicode', self.var_position(op.args[2]))
        else:
            # XXX only strings or simple arrays for now
            ARRAY = op.args[0].value
            arraydescr = self.cpu.arraydescrof(ARRAY)
            self.emit('new_array')
            self.emit(self.get_position(arraydescr))
            self.emit(self.var_position(op.args[2]))
        self.register_var(op.result)

    def serialize_op_new(self, op):
        TYPE = op.args[0].value
        cls = ootype.runtimeClass(TYPE)
        # XXX detect finalizers
        self.emit('new_with_vtable',
                  self.const_position(cls))
        self.codewriter.register_known_ooclass(cls, TYPE)
        self.register_var(op.result)
        # initialize fields with a non-default value: while in ootype it's
        # new() that takes care of it, for the jit we explicitly insert the
        # corresponding setfields(). This way, the backends don't need to care
        # about default fields and moreover the resulting code is more similar
        # to the lltype version, so the optimizer doesn't need to take special
        # care for them.
        if isinstance(TYPE, ootype.Instance):
            fields = TYPE._get_fields_with_default()
            var_inst = self.var_position(op.result)
            for name, (T, value) in fields:
                if T != ootype.Void:
                    descr = self.cpu.fielddescrof(TYPE, name)
                    self.emit('setfield_gc')
                    self.emit(var_inst)
                    self.emit(self.get_position(descr))
                    self.emit(self.var_position(Constant(value)))

    def serialize_op_oonewarray(self, op):
        ARRAY = op.args[0].value
        arraydescr = self.cpu.arraydescrof(ARRAY)
        self.emit('new_array')
        self.emit(self.get_position(arraydescr))
        self.emit(self.var_position(op.args[1]))
        self.register_var(op.result)

    def serialize_op_oonewcustomdict(self, op):
        assert False, 'should not be seen by the jit'

    def serialize_op_instanceof(self, op):
        v, c_TYPE = op.args
        TYPE = c_TYPE.value
        typedescr = self.cpu.typedescrof(TYPE)
        self.emit('instanceof')
        self.emit(self.var_position(v))
        self.emit(self.get_position(typedescr))
        self.register_var(op.result)

    def serialize_op_zero_gc_pointers_inside(self, op):
        # XXX this is always a no-op for now
        XXX     # not actually called?
        warmrunnerdesc = self.codewriter.metainterp_sd.warmrunnerdesc
        if warmrunnerdesc is not None:
            assert warmrunnerdesc.gcdescr.malloc_zero_filled

    def serialize_op_getfield(self, op):
        if self.is_typeptr_getset(op):
            self.handle_getfield_typeptr(op)
            return
        # turn the flow graph 'getfield' operation into our own version
        [v_inst, c_fieldname] = op.args
        RESULT = op.result.concretetype
        if RESULT is lltype.Void:
            return
        # check for virtualizable
        try:
            if self.is_virtualizable_getset(op):
                vinfo = self.codewriter.metainterp_sd.virtualizable_info
                index = vinfo.static_field_to_extra_box[op.args[1].value]
                self.emit('getfield_vable',
                          self.var_position(v_inst),
                          index)
                self.register_var(op.result)
                return
        except VirtualizableArrayField:
            # xxx hack hack hack
            vinfo = self.codewriter.metainterp_sd.virtualizable_info
            arrayindex = vinfo.array_field_counter[op.args[1].value]
            self.vable_array_vars[op.result] = (op.args[0], arrayindex)
            return
        # check for deepfrozen structures that force constant-folding
        hints = deref(v_inst.concretetype)._hints
        accessor = hints.get("immutable_fields")
        if accessor and c_fieldname.value in accessor.fields:
            pure = '_pure'
            if accessor.fields[c_fieldname.value] == "[*]":
                self.immutable_arrays[op.result] = True
        elif hints.get('immutable'):
            pure = '_pure'
        else:
            pure = ''
        argname = getattr(deref(v_inst.concretetype), '_gckind', 'gc')
        self.emit('getfield_%s%s' % (argname, pure))
        self.emit(self.var_position(v_inst))
        descr = self.cpu.fielddescrof(deref(v_inst.concretetype),
                                       c_fieldname.value)
        self.emit(self.get_position(descr))
        self.register_var(op.result)
        #self._eventualy_builtin(op.result)

    serialize_op_oogetfield = serialize_op_getfield

    def serialize_op_setfield(self, op):
        if self.is_typeptr_getset(op):
            # ignore the operation completely -- instead, it's done by 'new'
            return
        # turn the flow graph 'setfield' operation into our own version
        [v_inst, c_fieldname, v_value] = op.args
        RESULT = v_value.concretetype
        if RESULT is lltype.Void:
            return
        # check for virtualizable
        if self.is_virtualizable_getset(op):
            vinfo = self.codewriter.metainterp_sd.virtualizable_info
            index = vinfo.static_field_to_extra_box[op.args[1].value]
            self.emit('setfield_vable',
                      self.var_position(v_inst),
                      index,
                      self.var_position(v_value))
            return
        argname = getattr(deref(v_inst.concretetype), '_gckind', 'gc')
        self.emit('setfield_%s' % (argname,))
        self.emit(self.var_position(v_inst))
        descr = self.cpu.fielddescrof(deref(v_inst.concretetype),
                                       c_fieldname.value)
        self.emit(self.get_position(descr))
        self.emit(self.var_position(v_value))

    serialize_op_oosetfield = serialize_op_setfield

    def is_typeptr_getset(self, op):
        return (op.args[1].value == 'typeptr' and
                deref(op.args[0].concretetype)._hints.get('typeptr'))

    def is_virtualizable_getset(self, op):
        # every access of an object of exactly the type VTYPEPTR is
        # likely to be a virtualizable access, but we still have to
        # check it in pyjitpl.py.
        vinfo = self.codewriter.metainterp_sd.virtualizable_info
        if vinfo is None:
            return False
        if not vinfo.is_vtypeptr(op.args[0].concretetype):
            return False
        res = False
        if op.args[1].value in vinfo.static_field_to_extra_box:
            res = True
        if op.args[1].value in vinfo.array_fields:
            res = VirtualizableArrayField(self.graph)

        if res:
            flags = self.vable_flags[op.args[0]]
            if 'fresh_virtualizable' in flags:
                return False
        if isinstance(res, Exception):
            raise res
        return res

    def handle_getfield_typeptr(self, op):
        # special-casing for getting the typeptr of an object
        self.minimize_variables()
        self.emit('guard_class', self.var_position(op.args[0]))
        self.register_var(op.result)

    def serialize_op_classof(self, op):
        self.handle_getfield_typeptr(op)

    def serialize_op_getarrayitem(self, op):
        ARRAY = op.args[0].concretetype.TO
        assert ARRAY._gckind == 'gc'
        if self._array_of_voids(ARRAY):
            return
        if op.args[0] in self.vable_array_vars:     # for virtualizables
            (v_base, arrayindex) = self.vable_array_vars[op.args[0]]
            self.emit('getarrayitem_vable',
                      self.var_position(v_base),
                      arrayindex,
                      self.var_position(op.args[1]))
            self.register_var(op.result)
            return
        # normal case follows
        arraydescr = self.cpu.arraydescrof(ARRAY)
        self.emit('getarrayitem_gc')
        self.emit(self.var_position(op.args[0]))
        self.emit(self.get_position(arraydescr))
        self.emit(self.var_position(op.args[1]))
        self.register_var(op.result)

    def serialize_op_setarrayitem(self, op):
        ARRAY = op.args[0].concretetype.TO
        assert ARRAY._gckind == 'gc'
        if self._array_of_voids(ARRAY):
            return
        if op.args[0] in self.vable_array_vars:     # for virtualizables
            (v_base, arrayindex) = self.vable_array_vars[op.args[0]]
            self.emit('setarrayitem_vable',
                      self.var_position(v_base),
                      arrayindex,
                      self.var_position(op.args[1]),
                      self.var_position(op.args[2]))
            return
        arraydescr = self.cpu.arraydescrof(ARRAY)
        self.emit('setarrayitem_gc')
        self.emit(self.var_position(op.args[0]))
        self.emit(self.get_position(arraydescr))
        self.emit(self.var_position(op.args[1]))
        self.emit(self.var_position(op.args[2]))

    def serialize_op_getarraysize(self, op):
        ARRAY = op.args[0].concretetype.TO
        assert ARRAY._gckind == 'gc'
        if op.args[0] in self.vable_array_vars:     # for virtualizables
            (v_base, arrayindex) = self.vable_array_vars[op.args[0]]
            self.emit('arraylen_vable',
                      self.var_position(v_base),
                      arrayindex)
            self.register_var(op.result)
            return
        # normal case follows
        arraydescr = self.cpu.arraydescrof(ARRAY)
        self.emit('arraylen_gc')
        self.emit(self.var_position(op.args[0]))
        self.emit(self.get_position(arraydescr))
        self.register_var(op.result)

    def serialize_op_getinteriorarraysize(self, op):
        # XXX only supports strings and unicodes for now
        assert len(op.args) == 2
        assert op.args[1].value == 'chars'
        optype = op.args[0].concretetype
        if optype == lltype.Ptr(rstr.STR):
            opname = "strlen"
        else:
            assert optype == lltype.Ptr(rstr.UNICODE)
            opname = "unicodelen"
        self.emit(opname, self.var_position(op.args[0]))
        self.register_var(op.result)

    def serialize_op_getinteriorfield(self, op):
        # XXX only supports strings and unicodes for now
        assert len(op.args) == 3
        assert op.args[1].value == 'chars'
        optype = op.args[0].concretetype
        if optype == lltype.Ptr(rstr.STR):
            opname = "strgetitem"
        else:
            assert optype == lltype.Ptr(rstr.UNICODE)
            opname = "unicodegetitem"
        self.emit(opname, self.var_position(op.args[0]),
                  self.var_position(op.args[2]))
        self.register_var(op.result)

    def serialize_op_setinteriorfield(self, op):
        # XXX only supports strings and unicodes for now
        assert len(op.args) == 4
        assert op.args[1].value == 'chars'
        optype = op.args[0].concretetype
        if optype == lltype.Ptr(rstr.STR):
            opname = "strsetitem"
        else:
            assert optype == lltype.Ptr(rstr.UNICODE)
            opname = "unicodesetitem"
        self.emit(opname, self.var_position(op.args[0]),
                  self.var_position(op.args[2]),
                  self.var_position(op.args[3]))

    def serialize_op_jit_marker(self, op):
        jitdriver = op.args[1].value
        if self.codewriter.jitdriver is None:
            self.codewriter.jitdriver = jitdriver
        assert jitdriver is self.codewriter.jitdriver
        key = op.args[0].value
        getattr(self, 'handle_jit_marker__%s' % key)(op)

    def promote_greens(self, args):
        self.minimize_variables()
        num_green_args = len(self.codewriter.jitdriver.greens)
        for i in range(num_green_args):
            pos = self.var_position(args[i])
            if (pos % 2) == 0:
                self.emit('guard_green', pos//2)

    def handle_jit_marker__jit_merge_point(self, op):
        assert self.portal, "jit_merge_point in non-main graph!"
        self.promote_greens(op.args[2:])
        self.emit('jit_merge_point')
        assert ([self.var_position(i) for i in op.args[2:]] ==
                range(0, 2*(len(op.args) - 2), 2))

    def handle_jit_marker__can_enter_jit(self, op):
        self.promote_greens(op.args[2:])
        self.emit('can_enter_jit')

    def serialize_op_direct_call(self, op):
        kind = self.codewriter.guess_call_kind(op)
        return getattr(self, 'handle_%s_call' % kind)(op)

    def serialize_op_indirect_call(self, op):
        kind = self.codewriter.guess_call_kind(op)
        return getattr(self, 'handle_%s_indirect_call' % kind)(op)

    def serialize_op_oosend(self, op):
        kind = self.codewriter.guess_call_kind(op)
        return getattr(self, 'handle_%s_oosend' % kind)(op)

    def handle_regular_call(self, op, oosend_methdescr=None):
        self.minimize_variables()
        [targetgraph] = self.codewriter.graphs_from(op)
        jitbox = self.codewriter.get_jitcode(targetgraph, self.graph,
                                             oosend_methdescr=oosend_methdescr)
        if oosend_methdescr:
            args = op.args
        else:
            args = op.args[1:]
        self.emit('call')
        self.emit(self.get_position(jitbox))
        self.emit_varargs([x for x in args
                           if x.concretetype is not lltype.Void])
        self.register_var(op.result)

    def handle_residual_call(self, op, skip_last=False):
        self.minimize_variables()
        if skip_last:
            args = op.args[1:-1]
        else:
            args = op.args[1:]
        calldescr, non_void_args = self.codewriter.getcalldescr(
            op.args[0], args, op.result, consider_effects_of=op)
        pure = False
        loopinvariant = False
        if op.opname == "direct_call":
            func = getattr(get_funcobj(op.args[0].value), '_callable', None)
            pure = getattr(func, "_pure_function_", False)
            loopinvariant = getattr(func, "_jit_loop_invariant_", False)
            if pure or loopinvariant:
                effectinfo = calldescr.get_extra_info()
                assert (effectinfo is not None and
                        not effectinfo.forces_virtual_or_virtualizable)
        try:
            canraise = self.codewriter.raise_analyzer.can_raise(op)
        except lltype.DelayedPointer:
            canraise = True  # if we need to look into the delayed ptr that is
                             # the portal, then it's certainly going to raise
        if loopinvariant:
            self.emit("residual_call_loopinvariant")
            assert not non_void_args, "arguments not supported for loop-invariant function!"
        elif pure:
            # XXX check what to do about exceptions (also MemoryError?)
            self.emit('residual_call_pure')
        elif canraise:
            self.emit('residual_call')
        else:
            self.emit('residual_call_noexception')
        self.emit(self.get_position(calldescr))
        self.emit_varargs([op.args[0]] + non_void_args)
        self.register_var(op.result)

    def handle_recursive_call(self, op):
        self.promote_greens(op.args[1:])
        self.minimize_variables()
        args = op.args[1:]
        calldescr, non_void_args = self.codewriter.getcalldescr(op.args[0],
                                                                args,
                                                                op.result)
        self.emit('recursion_leave_prep')
        self.emit_varargs(non_void_args)        
        self.emit('recursive_call')
        self.emit(self.get_position(calldescr))
        self.emit_varargs([op.args[0]] + non_void_args)
        self.register_var(op.result)

    handle_residual_indirect_call = handle_residual_call

    def handle_regular_indirect_call(self, op):
        self.codewriter.register_indirect_call_targets(op)
        args = op.args[1:-1]
        calldescr, non_void_args = self.codewriter.getcalldescr(
            op.args[0], args, op.result, consider_effects_of=op)
        self.minimize_variables()
        self.emit('indirect_call')
        self.emit(self.get_position(calldescr))
        self.emit(self.var_position(op.args[0]))
        self.emit_varargs(non_void_args)
        self.register_var(op.result)

    def handle_regular_oosend(self, op):
        self.minimize_variables()
        methname = op.args[0].value
        v_obj = op.args[1]
        INSTANCE = v_obj.concretetype
        methdescr = self.codewriter.get_methdescr(INSTANCE, methname, True)
        graphs = v_obj.concretetype._lookup_graphs(methname)
        if len(graphs) == 1:
            self.handle_regular_call(op, oosend_methdescr=methdescr)
            return
        self.minimize_variables()
        self.emit('oosend')
        self.emit(self.get_position(methdescr))
        self.emit_varargs([x for x in op.args
                             if x.concretetype is not lltype.Void])
        self.register_var(op.result)

    def handle_builtin_call(self, op):
        oopspec_name, args = support.decode_builtin_call(op)
        return self._do_builtin_call(op, oopspec_name, args)

    def _do_builtin_call(self, op, oopspec_name, args):
        if oopspec_name.startswith('virtual_ref'):
            self.handle_virtual_ref_call(op, oopspec_name, args)
            return
        argtypes = [v.concretetype for v in args]
        resulttype = op.result.concretetype
        c_func, TP = support.builtin_func_for_spec(self.codewriter.rtyper,
                                                   oopspec_name, argtypes,
                                                   resulttype)
        if self.codewriter.metainterp_sd.options.listops:
            if self.handle_list_call(op, oopspec_name, args, TP):
                return
        if oopspec_name.endswith('_foldable'):
            opname = 'residual_call_pure'   # should not raise, either
        else:
            opname = 'residual_call'

        calldescr, non_void_args = self.codewriter.getcalldescr(
            c_func, args, op.result, consider_effects_of=op)
        self.emit(opname)
        self.emit(self.get_position(calldescr))
        self.emit_varargs([c_func] + non_void_args)
        self.register_var(op.result)

    def handle_virtual_ref_call(self, op, oopspec_name, args):
        self.emit(oopspec_name)     # 'virtual_ref' or 'virtual_ref_finish'
        self.emit(self.var_position(args[0]))
        self.register_var(op.result)
        #
        vrefinfo = self.codewriter.metainterp_sd.virtualref_info
        self.codewriter.register_known_gctype(vrefinfo.jit_virtual_ref_vtable,
                                              vrefinfo.JIT_VIRTUAL_REF)

    def _array_of_voids(self, ARRAY):
        if isinstance(ARRAY, ootype.Array):
            return ARRAY.ITEM == ootype.Void
        else:
            return ARRAY.OF == lltype.Void

    def handle_resizable_list_setitem(self, op, arraydescr, itemsdescr,
                                      lengthdescr, args):
        index = self.prepare_list_getset(op, lengthdescr, args,
                                         'check_resizable_neg_index')
        if index is None:
            return False
        self.emit('setlistitem_gc')
        self.emit(self.var_position(args[0]))
        self.emit(self.get_position(itemsdescr))
        self.emit(self.get_position(arraydescr))
        self.emit(self.var_position(index))
        self.emit(self.var_position(args[2]))
        self.register_var(op.result)
        return True

    def handle_resizable_list_call(self, op, oopspec_name, args, LIST):
        assert isinstance(LIST.TO, lltype.GcStruct)
        # no ootype
        ARRAY = LIST.TO.items.TO
        if self._array_of_voids(ARRAY):
            return False # arrays of voids: not supported
        arraydescr = self.cpu.arraydescrof(ARRAY)
        lengthdescr = self.cpu.fielddescrof(LIST.TO, 'length')
        itemsdescr = self.cpu.fielddescrof(LIST.TO, 'items')
        structdescr = self.cpu.sizeof(LIST.TO)
        if oopspec_name == 'list.getitem':
            return self.handle_resizable_list_getitem(op, arraydescr,
                                             itemsdescr, lengthdescr, args)
        if oopspec_name == 'list.setitem':
            return self.handle_resizable_list_setitem(op, arraydescr,
                                             itemsdescr, lengthdescr, args)
        if oopspec_name == 'list.len':
            self.emit('getfield_gc')
            self.emit(self.var_position(args[0]))
            self.emit(self.get_position(lengthdescr))
            self.register_var(op.result)
            return True
        if oopspec_name == 'newlist':
            if len(args) < 1:
                args.append(Constant(0, lltype.Signed))
            if len(args) > 1:
                v_default = args[1]
                if (not isinstance(v_default, Constant) or
                    v_default.value != arrayItem(ARRAY)._defl()):
                    return False     # variable or non-null initial value
            self.emit('newlist')
            self.emit(self.get_position(structdescr))
            self.emit(self.get_position(lengthdescr))
            self.emit(self.get_position(itemsdescr))
            self.emit(self.get_position(arraydescr))
            self.emit(self.var_position(args[0]))
            self.register_var(op.result)
            return True
        return False

    def handle_list_call(self, op, oopspec_name, args, LIST):
        if not (oopspec_name.startswith('list.') or oopspec_name == 'newlist'):
            return False
        if not isinstance(deref(LIST), (lltype.GcArray, ootype.Array)):
            if isinstance(deref(LIST), lltype.GcStruct):
                return self.handle_resizable_list_call(op, oopspec_name, args,
                                                       LIST)
            else:
                return False # resizable lists on ootype
        ARRAY = deref(LIST)
        if self._array_of_voids(ARRAY):
            return False # arrays of voids: not supported
        arraydescr = self.cpu.arraydescrof(ARRAY)
        #
        if oopspec_name == 'newlist':
            # normalize number of arguments
            if len(args) < 1:
                args.append(Constant(0, lltype.Signed))
            if len(args) > 1:
                v_default = args[1]
                if (not isinstance(v_default, Constant) or
                    v_default.value != arrayItem(ARRAY)._defl()):
                    return False     # variable or non-null initial value
            self.emit('new_array')
            self.emit(self.get_position(arraydescr))
            self.emit(self.var_position(args[0]))
            self.register_var(op.result)
            return True
        #
        if oopspec_name == 'list.getitem':
            return self.handle_list_getitem(op, arraydescr, args,
                                            'getarrayitem_gc')
        #
        if oopspec_name == 'list.getitem_foldable':
            return self.handle_list_getitem(op, arraydescr, args,
                                            'getarrayitem_gc_pure')
        #
        if oopspec_name == 'list.setitem':
            if args[0] in self.vable_array_vars:     # virtualizable array
                (v_base, arrayindex) = self.vable_array_vars[args[0]]
                self.emit('setarrayitem_vable',
                          self.var_position(v_base),
                          arrayindex,
                          self.var_position(args[1]),
                          self.var_position(args[2]))
                return True
            index = self.prepare_list_getset(op, arraydescr, args,
                                             'check_neg_index')
            if index is None:
                return False
            self.emit('setarrayitem_gc')
            self.emit(self.var_position(args[0]))
            self.emit(self.get_position(arraydescr))
            self.emit(self.var_position(index))
            self.emit(self.var_position(args[2]))
            self.register_var(op.result)
            return True
        #
        if (oopspec_name == 'list.len' or
            oopspec_name == 'list.len_foldable'):
            if args[0] in self.vable_array_vars:     # virtualizable array
                (v_base, arrayindex) = self.vable_array_vars[args[0]]
                self.emit('arraylen_vable',
                          self.var_position(v_base),
                          arrayindex)
                self.register_var(op.result)
                return True
            self.emit('arraylen_gc')
            self.emit(self.var_position(args[0]))
            self.emit(self.get_position(arraydescr))
            self.register_var(op.result)
            return True
        #
        return False

    def handle_list_getitem(self, op, arraydescr, args, opname):
        if args[0] in self.vable_array_vars:     # virtualizable array
            (v_base, arrayindex) = self.vable_array_vars[args[0]]
            self.emit('getarrayitem_vable',
                      self.var_position(v_base),
                      arrayindex,
                      self.var_position(args[1]))
            self.register_var(op.result)
            return True
        elif args[0] in self.immutable_arrays:
            opname = "getarrayitem_gc_pure"
        index = self.prepare_list_getset(op, arraydescr, args,
                                         'check_neg_index')
        if index is None:
            return False
        self.emit(opname)
        self.emit(self.var_position(args[0]))
        self.emit(self.get_position(arraydescr))
        self.emit(self.var_position(index))
        self.register_var(op.result)
        return True

    def handle_resizable_list_getitem(self, op, arraydescr, itemsdescr,
                                      lengthdescr, args):
        index = self.prepare_list_getset(op, lengthdescr, args,
                                         'check_resizable_neg_index')
        if index is None:
            return False
        self.emit('getlistitem_gc')
        self.emit(self.var_position(args[0]))
        self.emit(self.get_position(itemsdescr))
        self.emit(self.get_position(arraydescr))
        self.emit(self.var_position(index))
        self.register_var(op.result)
        return True

    def prepare_list_getset(self, op, descr, args, checkname):
        if op.opname == 'oosend':
            SELFTYPE, _, meth = support.lookup_oosend_method(op)
            func = meth._callable
        else:
            func = get_funcobj(op.args[0].value)._callable      # xxx break of abstraction
        # base hints on the name of the ll function, which is a bit xxx-ish
        # but which is safe for now
        assert func.__name__.startswith('ll_')
        non_negative = '_nonneg' in func.__name__
        fast = '_fast' in func.__name__
        if fast:
            can_raise = False
            non_negative = True
        else:
            tag = op.args[1].value
            assert tag in (rlist.dum_nocheck, rlist.dum_checkidx)
            can_raise = tag != rlist.dum_nocheck
        #
        if can_raise:
            return None
        if non_negative:
            v_posindex = args[1]
        else:
            self.emit(checkname)
            self.emit(self.var_position(args[0]))
            self.emit(self.get_position(descr))
            self.emit(self.var_position(args[1]))
            v_posindex = Variable('posindex')
            v_posindex.concretetype = lltype.Signed
            self.register_var(v_posindex)
        return v_posindex

    def handle_builtin_oosend(self, op):
        self.minimize_variables()
        oopspec_name, args = support.decode_builtin_call(op)
        SELFTYPE, methname, meth = support.lookup_oosend_method(op)
        assert SELFTYPE.oopspec_name is not None
        # try to special-case list operations
        if self.codewriter.metainterp_sd.options.listops:
            if self.handle_list_call(op, oopspec_name, args, SELFTYPE):
                return
        # fallback to all the other builtin oosends
        if getattr(meth, '_pure_meth', False):
            kind = '_pure'
        elif getattr(meth, '_can_raise', True):
            kind = '_canraise'
        else:
            kind = '_noraise'
        methdescr = self.codewriter.get_methdescr(SELFTYPE, methname, False)
        self.emit('residual_oosend' + kind)
        self.emit(self.get_position(methdescr))
        non_void_args = [arg for arg in op.args[1:]
                         if arg.concretetype is not ootype.Void]
        self.emit_varargs(non_void_args)
        self.register_var(op.result)

    def handle_residual_oosend(self, op):
        self.minimize_variables()
        SELFTYPE, methname, meth = support.lookup_oosend_method(op)
        methdescr = self.codewriter.get_methdescr(SELFTYPE, methname, False)
        graphs = SELFTYPE._lookup_graphs(methname)
        kind = self.get_kind_of_graphs(graphs)
        self.emit('residual_oosend_%s' % kind)
        self.emit(self.get_position(methdescr))
        non_void_args = [arg for arg in op.args[1:]
                         if arg.concretetype is not ootype.Void]
        self.emit_varargs(non_void_args)
        self.register_var(op.result)

    def get_kind_of_graphs(self, graphs):
        pure = True
        for graph in graphs:
            if not hasattr(graph, 'func'):
                pure = False
            pure = pure and getattr(graph.func, '_pure_function_', False)
            
        if pure:
            return 'pure'
        else:
            return 'canraise'

    def serialize_op_debug_assert(self, op):
        log.WARNING("found debug_assert in %r; should have be removed" %
                    (self.graph,))

    def serialize_op_jit_force_virtualizable(self, op):
        vinfo = self.codewriter.metainterp_sd.virtualizable_info
        assert vinfo is not None
        assert vinfo.is_vtypeptr(op.args[0].concretetype)
        self.vable_flags[op.args[0]] = op.args[2].value

    def serialize_op_jit_force_virtual(self, op):
        self._do_builtin_call(op, 'jit_force_virtual', op.args)

    serialize_op_oostring  = handle_builtin_call
    serialize_op_oounicode = handle_builtin_call
    serialize_op_gc_identityhash = handle_builtin_call

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
            try:
                return self.var_positions[v]
            except KeyError:
                if v in self.vable_array_vars:
                    raise VirtualizableArrayField(self.graph)
                raise

    def get_constant_value(self, vpos):
        """Reverse of var_position().  Returns either None or a Constant."""
        if vpos & 1:
            value = self.constants[vpos // 2].value
            return Constant(value)
        else:
            return None

    def emit(self, *stuff):
        self.assembler.extend(stuff)

    def emit_varargs(self, varargs):
        self.emit_list(map(self.var_position, varargs))

    def emit_list(self, l):
        self.emit(len(l))
        self.emit(*l)

    def resolve_switch_targets(self, labelpos):
        for sd in self.constants:
            if isinstance(sd, SwitchDict):
                sd.dict = {}
                for key, link in sd._maps.items():
                    sd.dict[key] = labelpos[link]

    def _call_stack(self):
        p = self.bytecode
        i = 0
        while p is not None:
            print " " * i + p.graph.name
            i += 1
            if p.called_from is None:
                p = None
            else:
                p = self.codewriter.get_jitcode(p.called_from)

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
    if index < 0:
        index += 2*(sys.maxint + 1)
    result = []
    while True:
        byte = index & 0x7F
        index >>= 7
        result.append(chr(byte + 0x80 * bool(index)))
        if not index:
            break
    return result

def assemble(labelpos, metainterp_sd, assembler):
    result = []
    for arg in assembler:
        if isinstance(arg, str):
            if arg.startswith('#'):     # skip comments
                continue
            opcode = metainterp_sd.find_opcode(arg)
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

# ____________________________________________________________

class VirtualizableArrayField(Exception):
    def __str__(self):
        return "using virtualizable array in illegal way in %r" % (
            self.args[0],)
