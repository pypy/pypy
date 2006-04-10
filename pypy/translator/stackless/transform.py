from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython import rarithmetic, rclass, rmodel
from pypy.translator.backendopt import support
from pypy.objspace.flow import model
from pypy.rpython.memory.gctransform import varoftype
from pypy.translator.unsimplify import copyvar
from pypy.annotation import model as annmodel
from pypy.rpython.annlowlevel import MixLevelHelperAnnotator
from pypy.translator.stackless import code 
from pypy.rpython.rclass import getinstancerepr

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

## def func(x):
##     return g() + x + 1

## STATE_func_0 = lltype.Struct('STATE_func_0',
##                              ('header', STATE_HEADER),
##                              ('saved_long_0', Signed))

## def func(x):
##     if global_state.top:
##         if global_state.restart_substate == 0:
##             frame = cast_pointer(lltype.Ptr(STATE_func_0), global_state.top)
##             x = frame.saved_long_0
##             retval = global_state.long_retval
##         else:
##             abort()
##     else:
##         try:
##             retval = g(x)
##         except UnwindException, u:
##             state = lltype.raw_malloc(STATE_func_0)
##             state.saved_long_0 = x
##             state.header.f_back = u.frame
##             state.header.state = XXX
##             u.frame = state.header
##             raise
        
##     return retval + x + 1

class ResumePoint:
    def __init__(self, var_result, link_to_resumption, frame_state_type):
        self.var_result = var_result
        self.link_to_resumption = link_to_resumption
        self.frame_state_type = frame_state_type

class StacklessTransfomer(object):
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

        annotations = [annmodel.SomeInstance(bk.getuniqueclassdef(code.UnwindException)),
                       annmodel.SomePtr(lltype.Ptr(STATE_HEADER))]

        add_frame_state_graph = mixlevelannotator.getgraph(
            code.add_frame_state,
            annotations, l2a(lltype.Void))
        ADD_FRAME_STATE_TYPE = lltype.FuncType(
            [self.unwind_exception_type, lltype.Ptr(STATE_HEADER)],
            lltype.Void)
        self.add_frame_state_ptr = model.Constant(lltype.functionptr(
            ADD_FRAME_STATE_TYPE, "add_frame_state",
            graph=add_frame_state_graph),
            lltype.Ptr(ADD_FRAME_STATE_TYPE))

        RESUME_STATE_TYPE = lltype.FuncType([], lltype.Signed)
        resume_state_graph = mixlevelannotator.getgraph(
            code.resume_state, [], annmodel.SomeInteger())
        self.resume_state_ptr = model.Constant(lltype.functionptr(
            RESUME_STATE_TYPE, "resume_state",
            graph=resume_state_graph),
            lltype.Ptr(RESUME_STATE_TYPE))

        FETCH_RETVAL_LONG_TYPE = lltype.FuncType([], lltype.Signed)
        fetch_retval_long_graph = mixlevelannotator.getgraph(
            code.fetch_retval_long, [], annmodel.SomeInteger())
        self.fetch_retval_long_ptr = model.Constant(lltype.functionptr(
            FETCH_RETVAL_LONG_TYPE, "fetch_retval_long",
            graph=fetch_retval_long_graph),
            lltype.Ptr(FETCH_RETVAL_LONG_TYPE))

        mixlevelannotator.finish()

        s_global_state = bk.immutablevalue(code.global_state)
        r_global_state = translator.rtyper.getrepr(s_global_state)
        self.ll_global_state = model.Constant(r_global_state.convert_const(code.global_state),
                                              r_global_state.lowleveltype)
        

    def frame_type_for_vars(self, vars):
        types = [storage_type(v.concretetype) for v in vars]
        counts = dict.fromkeys(range(len(STORAGE_TYPES)), 0)
        for t in types:
            counts[t] = counts[t] + 1
        keys = counts.keys()
        keys.sort()
        key = tuple([counts[k] for k in keys])
        if key in self.frametypes:
            return self.frametypes[key]
        else:
            fields = []
            for i, k in enumerate(key):
                for j in range(k):
                    fields.append(('state_%s_%d'%(STORAGE_FIELDS[i], j), STORAGE_TYPES[i]))
            T = lltype.Struct("state_%d_%d_%d_%d"%tuple(key),
                              ('header', STATE_HEADER),
                              *fields)
            self.frametypes[key] = T
            return T

    def transform_graph(self, graph):
        self.resume_points = []
        
        assert self.curr_graph is None
        self.curr_graph = graph
        
        for block in list(graph.iterblocks()):
            self.transform_block(block)

        if self.resume_points:
            self.insert_resume_handling(graph)

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
            [self.ll_global_state, model.Constant(llfieldname, lltype.Void)],
            tmpvar))
        if tmpvar is not targetvar: 
            ops.append(model.SpaceOperation(
                "cast_pointer", [tmpvar],
                targetvar))
        return ops

    def insert_resume_handling(self, graph):
        old_start_block = graph.startblock
        newinputargs = [copyvar(self.translator, v) for v in old_start_block.inputargs]
        new_start_block = model.Block(newinputargs)
        var_resume_state = varoftype(lltype.Signed)
        new_start_block.operations.append(
            model.SpaceOperation("direct_call", [self.resume_state_ptr], var_resume_state))
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
                "setfield", [self.ll_global_state, model.Constant("inst_top", lltype.Void),
                             model.Constant(null_state, lltype.typeOf(null_state))],
                            varoftype(lltype.Void)))
            i = 0
            for arg in resume_point.link_to_resumption.args:
                newarg = copyvar(self.translator, arg)
                if arg is resume_point.var_result:
                    ops.append(model.SpaceOperation("direct_call", [self.fetch_retval_long_ptr], newarg))
                else:
                    # frame_state_type._names[0] is 'header'
                    fname = model.Constant(frame_state_type._names[i+1], lltype.Void)
                    ops.append(model.SpaceOperation(
                        'getfield', [frame_top, fname], newarg))
                    i += 1
                newargs.append(newarg)
            newblock.operations.extend(ops)
            newblock.closeblock(model.Link(newargs, resume_point.link_to_resumption.target))
            
            resuming_links.append(model.Link([], newblock, resume_point_index+1))
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
                if i == len(block.operations) - 1 and block.exitswitch == model.c_last_exception:
                    link = block.exits[0]
                else:
                    link = support.split_block_with_keepalive(self.translator, block, i+1)
                    block.exitswitch = model.c_last_exception
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
                args = [v for v in link.args 
                        if v is not op.result and v.concretetype is not lltype.Void]
                save_block, frame_state_type = self.generate_save_block(
                                args, var_unwind_exception)

                self.resume_points.append(ResumePoint(op.result, link, frame_state_type))

                newlink = model.Link(args + [var_unwind_exception], 
                                     save_block, code.UnwindException)
                newlink.last_exception = model.Constant(code.UnwindException, etype) 
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
        inputargs = [copyvar(self.translator, v) for v in varstosave]
        var_unwind_exception = copyvar(self.translator, var_unwind_exception) 

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

        saveops.append(model.SpaceOperation('malloc',
                                        [model.Constant(frame_type, lltype.Void)],
                                        frame_state_var))
        
        saveops.extend(self.generate_saveops(frame_state_var, inputargs))

        var_exc = varoftype(self.unwind_exception_type)
        saveops.append(model.SpaceOperation("cast_pointer", [var_unwind_exception], 
                                            var_exc))
        
        var_header = varoftype(lltype.Ptr(STATE_HEADER))
    
        # XXX should this be getsubstruct?
        saveops.append(model.SpaceOperation("getsubstruct", [frame_state_var, model.Constant("header", lltype.Void)], var_header))

        saveops.append(model.SpaceOperation(
            "direct_call",
            [self.add_frame_state_ptr, var_exc, var_header],
            varoftype(lltype.Void)))

        saveops.append(model.SpaceOperation(
            "setfield", [var_header, model.Constant("restartstate", lltype.Void), 
                         model.Constant(len(self.resume_points)+1, lltype.Signed)],
                        varoftype(lltype.Void)))
        # XXX add returntypes 

        funcptr = rtyper.type_system.getcallable(self.curr_graph)
        saveops.append(model.SpaceOperation(
            "setfield", [var_header, model.Constant("function", lltype.Void), 
                         model.Constant(llmemory.fakeaddress(funcptr), llmemory.Address)],
                        varoftype(lltype.Void)))

        type_repr = rclass.get_type_repr(rtyper)
        c_unwindexception = model.Constant(type_repr.convert_const(code.UnwindException), etype)
        if not hasattr(self.curr_graph.exceptblock.inputargs[0], 'concretetype'):
            self.curr_graph.exceptblock.inputargs[0].concretetype = etype
        if not hasattr(self.curr_graph.exceptblock.inputargs[1], 'concretetype'):
            self.curr_graph.exceptblock.inputargs[1].concretetype = evalue
        save_state_block.closeblock(model.Link([c_unwindexception, var_unwind_exception], 
                                               self.curr_graph.exceptblock))
        self.translator.rtyper._convert_link(save_state_block, save_state_block.exits[0])
        return save_state_block, frame_type
        

    def generate_saveops(self, frame_state_var, varstosave):
        frame_type = frame_state_var.concretetype.TO
        ops = []
        for i, var in enumerate(varstosave):
            t = storage_type(var.concretetype)
            fname = model.Constant(frame_type._names[i+1], lltype.Void)
            ops.append(model.SpaceOperation('setfield',
                                            [frame_state_var, fname, var],
                                            varoftype(lltype.Void)))

        return ops
        
        
