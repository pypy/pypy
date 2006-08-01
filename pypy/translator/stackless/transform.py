from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.lltypesystem.lloperation import LL_OPERATIONS
from pypy.rpython import rarithmetic, rclass, rmodel
from pypy.translator.backendopt import support
from pypy.objspace.flow import model
from pypy.rpython.memory.gctransform import varoftype
from pypy.translator import unsimplify
from pypy.annotation import model as annmodel
from pypy.rpython.annlowlevel import MixLevelHelperAnnotator
from pypy.translator.stackless import code, frame
from pypy.rpython.rclass import getinstancerepr
from pypy.rpython.rbuiltin import gen_cast
from pypy.rpython.rtyper import LowLevelOpList
from pypy.rpython.module import ll_stackless, ll_stack
from pypy.rpython.objectmodel import ComputedIntSymbolic
from pypy.translator.backendopt import graphanalyze

from pypy.translator.stackless.frame import SAVED_REFERENCE, STORAGE_TYPES
from pypy.translator.stackless.frame import STORAGE_FIELDS
from pypy.translator.stackless.frame import STATE_HEADER, null_state
from pypy.translator.stackless.frame import storage_type

SAVE_STATISTICS = True

if SAVE_STATISTICS:
    import cStringIO
    
    class StacklessStats:
        def __init__(self):
            self.rp_count = 0
            self.rp_type_counts = {}
            self.rp_per_graph = {}
            self.rp_per_graph_type_counts = {}
            self.saveops = self.resumeops = 0
            self.pot_exact_saves = {}
            self.total_pot_exact_saves = 0
            self.pot_erased_saves = {}
            self.total_pot_erased_saves = 0
        def __repr__(self):
            s = cStringIO.StringIO()
            print >> s, self.__class__.__name__
            for k in sorted(self.__dict__.keys()):
                r = repr(self.__dict__[k])
                if len(r) > 60:
                    r = r[:50] + '...'
                print >>s, '    '+k, r
            return s.getvalue()

    def inc(d, key):
        d[key] = d.get(key, 0) + 1

    def gkey(graph):
        return (graph.name, id(graph))

# a simple example of what the stackless transform does
#
# def func(x):
#     return g() + x + 1
#
# STATE_func_0 = lltype.Struct('STATE_func_0',
#                              ('header', STATE_HEADER),
#                              ('saved_long_0', Signed))
#
# def func(x):
#     state = global_state.restart_substate
#     if state == -1:   # normal case
#         try:
#             retval = g(x)
#         except code.UnwindException, u:
#             state = lltype.malloc(STATE_func_0, flavor='gc_nocollect')
#             state.header.f_restart = <index in array of frame.FRAMEINFO>
#             state.saved_long_0 = x
#             code.add_frame_state(u, state.header)
#             raise
#     elif state == 0:
#         global_state.restart_substate = -1
#         state = lltype.cast_pointer(lltype.Ptr(STATE_func_0),
#                                     global_state.top)
#         global_state.top = null_state
#         x = state.saved_long_0
#         retval = code.fetch_retval_long() # can raise an exception
#     elif state == 1:
#         ...
#     elif state == 2:
#         ...
#     else:
#         abort()
#     return retval + x + 1

class SymbolicRestartNumber(ComputedIntSymbolic):
    def __init__(self, label, value=None):
        ComputedIntSymbolic.__init__(self, self._getvalue)
        self.label = label
        self.value = value

    def _getvalue(self):
        # argh, we'd like to assert-fail if value is None here, but we
        # get called too early (during databasing) for this to be
        # valid.  so we might return None and rely on the database
        # checking that this only happens before the database is
        # complete.
        return self.value

class FrameTyper:
    # this class only exists independently to ease testing
    def __init__(self, stackless_gc=False, transformer=None):
        self.frametypes = {}
        self.stackless_gc = stackless_gc
        self.c_gc_nocollect = model.Constant("gc_nocollect", lltype.Void)
        self.transformer = transformer
        

    def _key_for_types(self, types):
        counts = {}
        for tt in types:
            if tt is lltype.Void:
                continue
            t = storage_type(tt)
            counts[t] = counts.get(t, 0) + 1
        key = lltype.frozendict(counts)
        return key

    def saving_function_for_type(self, FRAME_TYPE):
        v_exception = varoftype(self.transformer.unwind_exception_type)
        v_restart = varoftype(lltype.Signed)
        
        save_block = model.Block([v_exception, v_restart])
        
        llops = LowLevelOpList()
        if self.stackless_gc:
            v_state = llops.genop(
                'flavored_malloc',
                [self.c_gc_nocollect, model.Constant(FRAME_TYPE, lltype.Void)],
                resulttype=lltype.Ptr(FRAME_TYPE))
        else:
            v_state = llops.genop(
                'malloc',
                [model.Constant(FRAME_TYPE, lltype.Void)],
                resulttype=lltype.Ptr(FRAME_TYPE))

        for fieldname in FRAME_TYPE._names[1:]: # skip the 'header' field
            TYPE = FRAME_TYPE._flds[fieldname]
            var = varoftype(TYPE)
            save_block.inputargs.append(var)
            llops.genop('setfield',
                        [v_state, model.Constant(fieldname, lltype.Void), var],
                        resulttype=lltype.Void)

        v_header = gen_cast(llops, lltype.Ptr(STATE_HEADER), v_state)
        llops.genop('direct_call',
                    [self.transformer.add_frame_state_ptr, v_exception, v_header],
                    resulttype=lltype.Void)
        llops.genop("setfield",
                    [v_header, self.transformer.c_f_restart_name, v_restart],
                    resulttype=lltype.Void)

        save_state_graph = model.FunctionGraph('save_' + FRAME_TYPE._name, save_block,
                                               varoftype(lltype.Void))
        save_block.operations = llops
        save_block.closeblock(model.Link([v_header], save_state_graph.returnblock))

        FUNC_TYPE = lltype.FuncType([v.concretetype for v in save_block.inputargs],
                                    lltype.Void)
        return lltype.functionptr(FUNC_TYPE, save_state_graph.name,
                                  graph=save_state_graph)
        

    def frame_type_for_vars(self, vars):
        key = self._key_for_types([v.concretetype for v in vars])
        if key not in self.frametypes:
            fields = []
            fieldsbytype = {}
            tcounts = []
            for t in STORAGE_TYPES:
                tcount = key.get(t, 0)
                tcounts.append(str(tcount))
                for j in range(tcount):
                    fname = 'state_%s_%d' % (STORAGE_FIELDS[t], j)
                    fields.append((fname, t))
                    fieldsbytype.setdefault(t, []).append(fname)
            
            FRAME_TYPE = frame.make_state_header_type(
                "FrameState_"+'_'.join(tcounts), *fields)
            self.frametypes[key] = (FRAME_TYPE,
                                    self.saving_function_for_type(FRAME_TYPE),
                                    fieldsbytype)

        T, save_state_funcptr, fieldsbytype = self.frametypes[key]
        varsforcall = list(vars)
        def key(v):
            return STORAGE_TYPES.index(storage_type(v.concretetype))
        def mycmp(x, y):
            return cmp(key(x), key(y))
        varsforcall.sort(mycmp)
        return T, varsforcall, save_state_funcptr

    def ensure_frame_type_for_types(self, frame_type):
        assert len(frame_type._names[1:]) <= 1, "too lazy"
        if len(frame_type._names[1:]) == 1:
            fname, = frame_type._names[1:]
            t = frame_type._flds[fname]
            fieldsbytype = {t:[fname]}
            key = self._key_for_types([t])
        else:
            key = self._key_for_types([])
            fieldsbytype = {}
        if key in self.frametypes:
            assert self.frametypes[key][0] is frame_type
        self.frametypes[key] = (frame_type,
                                self.saving_function_for_type(frame_type),
                                fieldsbytype)


class StacklessAnalyzer(graphanalyze.GraphAnalyzer):
    def __init__(self, translator, unwindtype, stackless_gc):
        graphanalyze.GraphAnalyzer.__init__(self, translator)
        self.unwindtype = unwindtype
        self.stackless_gc = stackless_gc

    def operation_is_true(self, op):
        if op.opname == 'yield_current_frame_to_caller':
            return True
        elif op.opname == 'resume_point':
            return True
        elif op.opname == 'resume_state_invoke':
            return True
        return self.stackless_gc and LL_OPERATIONS[op.opname].canunwindgc

    def analyze_external_call(self, op):
        callable = op.args[0].value._obj._callable
        #assert getattr(callable, 'suggested_primitive', False)
        return callable in [ll_stack.ll_stack_unwind, ll_stack.ll_stack_capture,
                            ll_stackless.ll_stackless_stack_frames_depth,
                            ll_stackless.ll_stackless_switch]

def vars_to_save(block):
    lastresult = block.operations[-1].result
    args = []
    for l in block.exits:
        for arg in l.args:
            if isinstance(arg, model.Variable) \
               and arg is not lastresult \
               and arg not in args \
               and arg not in [l.last_exception, l.last_exc_value]:
                args.append(arg)
    return args             

class StacklessTransformer(object):

    def __init__(self, translator, entrypoint,
                 stackless_gc=False, assert_unwind=False):
        self.translator = translator
        self.stackless_gc = stackless_gc

        self.frametyper = FrameTyper(stackless_gc, self)
        self.masterarray1 = []
        self.curr_graph = None
        
        bk = translator.annotator.bookkeeper

        self.unwind_exception_type = getinstancerepr(
            self.translator.rtyper,
            bk.getuniqueclassdef(code.UnwindException)).lowleveltype
        self.analyzer = StacklessAnalyzer(translator,
                                          self.unwind_exception_type,
                                          stackless_gc)

        # the point of this little dance is to not annotate
        # code.global_state.masterarray as a constant.
        data_classdef = bk.getuniqueclassdef(code.StacklessData)
        data_classdef.generalize_attr(
            'masterarray',
            annmodel.SomePtr(lltype.Ptr(frame.FRAME_INFO_ARRAY)))

        mixlevelannotator = MixLevelHelperAnnotator(translator.rtyper)
        l2a = annmodel.lltype_to_annotation

        if assert_unwind:
            def slp_entry_point(argv):
                try:
                    r = entrypoint(argv)
                except code.UnwindException, u:
                    code.slp_main_loop()
                    return code.global_state.retval_long
                else:
                    assert False, "entrypoint never unwound the stack"
                return r
            slp_entry_point.stackless_explicit = True
        else:
            def slp_entry_point(argv):
                try:
                    r = entrypoint(argv)
                except code.UnwindException, u:
                    code.slp_main_loop()
                    return code.global_state.retval_long
                return r
            slp_entry_point.stackless_explicit = True

        self.slp_entry_point = slp_entry_point
        oldgraph = bk.getdesc(entrypoint).getuniquegraph()
        s_argv = translator.annotator.binding(oldgraph.getargs()[0])
        self.slp_entry_point_ptr = mixlevelannotator.constfunc(
            slp_entry_point, [s_argv], annmodel.SomeInteger())

        unwinddef = bk.getuniqueclassdef(code.UnwindException)
        self.add_frame_state_ptr = mixlevelannotator.constfunc(
            code.add_frame_state,
            [annmodel.SomeInstance(unwinddef),
             annmodel.SomePtr(lltype.Ptr(STATE_HEADER))],
            l2a(lltype.Void))

        # order really matters on 64 bits machines on which
        # longlong==signed; so lltype.Signed must appear *after*
        # longlong in this dict
        self.fetch_retvals = {
            lltype.Void: mixlevelannotator.constfunc(
                code.fetch_retval_void, [], annmodel.s_None),
            lltype.SignedLongLong: mixlevelannotator.constfunc(
                code.fetch_retval_longlong, [], annmodel.SomeInteger(knowntype=rarithmetic.r_longlong)),
            lltype.Signed: mixlevelannotator.constfunc(
                code.fetch_retval_long, [], annmodel.SomeInteger()),
            lltype.Float: mixlevelannotator.constfunc(
                code.fetch_retval_float, [], annmodel.SomeFloat()),
            llmemory.Address: mixlevelannotator.constfunc(
                code.fetch_retval_addr, [], annmodel.SomeAddress()),
            SAVED_REFERENCE: mixlevelannotator.constfunc(
                code.fetch_retval_ref, [], annmodel.SomePtr(SAVED_REFERENCE)),
            }

        s_StatePtr = annmodel.SomePtr(frame.OPAQUE_STATE_HEADER_PTR)
        self.suggested_primitives = {
            ll_stackless.ll_stackless_stack_frames_depth:
                mixlevelannotator.constfunc(
                    code.stack_frames_depth, [], annmodel.SomeInteger()),
            ll_stackless.ll_stackless_switch:
                mixlevelannotator.constfunc(
                    code.ll_frame_switch, [s_StatePtr], s_StatePtr),
            ll_stack.ll_stack_unwind:
                mixlevelannotator.constfunc(
                    code.ll_stack_unwind, [], annmodel.s_None),
            ll_stack.ll_stack_capture:
                mixlevelannotator.constfunc(
                    code.ll_stack_capture, [], s_StatePtr),
            }

        self.yield_current_frame_to_caller_ptr = mixlevelannotator.constfunc(
            code.yield_current_frame_to_caller, [], s_StatePtr)

        s_hdrptr = annmodel.SomePtr(lltype.Ptr(STATE_HEADER))
        # order really matters on 64 bits machines on which
        # longlong==signed; so lltype.Signed must appear *after*
        # longlong in this dict
        self.resume_afters = {
            lltype.Void: mixlevelannotator.constfunc(
                code.resume_after_void,
                [s_StatePtr, annmodel.s_None],
                annmodel.s_None),
            lltype.SignedLongLong: mixlevelannotator.constfunc(
                code.resume_after_longlong,
                [s_StatePtr, annmodel.SomeInteger(knowntype=rarithmetic.r_longlong)],
                annmodel.s_None),
            lltype.Signed: mixlevelannotator.constfunc(
                code.resume_after_long,
                [s_StatePtr, annmodel.SomeInteger()],
                annmodel.s_None),
            lltype.Float: mixlevelannotator.constfunc(
                code.resume_after_float,
                [s_StatePtr, annmodel.SomeFloat()],
                annmodel.s_None),
            llmemory.Address: mixlevelannotator.constfunc(
                code.resume_after_addr,
                [s_StatePtr, annmodel.SomeAddress()],
                annmodel.s_None),
            SAVED_REFERENCE: mixlevelannotator.constfunc(
                code.resume_after_ref,
                [s_StatePtr, annmodel.SomePtr(SAVED_REFERENCE)],
                annmodel.s_None),
            }
        exception_def = bk.getuniqueclassdef(Exception)
        self.resume_after_raising_ptr = mixlevelannotator.constfunc(
            code.resume_after_raising,
            [s_StatePtr, annmodel.SomeInstance(exception_def)],
            annmodel.s_None)
        self.exception_type = getinstancerepr(
            self.translator.rtyper, exception_def).lowleveltype

        mixlevelannotator.finish()

        s_global_state = bk.immutablevalue(code.global_state)
        r_global_state = translator.rtyper.getrepr(s_global_state)
        self.ll_global_state = model.Constant(
            r_global_state.convert_const(code.global_state),
            r_global_state.lowleveltype)
        self.seen_blocks = set()

        # some prebuilt constants to save memory
        self.c_restart_substate_name = model.Constant("inst_restart_substate",
                                                      lltype.Void)
        self.c_inst_top_name = model.Constant("inst_top", lltype.Void)
        self.c_f_restart_name = model.Constant("f_restart", lltype.Void)
        self.c_minus_one = model.Constant(-1, lltype.Signed)
        self.c_null_state = model.Constant(null_state,
                                           lltype.typeOf(null_state))
        self.c_gc_nocollect = model.Constant("gc_nocollect", lltype.Void)

        self.is_finished = False

        # only for sanity checking, but still very very important
        self.explicit_resume_point_data = {}
        
        self.symbolic_restart_numbers = {}

        # register the prebuilt restartinfos & give them names for use
        # with resume_state_create
        # the mauling of frame_typer internals should be a method on FrameTyper.
        for restartinfo in frame.RestartInfo.prebuilt:
            name = restartinfo.func_or_graph.__name__
            for i in range(len(restartinfo.frame_types)):
                label = name + '_' + str(i)
                assert label not in self.symbolic_restart_numbers
                # XXX we think this is right:
                self.symbolic_restart_numbers[label] = SymbolicRestartNumber(
                    label, len(self.masterarray1) + i)
                frame_type = restartinfo.frame_types[i]
                self.explicit_resume_point_data[label] = frame_type
                self.frametyper.ensure_frame_type_for_types(frame_type)
            self.register_restart_info(restartinfo)

        if SAVE_STATISTICS:
            translator.stackless_stats = self.stats = StacklessStats()

    def transform_all(self):
        for graph in self.translator.graphs:
            self.transform_graph(graph)
        self.finish()
        
    def transform_graph(self, graph):
        self.resume_blocks = []
        
        if hasattr(graph, 'func'):
            if getattr(graph.func, 'stackless_explicit', False):
                if self.stackless_gc:
                    self.transform_gc_nocollect(graph)
                return

        if not self.analyzer.analyze_direct_call(graph):
            return
        
        assert self.curr_graph is None
        self.curr_graph = graph
        self.curr_graph_save_blocks = {}
        self.curr_graph_resume_blocks = {}
        if SAVE_STATISTICS:
            self.stats.cur_rp_exact_types = {}
            self.stats.cur_rp_erased_types = {}
            
        
        for block in list(graph.iterblocks()):
            assert block not in self.seen_blocks
            self.transform_block(block)
            self.seen_blocks.add(block)

        if self.resume_blocks:
            self.insert_resume_handling(graph)
            self.generate_restart_infos(graph)

        model.checkgraph(graph)

        if SAVE_STATISTICS:
            pot_exact_save_count = 0
            for t, count in self.stats.cur_rp_exact_types.items():
                pot_exact_save_count += count - 1
            del self.stats.cur_rp_exact_types
            self.stats.pot_exact_saves[gkey(self.curr_graph)] = pot_exact_save_count
            self.stats.total_pot_exact_saves += pot_exact_save_count
            
            pot_erased_save_count = 0
            for t, count in self.stats.cur_rp_erased_types.items():
                pot_erased_save_count += count - 1
            del self.stats.cur_rp_erased_types
            self.stats.pot_erased_saves[gkey(self.curr_graph)] = pot_erased_save_count 
            self.stats.total_pot_erased_saves += pot_erased_save_count
           
        self.curr_graph = None
        self.curr_graph_save_blocks = None
        self.curr_graph_resume_blocks = None

    def ops_read_global_state_field(self, targetvar, fieldname):
        ops = []
        llfieldname = "inst_%s" % fieldname
        llfieldtype = self.ll_global_state.value._T._flds[llfieldname]
        if llfieldtype == targetvar.concretetype: 
            tmpvar = targetvar
        else:
            assert isinstance(llfieldtype, lltype.Ptr)
            tmpvar = varoftype(llfieldtype)
   
        ops.append(model.SpaceOperation(
            "getfield",
            [self.ll_global_state,
             model.Constant(llfieldname, lltype.Void)],
            tmpvar))
        if tmpvar is not targetvar: 
            ops.append(model.SpaceOperation(
                "cast_pointer", [tmpvar],
                targetvar))
        return ops

    def insert_resume_handling(self, graph):
        old_start_block = graph.startblock
        newinputargs = [unsimplify.copyvar(self.translator.annotator, v)
                        for v in old_start_block.inputargs]
        new_start_block = model.Block(newinputargs)
        var_resume_state = varoftype(lltype.Signed)
        new_start_block.operations.append(
            model.SpaceOperation("getfield",
                                 [self.ll_global_state,
                                  self.c_restart_substate_name],
                                 var_resume_state))
        not_resuming_link = model.Link(newinputargs, old_start_block, -1)
        not_resuming_link.llexitcase = -1
        resuming_links = []
        for resume_index, resume_block in enumerate(self.resume_blocks):
            if resume_block.inputargs:
                args = [var_resume_state]
            else:
                args = []
            resuming_links.append(
                model.Link(args, resume_block, resume_index))
            resuming_links[-1].llexitcase = resume_index

        new_start_block.exitswitch = var_resume_state
        new_start_block.closeblock(not_resuming_link, *resuming_links)

        old_start_block.isstartblock = False
        new_start_block.isstartblock = True
        graph.startblock = new_start_block

    def insert_return_conversion(self, link, targettype, retvar):
        llops = LowLevelOpList()
        newvar = gen_cast(llops, targettype, retvar)
        convertblock = unsimplify.insert_empty_block(None, link, llops)
        # begin ouch!
        for index, linkvar in enumerate(convertblock.exits[0].args):
            # does this var come from retval ?
            try:
                index1 = convertblock.inputargs.index(linkvar)
            except ValueError:   # e.g. linkvar is a Constant
                continue
            if link.args[index1] is retvar:
                # yes
                convertblock.exits[0].args[index] = newvar
        # end ouch!
        
    def handle_resume_point(self, block, i):
        # in some circumstances we might be able to reuse
        # an already inserted resume point
        op = block.operations[i]
        if i == len(block.operations) - 1:
            link = block.exits[0]
            nextblock = None
        else:
            link = support.split_block_with_keepalive(block, i+1)
            i = 0
            nextblock = link.target

        label = op.args[0].value

        parms = op.args[1:]
        if not isinstance(parms[0], model.Variable):
            assert parms[0].value is None
            parms[0] = None
        args = vars_to_save(block)
        for a in args:
            if a not in parms:
                raise Exception, "not covered needed value at resume_point %r"%(label,)
        if parms[0] is not None: # returns= case
            res = parms[0]
            args = [arg for arg in args if arg is not res]
        else:
            args = args
            res = op.result

        (frame_type,
         varsforcall, saver) = self.frametyper.frame_type_for_vars(parms[1:])

        if label in self.explicit_resume_point_data:
            other_type = self.explicit_resume_point_data[label]
            assert frame_type == other_type, "inconsistent types for label %r"%(label,)
        else:
            self.explicit_resume_point_data[label] = frame_type

        self.resume_blocks.append(
            self._generate_resume_block(varsforcall, frame_type, res, block.exits))

        restart_number = len(self.masterarray1) + len(self.resume_blocks)-1

        if label in self.symbolic_restart_numbers:
            symb = self.symbolic_restart_numbers[label]
            assert symb.value is None
            symb.value = restart_number
        else:
            symb = SymbolicRestartNumber(label, restart_number)
            self.symbolic_restart_numbers[label] = symb

        return nextblock

    def handle_resume_state_create(self, block, i):
        op = block.operations[i]
        llops = LowLevelOpList()
        # XXX we do not look at op.args[0], the prevstate, at all
        label = op.args[1].value
        parms = op.args[2:]
        FRAME, varsforcall, saver = self.frametyper.frame_type_for_vars(parms)

        if label in self.explicit_resume_point_data:
            other_type = self.explicit_resume_point_data[label]
            assert FRAME == other_type, "inconsistent types for label %r"%(label,)
        else:
            self.explicit_resume_point_data[label] = FRAME

        if label in self.symbolic_restart_numbers:
            symb = self.symbolic_restart_numbers[label]
        else:
            symb = SymbolicRestartNumber(label)
            self.symbolic_restart_numbers[label] = symb

        # this is rather insane: we create an exception object, pass
        # it to the saving function, then read the thus created state
        # out of and then clear global_state.top
        c_EXC = model.Constant(self.unwind_exception_type.TO, lltype.Void)
        v_exc = llops.genop('malloc', [c_EXC],
                            resulttype = self.unwind_exception_type)

        realvarsforcall = []
        for v in varsforcall:
            if v.concretetype != lltype.Void:
                realvarsforcall.append(gen_cast(llops, storage_type(v.concretetype), v))
        
        llops.genop('direct_call',
                    [model.Constant(saver, lltype.typeOf(saver)), v_exc,
                     model.Constant(symb, lltype.Signed)] + realvarsforcall,
                    resulttype = lltype.Void)
        v_state = varoftype(lltype.Ptr(frame.STATE_HEADER))
        llops.extend(self.ops_read_global_state_field(v_state, "top"))
        llops.genop("setfield",
                   [self.ll_global_state,
                    self.c_inst_top_name,
                    self.c_null_state])

        v_prevstate = llops.genop('cast_opaque_ptr', [op.args[0]],
                                  resulttype=lltype.Ptr(frame.STATE_HEADER))
        llops.genop('setfield', [v_state,
                                 model.Constant('f_back', lltype.Void),
                                 v_prevstate])
        llops.append(model.SpaceOperation('cast_opaque_ptr', [v_state], op.result))
        block.operations[i:i+1] = llops

    def handle_resume_state_invoke(self, block):
        op = block.operations[-1]
        assert op.opname == 'resume_state_invoke'
        # some commentary.
        #
        # we don't want to write 155 or so different versions of
        # resume_after_foo that appear to the annotator to return
        # different types.  we take advantage of the fact that this
        # function always raises UnwindException and have it (appear
        # to) return Void.  then to placate all the other machinery,
        # we pass a constant zero-of-the-appropriate-type along the
        # non-exceptional link (which we know will never be taken).
        # Nota Bene: only mutate a COPY of the non-exceptional link
        # because the non-exceptional link has been stored in
        # self.resume_blocks and we don't want a constant "zero" in
        # there.
        v_state = op.args[0]
        v_returning = op.args[1]
        v_raising = op.args[2]
        llops = LowLevelOpList()

        if v_raising.concretetype == lltype.Void:
            erased_type = storage_type(v_returning.concretetype)
            resume_after_ptr = self.resume_afters[erased_type]
            v_param = v_returning
        else:
            assert v_returning.concretetype == lltype.Void
            erased_type = self.exception_type
            resume_after_ptr = self.resume_after_raising_ptr
            v_param = v_raising

        if erased_type != v_param.concretetype:
            v_param = gen_cast(llops, erased_type, v_param)
        llops.genop('direct_call', [resume_after_ptr, v_state, v_param],
                    resulttype=lltype.Void)

        del block.operations[-1]
        block.operations.extend(llops)

        noexclink = block.exits[0].copy()
        realrettype = op.result.concretetype
        for i, a in enumerate(noexclink.args):
            if a is op.result:
                noexclink.args[i] = model.Constant(realrettype._defl(), realrettype)
        block.recloseblock(*((noexclink,) + block.exits[1:]))        

    def insert_unwind_handling(self, block, i):
        # for the case where we are resuming to an except:
        # block we need to store here a list of links that
        # might be resumed to, and in insert_resume_handling
        # we need to basically copy each link onto the
        # resuming block.
        #
        # it probably also makes sense to compute the list of
        # args to save once, here, and save that too.
        #
        # finally, it is important that the fetch_retval
        # function be called right at the end of the resuming
        # block, and that it is called even if the return
        # value is not again used.
        
        edata = self.translator.rtyper.getexceptiondata()
        etype = edata.lltype_of_exception_type
        evalue = edata.lltype_of_exception_value

        if i == len(block.operations) - 1 \
               and block.exitswitch == model.c_last_exception:
            link = block.exits[0]
            exitcases = dict.fromkeys(l.exitcase for l in block.exits)
            nextblock = None
        else:
            link = support.split_block_with_keepalive(block, i+1)
            nextblock = link.target
            block.exitswitch = model.c_last_exception
            link.llexitcase = None
            # add a general Exception link, because all calls can
            # raise anything
            v_exctype = varoftype(etype)
            v_excvalue = varoftype(evalue)
            newlink = model.Link([v_exctype, v_excvalue],
                                 self.curr_graph.exceptblock,
                                 Exception)
            newlink.last_exception = v_exctype
            newlink.last_exc_value = v_excvalue
            newexits = list(block.exits)
            newexits.append(newlink)
            block.recloseblock(*newexits)
            self.translator.rtyper._convert_link(block, newlink)

        var_unwind_exception = varoftype(evalue)

        op = block.operations[i]

        args = vars_to_save(block)

        save_block, resume_block, varsforcall = self.generate_save_and_resume_blocks(
            args, var_unwind_exception, op.result, block.exits)

        self.resume_blocks.append(resume_block)

        newlink = model.Link(varsforcall + [var_unwind_exception], 
                             save_block, code.UnwindException)
        newlink.last_exception = model.Constant(code.UnwindException,
                                                etype)
        newlink.last_exc_value = var_unwind_exception
        newexits = list(block.exits)
        newexits.insert(1, newlink)
        block.recloseblock(*newexits)
        self.translator.rtyper._convert_link(block, newlink)
        
        return nextblock

    def transform_block(self, block):
        i = 0

        def replace_with_call(fnptr):
            args = [fnptr] + op.args[1:]
            newop = model.SpaceOperation('direct_call', args, op.result)
            block.operations[i] = newop
            return newop

        while i < len(block.operations):
            stackless_op = False
            op = block.operations[i]
            if op.opname == 'yield_current_frame_to_caller':
                op = replace_with_call(self.yield_current_frame_to_caller_ptr)
                stackless_op = True

            if op.opname == 'resume_state_create':
                self.handle_resume_state_create(block, i)
                continue # go back and look at that malloc
                        
            if (op.opname in ('direct_call', 'indirect_call')
                or self.analyzer.operation_is_true(op)):
                if op.opname == 'resume_point':
                    block = self.handle_resume_point(block, i)
                    if block is None:
                        return
                    else:
                        i = 0
                        continue

                # trap calls to stackless-related suggested primitives
                if op.opname == 'direct_call':
                    func = getattr(op.args[0].value._obj, '_callable', None)
                    if func in self.suggested_primitives:
                        op = replace_with_call(self.suggested_primitives[func])
                        stackless_op = True

                if not stackless_op and not self.analyzer.analyze(op):
                    i += 1
                    continue

                if (not stackless_op and i == len(block.operations) - 1 and
                    len(block.exits) == 1 and
                    block.exits[0].target is self.curr_graph.returnblock and
                    (block.exits[0].args[0].concretetype is lltype.Void or 
                     block.exits[0].args[0] is op.result)):
#                    print "optimizing tail call %s in function %s" % (op, self.curr_graph.name)
                    i += 1
                    continue

                nextblock = self.insert_unwind_handling(block, i)
                if op.opname == 'resume_state_invoke':
                    self.handle_resume_state_invoke(block)
                
                if nextblock is None:
                    return

                block = nextblock
                i = 0
            else:
                i += 1

    def generate_save_and_resume_blocks(self, varstosave, var_exception,
                                        var_result, links_to_resumption):
        frame_type, varsforcall, saver = self.frametyper.frame_type_for_vars(varstosave)
        if SAVE_STATISTICS:
            self.stats.rp_count += 1
            inc(self.stats.rp_type_counts, frame_type)
            inc(self.stats.rp_per_graph, gkey(self.curr_graph))
            inc(self.stats.rp_per_graph_type_counts.setdefault(gkey(self.curr_graph), {}), frame_type)
            exact_key = [v.concretetype for v in varstosave]
            exact_key.sort()
            exact_key = (tuple(exact_key), var_result.concretetype)
            inc(self.stats.cur_rp_exact_types, exact_key)
            inc(self.stats.cur_rp_erased_types, frame_type)

        varsforcall0 = varsforcall[:]
        c_restart = model.Constant(len(self.masterarray1) + len(self.resume_blocks), lltype.Signed)
        varsforcall.insert(0, c_restart)
        varsforcall = [v for v in varsforcall if v.concretetype != lltype.Void]
        
        return (self._generate_save_block(varsforcall, var_exception, saver),
                self._generate_resume_block(varsforcall0, frame_type,
                                            var_result, links_to_resumption),
                varsforcall)

    def _generate_save_block(self, varsforcall, var_unwind_exception, saver):
        conc_types = tuple([v.concretetype for v in varsforcall])
        if conc_types in self.curr_graph_save_blocks:
            return self.curr_graph_save_blocks[conc_types]
        rtyper = self.translator.rtyper
        edata = rtyper.getexceptiondata()
        etype = edata.lltype_of_exception_type
        evalue = edata.lltype_of_exception_value
        def cv(v):
            if isinstance(v, model.Variable):
                return unsimplify.copyvar(None, v)
            else:
                return varoftype(v.concretetype)
        inputargs = [cv(v) for v in varsforcall]
        var_unwind_exception = unsimplify.copyvar(None, var_unwind_exception)

        save_state_block = model.Block(inputargs + [var_unwind_exception])
        saveops = LowLevelOpList()
        
        var_exc = gen_cast(saveops, self.unwind_exception_type, var_unwind_exception)
        
        realvarsforcall = [var_exc]
        for v in inputargs:
            realvarsforcall.append(gen_cast(saveops, storage_type(v.concretetype), v))
        
        saveops.genop('direct_call',
                      [model.Constant(saver, lltype.typeOf(saver))] + realvarsforcall,
                      resulttype=lltype.Void)
        save_state_block.operations = saveops

        type_repr = rclass.get_type_repr(rtyper)
        c_unwindexception = model.Constant(
            type_repr.convert_const(code.UnwindException), etype)
        if not hasattr(self.curr_graph.exceptblock.inputargs[0], 'concretetype'):
            self.curr_graph.exceptblock.inputargs[0].concretetype = etype
        if not hasattr(self.curr_graph.exceptblock.inputargs[1], 'concretetype'):
            self.curr_graph.exceptblock.inputargs[1].concretetype = evalue
        save_state_block.closeblock(model.Link(
            [c_unwindexception, var_unwind_exception], 
            self.curr_graph.exceptblock))
        self.translator.rtyper._convert_link(
            save_state_block, save_state_block.exits[0])
        if SAVE_STATISTICS:
            self.stats.saveops += len(save_state_block.operations)
        self.curr_graph_save_blocks[conc_types] = save_state_block
        return save_state_block

    def _generate_resume_block(self, varsinfieldorder, frame_type,
                               var_result, links_to_resumption):
        typekey = [v.concretetype for v in varsinfieldorder]
        linkkey = [(link.target, link.exitcase) for link in links_to_resumption[1:]]
        key = tuple([var_result.concretetype] + typekey + linkkey)
        if key in self.curr_graph_resume_blocks:
            newblock, switchblock, newargs, newresult = self.curr_graph_resume_blocks[key]
            if switchblock is None:
                newblock.inputargs = [varoftype(lltype.Signed)]
                switchblock = unsimplify.insert_empty_block(None, newblock.exits[0], [])
                newblock.exits[0].args.append(newblock.inputargs[0])
                switchblock.inputargs.append(varoftype(lltype.Signed))
                switchblock.exitswitch = switchblock.inputargs[-1]
                link, = switchblock.exits
                link.exitcase = link.llexitcase = self.resume_blocks.index(newblock)
                mapping = {}
                for i in range(len(newblock.exits[0].args)):
                    mapping[newblock.exits[0].args[i]] = switchblock.inputargs[i]
                if newresult in mapping:
                    newresult = mapping[newresult]
                newnewargs = []
                for arg in newargs:
                    newnewargs.append(mapping[arg])
                newargs = newnewargs
                self.curr_graph_resume_blocks[key] = newblock, switchblock, newnewargs, newresult
            oldlink = links_to_resumption[0]
            varmap = {}
            for old, new in zip(varsinfieldorder, newargs):
                varmap[old] = new
            varmap[var_result] = newresult
            def rename(arg):
                if isinstance(arg, model.Variable):
                    return varmap[arg]
                else:
                    return arg
            newlink = oldlink.copy(rename)
            newlink.exitcase = newlink.llexitcase = len(self.resume_blocks)
            switchblock.recloseblock(*(switchblock.exits + (newlink,)))
            rettype = newresult.concretetype
            retval = newresult
            retlink = newlink
        else:
            newblock = model.Block([])
            newargs = []
            llops = LowLevelOpList()
            llops.genop("setfield",
                        [self.ll_global_state,
                         self.c_restart_substate_name,
                         self.c_minus_one])
            frame_top = varoftype(lltype.Ptr(frame_type))
            llops.extend(self.ops_read_global_state_field(frame_top, "top"))
            llops.genop("setfield",
                       [self.ll_global_state,
                        self.c_inst_top_name,
                        self.c_null_state])
            varmap = {}
            newargs = []
            fielditer = iter(frame_type._names[1:])
            for arg in varsinfieldorder:
                assert arg is not var_result
                t = storage_type(arg.concretetype)
                if t is lltype.Void:
                    v_newarg = model.Constant(None, lltype.Void)
                else:
                    fname = model.Constant(fielditer.next(), lltype.Void)
                    assert frame_type._flds[fname.value] is t
                    v_newarg = llops.genop('getfield', [frame_top, fname],
                                           resulttype = t)
                    v_newarg = gen_cast(llops, arg.concretetype, v_newarg)
                newargs.append(v_newarg)
                varmap[arg] = v_newarg

            rettype = storage_type(var_result.concretetype)
            getretval = self.fetch_retvals[rettype]
            retval = llops.genop("direct_call", [getretval],
                                 resulttype = rettype)
            varmap[var_result] = retval

            newblock.operations.extend(llops)

            def rename(arg):
                if isinstance(arg, model.Variable):
                    if arg in varmap:
                        return varmap[arg]
                    else:
                        assert arg in [l.last_exception, l.last_exc_value]
                        r = unsimplify.copyvar(None, arg)
                        varmap[arg] = r
                        return r
                else:
                    return arg

            newblock.closeblock(*[l.copy(rename)
                                  for l in links_to_resumption])
            # this check is a bit implicit!
            if len(links_to_resumption) > 1:
                newblock.exitswitch = model.c_last_exception
            else:
                newblock.exitswitch = None
            self.curr_graph_resume_blocks[key] = newblock, None, newargs, retval
            retlink = newblock.exits[0]
            if SAVE_STATISTICS:
                self.stats.resumeops += len(newblock.operations)
        
        if var_result.concretetype != rettype:
            self.insert_return_conversion(retlink, var_result.concretetype, retval)

        return newblock
        
    def generate_restart_infos(self, graph):
        restartinfo = frame.RestartInfo(graph, len(self.resume_blocks))
        self.register_restart_info(restartinfo)

    def register_restart_info(self, restartinfo):
        assert not self.is_finished
        rtyper = self.translator.rtyper
        for frame_info in restartinfo.compress(rtyper):
            self.masterarray1.append(frame_info)

    def finish(self):
        # compute the final masterarray by copying over the masterarray1,
        # which is a list of dicts of attributes
        if SAVE_STATISTICS:
            import cPickle
            cPickle.dump(self.stats, open('stackless-stats.pickle', 'wb'))

        self.is_finished = True
        masterarray = lltype.malloc(frame.FRAME_INFO_ARRAY,
                                    len(self.masterarray1),
                                    immortal=True)
        for dst, src in zip(masterarray, self.masterarray1):
            dst.fnaddr, dst.info = src
        # horrors in the same spirit as in rpython.memory.gctransform
        # (shorter, though)
        ll_global_state = self.ll_global_state.value
        ll_global_state.inst_masterarray = masterarray
        return [masterarray]

    def transform_gc_nocollect(self, graph):
        # for the framework gc: in stackless_explicit graphs, make sure
        # that the mallocs won't trigger a collect.
        for block in graph.iterblocks():
            for i, op in enumerate(block.operations):
                if op.opname.startswith('malloc'):
                    newop = model.SpaceOperation('flavored_' + op.opname,
                                                 [self.c_gc_nocollect]+op.args,
                                                 op.result)
                    block.operations[i] = newop
