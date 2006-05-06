from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython import rarithmetic, rclass, rmodel
from pypy.translator.backendopt import support
from pypy.objspace.flow import model
from pypy.rpython.memory.gctransform import varoftype
from pypy.translator import unsimplify
from pypy.annotation import model as annmodel
from pypy.rpython.annlowlevel import MixLevelHelperAnnotator
from pypy.translator.stackless import code 
from pypy.rpython.rclass import getinstancerepr
from pypy.rpython.typesystem import getfunctionptr
from pypy.rpython.rbuiltin import gen_cast
from pypy.rpython.rtyper import LowLevelOpList

from pypy.translator.stackless.code import STATE_HEADER, null_state

STORAGE_TYPES = [llmemory.Address,
                 lltype.Signed,
                 lltype.Float,
                 lltype.SignedLongLong]
STORAGE_FIELDS = ['addr',
                  'long',
                  'float',
                  'longlong']

def storage_type(T):
    """Return the index into STORAGE_TYPES 
    """
    if T is lltype.Void:
        return None
    elif T is lltype.Float:
        return 2
    elif T in [lltype.SignedLongLong, lltype.UnsignedLongLong]:
        return 3
    elif T is llmemory.Address or isinstance(T, lltype.Ptr):
        return 0
    elif isinstance(T, lltype.Primitive):
        return 1
    else:
        raise Exception("don't know about %r" % (T,))

# a simple example of what the stackless transform does
#
# def func(x):
#     return g() + x + 1
#
# STATE_func_0 = lltype.Struct('STATE_func_0',
#                              ('header', code.STATE_HEADER),
#                              ('saved_long_0', Signed))
#
# def func(x):
#     state = global_state.restart_substate
#     global_state.restart_substate = 0
#     if state == 0:   # normal case
#         try:
#             retval = g(x)
#         except code.UnwindException, u:
#             state = lltype.malloc(STATE_func_0)
#             state.header.restartstate = 1
#             state.header.function = llmemory.cast_ptr_to_adr(func)
#             state.header.retval_type = code.RETVAL_LONG
#             state.saved_long_0 = x
#             code.add_frame_state(u, state.header)
#             raise
#     elif state == 1:
#         state = lltype.cast_pointer(lltype.Ptr(STATE_func_0),
#                                     global_state.top)
#         global_state.top = null_state
#         x = state.saved_long_0
#         retval = global_state.long_retval
#     else:
#         abort()
#     return retval + x + 1

class ResumePoint:
    def __init__(self, var_result, args, links_to_resumption, frame_state_type):
        self.var_result = var_result
        self.args = args
        self.links_to_resumption = links_to_resumption
        self.frame_state_type = frame_state_type

class StacklessTransformer(object):
    def __init__(self, translator):
        self.translator = translator

        edata = translator.rtyper.getexceptiondata()
        bk = translator.annotator.bookkeeper

        self.unwind_exception_type = getinstancerepr(
            self.translator.rtyper,
            bk.getuniqueclassdef(code.UnwindException)).lowleveltype
        self.frametypes = {}
        self.curr_graph = None
                
        mixlevelannotator = MixLevelHelperAnnotator(translator.rtyper)
        l2a = annmodel.lltype_to_annotation

        unwinddef = bk.getuniqueclassdef(code.UnwindException)
        add_frame_state_graph = mixlevelannotator.getgraph(
            code.add_frame_state,
            [annmodel.SomeInstance(unwinddef),
             annmodel.SomePtr(lltype.Ptr(STATE_HEADER))],
            l2a(lltype.Void))

        resume_state_graph = mixlevelannotator.getgraph(
            code.resume_state, [], annmodel.SomeInteger())

        fetch_retval_void_graph = mixlevelannotator.getgraph(
            code.fetch_retval_void, [], annmodel.s_None)
        fetch_retval_long_graph = mixlevelannotator.getgraph(
            code.fetch_retval_long, [], annmodel.SomeInteger())
        fetch_retval_longlong_graph = mixlevelannotator.getgraph( # WAA!
            code.fetch_retval_longlong, [], annmodel.SomeInteger(size=2))
        fetch_retval_float_graph = mixlevelannotator.getgraph(
            code.fetch_retval_float, [], annmodel.SomeFloat())
        fetch_retval_void_p_graph = mixlevelannotator.getgraph(
            code.fetch_retval_void_p, [], annmodel.SomeAddress())

        mixlevelannotator.finish()

        def fptr(graph):
            FTYPE = lltype.FuncType(
                [v.concretetype for v in graph.startblock.inputargs],
                graph.returnblock.inputargs[0].concretetype)
            return model.Constant(getfunctionptr(graph), lltype.Ptr(FTYPE))

        self.add_frame_state_ptr = fptr(add_frame_state_graph)

        self.resume_state_ptr = fptr(resume_state_graph)

        self.fetch_retval_void_ptr = fptr(fetch_retval_void_graph)
        self.fetch_retval_long_ptr = fptr(fetch_retval_long_graph)
        self.fetch_retval_longlong_ptr = fptr(fetch_retval_longlong_graph)
        self.fetch_retval_float_ptr = fptr(fetch_retval_float_graph)
        self.fetch_retval_void_p_ptr = fptr(fetch_retval_void_p_graph)

        s_global_state = bk.immutablevalue(code.global_state)
        r_global_state = translator.rtyper.getrepr(s_global_state)
        self.ll_global_state = model.Constant(
            r_global_state.convert_const(code.global_state),
            r_global_state.lowleveltype)
        self.seen_blocks = set()


    def frame_type_for_vars(self, vars):
        types = [storage_type(v.concretetype) for v in vars]
        counts = [0] * len(STORAGE_TYPES)
        for t in types:
            counts[t] = counts[t] + 1
        key = tuple(counts)
        if key in self.frametypes:
            return self.frametypes[key]
        else:
            fields = []
            for i, k in enumerate(key):
                for j in range(k):
                    fields.append(
                        ('state_%s_%d'%(STORAGE_FIELDS[i], j), STORAGE_TYPES[i]))
            T = lltype.Struct("state_%d_%d_%d_%d"%tuple(key),
                              ('header', STATE_HEADER),
                              *fields)
            self.frametypes[key] = T
            return T

    def transform_all(self):
        for graph in self.translator.graphs:
            self.transform_graph(graph)
        
    def transform_graph(self, graph):
        self.resume_points = []
        
        if hasattr(graph, 'func'):
            if getattr(graph.func, 'stackless_explicit', False):
                return
        
        assert self.curr_graph is None
        self.curr_graph = graph
        
        for block in list(graph.iterblocks()):
            assert block not in self.seen_blocks
            self.transform_block(block)
            self.seen_blocks.add(block)

        if self.resume_points:
            self.insert_resume_handling(graph)

        model.checkgraph(graph)

        self.curr_graph = None

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
        newinputargs = [unsimplify.copyvar(self.translator, v)
                        for v in old_start_block.inputargs]
        new_start_block = model.Block(newinputargs)
        var_resume_state = varoftype(lltype.Signed)
        new_start_block.operations.append(
            model.SpaceOperation("direct_call",
                                 [self.resume_state_ptr],
                                 var_resume_state))
        not_resuming_link = model.Link(newinputargs, old_start_block, 0)
        not_resuming_link.llexitcase = 0
        resuming_links = []
        for resume_point_index, resume_point in enumerate(self.resume_points):
            newblock = model.Block([])
            newargs = []
            ops = []
            frame_state_type = resume_point.frame_state_type
            frame_top = varoftype(lltype.Ptr(frame_state_type))
            ops.extend(self.ops_read_global_state_field(frame_top, "top"))
            ops.append(model.SpaceOperation(
                "setfield",
                [self.ll_global_state,
                 model.Constant("inst_top", lltype.Void),
                 model.Constant(null_state, lltype.typeOf(null_state))],
                varoftype(lltype.Void)))
            varmap = {}
            for i, arg in enumerate(resume_point.args):
                newarg = varmap[arg] = unsimplify.copyvar(self.translator, arg)
                assert arg is not resume_point.var_result
                fname = model.Constant(frame_state_type._names[i+1], lltype.Void)
                ops.append(model.SpaceOperation(
                    'getfield', [frame_top, fname], newarg))

            r = storage_type(resume_point.var_result.concretetype)
            if r is not None:
                rettype = STORAGE_TYPES[r]
            else:
                rettype = lltype.Void

            if rettype == lltype.Signed:
                getretval = self.fetch_retval_long_ptr
            if rettype == lltype.SignedLongLong:
                getretval = self.fetch_retval_longlong_ptr
            elif rettype == lltype.Void:
                getretval = self.fetch_retval_void_ptr
            elif rettype == lltype.Float:
                getretval = self.fetch_retval_float_ptr
            elif rettype == llmemory.Address:
##                if resume_point.var_result.concretetype is not \
##                       llmemory.Address:
##                    if resume_point.var_result in \
##                           resume_point.links_to_resumption[0].args:
##                        need_address_conversion = True
                getretval = self.fetch_retval_void_p_ptr

            varmap[resume_point.var_result] = retval = varoftype(rettype)
            ops.append(model.SpaceOperation("direct_call", [getretval], retval))

            newblock.operations.extend(ops)

            def rename(arg):
                if isinstance(arg, model.Variable):
                    if arg in varmap:
                        return varmap[arg]
                    else:
                        assert arg in [l.last_exception, l.last_exc_value]
                        r = unsimplify.copyvar(self.translator, arg)
                        varmap[arg] = r
                        return r
                else:
                    return arg

            newblock.closeblock(*[l.copy(rename)
                                  for l in resume_point.links_to_resumption])
            # this check is a bit implicit!
            if len(resume_point.links_to_resumption) > 1:
                newblock.exitswitch = model.c_last_exception
            else:
                newblock.exitswitch = None

            if resume_point.var_result.concretetype != rettype:
                llops = LowLevelOpList(None)
                newvar = gen_cast(llops,
                                  resume_point.var_result.concretetype,
                                  retval)
                convertblock = unsimplify.insert_empty_block(
                    self.translator, newblock.exits[0], llops)
                # begin ouch!
                for index, linkvar in enumerate(convertblock.exits[0].args):
                    # does this var come from retval ?
                    try:
                        index1 = convertblock.inputargs.index(linkvar)
                    except IndexError:
                        continue
                    if newblock.exits[0].args[index1] is retval:
                        # yes
                        convertblock.exits[0].args[index] = newvar
                # end ouch!
            
            resuming_links.append(
                model.Link([], newblock, resume_point_index+1))
            resuming_links[-1].llexitcase = resume_point_index+1
        new_start_block.exitswitch = var_resume_state
        new_start_block.closeblock(not_resuming_link, *resuming_links)

        old_start_block.isstartblock = False
        new_start_block.isstartblock = True
        graph.startblock = new_start_block

    def transform_block(self, block):
        i = 0

        edata = self.translator.rtyper.getexceptiondata()
        etype = edata.lltype_of_exception_type
        evalue = edata.lltype_of_exception_value
        
        while i < len(block.operations):
            op = block.operations[i]
            if op.opname in ('direct_call', 'indirect_call'):
                if i == len(block.operations) - 1 \
                       and block.exitswitch == model.c_last_exception:
                    link = block.exits[0]
                    exitcases = dict.fromkeys(l.exitcase for l in block.exits)
                    if code.UnwindException in exitcases:
                        return
                else:
                    link = support.split_block_with_keepalive(block, i+1)
                    # this section deserves a whinge:
                    
                    # i want to use rtyper.insert_link_conversions() in
                    # insert_resume_handling().  insert_link_conversions()
                    # calls bindingrepr(), which depends on variables having
                    # annotations.  split_block called copyvar(None, ...)
                    # which doesn't preserve the annotation.  so put it back
                    # here.  it certainly sucks that this module has to worry
                    # about annotations :(
##                    XXX is this still needed?
##                    ann = self.translator.annotator
##                    for f, t in zip(link.args, link.target.inputargs):
##                        nb = ann.binding(f, None)
##                        if nb is not None:
##                            ann.setbinding(t, nb)
                    block.exitswitch = model.c_last_exception
                    link.llexitcase = None
                var_unwind_exception = varoftype(evalue)
               
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
                args = []
                for l in block.exits:
                    for arg in link.args:
                        if isinstance(arg, model.Variable) \
                           and arg.concretetype is not lltype.Void \
                           and arg is not op.result \
                           and arg not in args:
                            args.append(arg)
                
                save_block, frame_state_type = self.generate_save_block(
                                args, var_unwind_exception)

                self.resume_points.append(
                    ResumePoint(op.result, args, tuple(block.exits), frame_state_type))

                newlink = model.Link(args + [var_unwind_exception], 
                                     save_block, code.UnwindException)
                newlink.last_exception = model.Constant(code.UnwindException,
                                                        etype)
                newlink.last_exc_value = var_unwind_exception
                newexits = list(block.exits)
                newexits.insert(1, newlink)
                block.recloseblock(*newexits)
                self.translator.rtyper._convert_link(block, newlink)

                block = link.target
                i = 0
            else:
                i += 1

    def generate_save_block(self, varstosave, var_unwind_exception):
        rtyper = self.translator.rtyper
        edata = rtyper.getexceptiondata()
        etype = edata.lltype_of_exception_type
        evalue = edata.lltype_of_exception_value
        inputargs = [unsimplify.copyvar(self.translator, v) for v in varstosave]
        var_unwind_exception = unsimplify.copyvar(
            self.translator, var_unwind_exception) 

        fields = []
        n = []
        for i, v in enumerate(varstosave):
            assert v.concretetype is not lltype.Void
            fields.append(('field_%d'%(i,), v.concretetype))
            n.append(repr(v.concretetype))
        
        frame_type = lltype.GcStruct("S" + '-'.join(n),
                            ('header', STATE_HEADER),
                            *fields)
        

        save_state_block = model.Block(inputargs + [var_unwind_exception])
        saveops = save_state_block.operations
        frame_state_var = varoftype(lltype.Ptr(frame_type))

        saveops.append(model.SpaceOperation(
            'malloc',
            [model.Constant(frame_type, lltype.Void)],
            frame_state_var))
        
        saveops.extend(self.generate_saveops(frame_state_var, inputargs))

        var_exc = varoftype(self.unwind_exception_type)
        saveops.append(model.SpaceOperation(
            "cast_pointer",
            [var_unwind_exception], 
            var_exc))
        
        var_header = varoftype(lltype.Ptr(STATE_HEADER))
    
        saveops.append(model.SpaceOperation(
            "cast_pointer", [frame_state_var], var_header))

        saveops.append(model.SpaceOperation(
            "direct_call",
            [self.add_frame_state_ptr, var_exc, var_header],
            varoftype(lltype.Void)))

        saveops.append(model.SpaceOperation(
            "setfield",
            [var_header, model.Constant("restartstate", lltype.Void), 
             model.Constant(len(self.resume_points)+1, lltype.Signed)],
            varoftype(lltype.Void)))

        funcptr = rtyper.type_system.getcallable(self.curr_graph)
        saveops.append(model.SpaceOperation(
            "setfield",
            [var_header, model.Constant("function", lltype.Void), 
             model.Constant(llmemory.fakeaddress(funcptr), llmemory.Address)],
            varoftype(lltype.Void)))
        rettype = lltype.typeOf(funcptr).TO.RESULT
        retval_type = {None: code.RETVAL_VOID,
                       0: code.RETVAL_VOID_P,
                       1: code.RETVAL_LONG,
                       2: code.RETVAL_FLOAT,
                       3: code.RETVAL_LONGLONG}[storage_type(rettype)]
        
        saveops.append(model.SpaceOperation(
            "setfield", [var_header, model.Constant("retval_type", lltype.Void), 
                         model.Constant(retval_type, lltype.Signed)],
            varoftype(lltype.Void)))

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
        return save_state_block, frame_type
        
    def generate_saveops(self, frame_state_var, varstosave):
        frame_type = frame_state_var.concretetype.TO
        ops = []
        for i, var in enumerate(varstosave):
            t = storage_type(var.concretetype)
            fname = model.Constant(frame_type._names[i+1], lltype.Void)
            ops.append(model.SpaceOperation(
                'setfield',
                [frame_state_var, fname, var],
                varoftype(lltype.Void)))
        return ops
