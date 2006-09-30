from pypy.objspace.flow.model import Variable, Constant, Block, Link
from pypy.objspace.flow.model import SpaceOperation, mkentrymap
from pypy.annotation        import model as annmodel
from pypy.jit.hintannotator import model as hintmodel
from pypy.jit.hintannotator.model import originalconcretetype
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.rmodel import inputconst
from pypy.translator.unsimplify import varoftype, copyvar
from pypy.translator.unsimplify import split_block, split_block_at_start
from pypy.translator.simplify import rec_op_has_side_effects
from pypy.translator.backendopt.ssa import SSA_to_SSI
from pypy.translator.backendopt import support


class MergePointFamily(object):
    def __init__(self, tsgraph, is_global=False):
        self.tsgraph = tsgraph
        self.is_global = is_global
        self.count = 0
        self.resumepoint_after_mergepoint = {}
    def add(self):
        result = self.count
        self.count += 1
        return 'mp%d' % result
    def getattrnames(self):
        return ['mp%d' % i for i in range(self.count)]


class HintGraphTransformer(object):
    c_dummy = inputconst(lltype.Void, None)

    def __init__(self, hannotator, graph):
        self.hannotator = hannotator
        self.graph = graph
        self.graphcolor = self.graph_calling_color(graph)
        self.global_merge_points = self.graph_global_mps(self.graph)
        self.resumepoints = {}
        self.mergepoint_set = {}    # set of blocks
        self.mergepointfamily = MergePointFamily(graph,
                                                 self.global_merge_points)
        self.c_mpfamily = inputconst(lltype.Void, self.mergepointfamily)
        self.tsgraphs_seen = []

    def transform(self):
        self.compute_merge_points()
        self.insert_save_return()
        self.insert_splits()
        self.split_after_calls()
        self.handle_hints()
        self.insert_merge_points()
        self.insert_enter_graph()
        self.insert_dispatcher()
        self.insert_leave_graph()

    def compute_merge_points(self):
        entrymap = mkentrymap(self.graph)
        for block, links in entrymap.items():
            if len(links) > 1 and block is not self.graph.returnblock:
                self.mergepoint_set[block] = True
        if self.global_merge_points:
            self.mergepoint_set[self.graph.startblock] = True

    def graph_calling_color(self, tsgraph):
        args_hs, hs_res = self.hannotator.bookkeeper.tsgraphsigs[tsgraph]
        if originalconcretetype(hs_res) is lltype.Void:
            return 'gray'
        elif hs_res.is_green():
            return 'yellow'
        else:
            return 'red'

    def graph_global_mps(self, tsgraph):
        try:
            return tsgraph.func._global_merge_points_
        except AttributeError:
            return False

    def timeshifted_graph_of(self, graph, args_v):
        bk = self.hannotator.bookkeeper
        args_hs = [self.hannotator.binding(v) for v in args_v]
        # fixed is always false here
        specialization_key = bk.specialization_key(False, args_hs)
        tsgraph = bk.get_graph_by_key(graph, specialization_key)
        self.tsgraphs_seen.append(tsgraph)
        return tsgraph

    # __________ helpers __________

    def genop(self, block, opname, args, resulttype=None, result_like=None):
        # 'result_like' can be a template variable whose hintannotation is
        # copied
        if resulttype is not None:
            v_res = varoftype(resulttype)
            hs = hintmodel.SomeLLAbstractConstant(resulttype, {})
            self.hannotator.setbinding(v_res, hs)
        elif result_like is not None:
            v_res = copyvar(self.hannotator, result_like)
        else:
            v_res = self.new_void_var()

        spaceop = SpaceOperation(opname, args, v_res)
        if isinstance(block, list):
            block.append(spaceop)
        else:
            block.operations.append(spaceop)
        return v_res

    def genswitch(self, block, v_exitswitch, false, true):
        block.exitswitch = v_exitswitch
        link_f = Link([], false)
        link_f.exitcase = False
        link_t = Link([], true)
        link_t.exitcase = True
        block.recloseblock(link_f, link_t)

    def new_void_var(self, name=None):
        v_res = varoftype(lltype.Void, name)
        self.hannotator.setbinding(v_res, annmodel.s_ImpossibleValue)
        return v_res

    def new_block_before(self, block):
        newinputargs = [copyvar(self.hannotator, var)
                        for var in block.inputargs]
        newblock = Block(newinputargs)
        bridge = Link(newinputargs, block)
        newblock.closeblock(bridge)
        return newblock

    def naive_split_block(self, block, position):
        newblock = Block([])
        newblock.operations = block.operations[position:]
        del block.operations[position:]
        newblock.exitswitch = block.exitswitch
        block.exitswitch = None
        newblock.recloseblock(*block.exits)
        block.recloseblock(Link([], newblock))
        return newblock

    def variables_alive(self, block, before_position):
        created_before = dict.fromkeys(block.inputargs)
        for op in block.operations[:before_position]:
            created_before[op.result] = True
        used = {}
        for op in block.operations[before_position:]:
            for v in op.args:
                used[v] = True
        for link in block.exits:
            for v in link.args:
                used[v] = True
        return [v for v in used if v in created_before]

    def sort_by_color(self, vars, by_color_of_vars=None):
        reds = []
        greens = []
        if by_color_of_vars is None:
            by_color_of_vars = vars
        for v, bcv in zip(vars, by_color_of_vars):
            if self.hannotator.binding(bcv).is_green():
                greens.append(v)
            else:
                reds.append(v)
        return reds, greens

    def before_start_block(self):
        entryblock = self.new_block_before(self.graph.startblock)
        entryblock.isstartblock = True
        self.graph.startblock.isstartblock = False
        self.graph.startblock = entryblock
        return entryblock

    def before_return_block(self):
        block = self.graph.returnblock
        block.operations = []
        split_block(self.hannotator, block, 0)
        [link] = block.exits
        assert len(link.args) == 0
        link.args = [self.c_dummy]
        link.target.inputargs = [self.new_void_var('dummy')]
        self.graph.returnblock = link.target
        self.graph.returnblock.operations = ()
        return block

    # __________ transformation steps __________

    def insert_splits(self):
        hannotator = self.hannotator
        for block in self.graph.iterblocks():
            if block.exitswitch is not None:
                assert isinstance(block.exitswitch, Variable)
                hs_switch = hannotator.binding(block.exitswitch)
                if not hs_switch.is_green():
                    self.insert_split_handling(block)

    def insert_split_handling(self, block):
        # lots of clever in-line logic commented out
        v_redswitch = block.exitswitch
        link_f, link_t = block.exits
        if link_f.exitcase:
            link_f, link_t = link_t, link_f
        assert link_f.exitcase is False
        assert link_t.exitcase is True

##        constant_block = Block([])
##        nonconstant_block = Block([])

##        v_flag = self.genop(block, 'is_constant', [v_redswitch],
##                            resulttype = lltype.Bool)
##        self.genswitch(block, v_flag, true  = constant_block,
##                                      false = nonconstant_block)

##        v_greenswitch = self.genop(constant_block, 'revealconst',
##                                   [v_redswitch],
##                                   resulttype = lltype.Bool)
##        constant_block.exitswitch = v_greenswitch
##        constant_block.closeblock(link_f, link_t)

        reds, greens = self.sort_by_color(link_f.args, link_f.target.inputargs)
        self.genop(block, 'save_locals', reds)
        resumepoint = self.get_resume_point(link_f.target)
        c_resumepoint = inputconst(lltype.Signed, resumepoint)
        v_flag = self.genop(block, 'split',
                            [v_redswitch, c_resumepoint] + greens,
                            resulttype = lltype.Bool)

        block.exitswitch = v_flag
        true_block = Block([])
        true_link  = Link([], true_block)
        true_link.exitcase   = True
        true_link.llexitcase = True
        block.recloseblock(link_f, true_link)

        reds, greens = self.sort_by_color(link_t.args)
        self.genop(true_block, 'save_locals', reds)
        self.genop(true_block, 'enter_block', [])
        true_block.closeblock(Link(link_t.args, link_t.target))

        SSA_to_SSI({block     : True,    # reachable from outside
                    true_block: False}, self.hannotator)

    def get_resume_point_link(self, block):
        try:
            return self.resumepoints[block]
        except KeyError:
            resumeblock = Block([])
            redcount   = 0
            greencount = 0
            newvars = []
            for v in block.inputargs:
                if self.hannotator.binding(v).is_green():
                    c = inputconst(lltype.Signed, greencount)
                    v1 = self.genop(resumeblock, 'restore_green', [c],
                                    result_like = v)
                    greencount += 1
                else:
                    c = inputconst(lltype.Signed, redcount)
                    v1 = self.genop(resumeblock, 'restore_local', [c],
                                    result_like = v)
                    redcount += 1
                newvars.append(v1)

            resumeblock.closeblock(Link(newvars, block))
            reenter_link = Link([], resumeblock)
            N = len(self.resumepoints)
            reenter_link.exitcase = N
            self.resumepoints[block] = reenter_link
            return reenter_link

    def get_resume_point(self, block):
        return self.get_resume_point_link(block).exitcase

    def go_to_if(self, block, target, v_finished_flag):
        block.exitswitch = v_finished_flag
        [link_f] = block.exits
        link_t = Link([self.c_dummy], target)
        link_f.exitcase = False
        link_t.exitcase = True
        block.recloseblock(link_f, link_t)

    def go_to_dispatcher_if(self, block, v_finished_flag):
        self.go_to_if(block, self.graph.returnblock, v_finished_flag)

    def insert_merge_points(self):
        for block in self.mergepoint_set:
            self.insert_merge(block)

    def insert_merge(self, block):
        reds, greens = self.sort_by_color(block.inputargs)
        nextblock = self.naive_split_block(block, 0)

        self.genop(block, 'save_locals', reds)
        mp   = self.mergepointfamily.add()
        c_mp = inputconst(lltype.Void, mp)
        if self.global_merge_points:
            self.genop(block, 'save_greens', greens)
            prefix = 'global_'
        else:
            prefix = ''
        v_finished_flag = self.genop(block, '%smerge_point' % (prefix,),
                                     [self.c_mpfamily, c_mp] + greens,
                                     resulttype = lltype.Bool)
        self.go_to_dispatcher_if(block, v_finished_flag)

        restoreops = []
        mapping = {}
        for i, v in enumerate(reds):
            c = inputconst(lltype.Signed, i)
            v1 = self.genop(restoreops, 'restore_local', [c],
                            result_like = v)
            mapping[v] = v1
        nextblock.renamevariables(mapping)
        nextblock.operations[:0] = restoreops

        SSA_to_SSI({block    : True,    # reachable from outside
                    nextblock: False}, self.hannotator)

        if self.global_merge_points:
            N = self.get_resume_point(nextblock)
            self.mergepointfamily.resumepoint_after_mergepoint[mp] = N

    def insert_dispatcher(self):
        if self.global_merge_points or self.resumepoints:
            block = self.before_return_block()
            self.genop(block, 'dispatch_next', [])
            if self.global_merge_points:
                block = self.before_return_block()
                entryblock = self.before_start_block()
                v_rp = self.genop(entryblock, 'getresumepoint', [],
                                  resulttype = lltype.Signed)
                c_zero = inputconst(lltype.Signed, 0)
                v_abnormal_entry = self.genop(entryblock, 'int_ge',
                                              [v_rp, c_zero],
                                              resulttype = lltype.Bool)
                self.go_to_if(entryblock, block, v_abnormal_entry)

            v_switchcase = self.genop(block, 'getresumepoint', [],
                                      resulttype = lltype.Signed)
            block.exitswitch = v_switchcase
            defaultlink = block.exits[0]
            defaultlink.exitcase = 'default'
            links = self.resumepoints.values()
            links.sort(lambda l, r: cmp(l.exitcase, r.exitcase))
            links.append(defaultlink)
            block.recloseblock(*links)

    def insert_save_return(self):
        block = self.before_return_block()
        [v_retbox] = block.inputargs
        if self.graphcolor == 'gray':
            self.genop(block, 'save_locals', [])
        elif self.graphcolor == 'yellow':
            self.genop(block, 'save_greens', [v_retbox])
        elif self.graphcolor == 'red':
            self.leave_graph_opname = 'leave_graph_red'
            self.genop(block, 'save_locals', [v_retbox])
        else:
            raise AssertionError(self.graph, self.graphcolor)
        self.genop(block, 'save_return', [])

    def insert_enter_graph(self):
        entryblock = self.before_start_block()
        self.genop(entryblock, 'enter_graph', [self.c_mpfamily])

    def insert_leave_graph(self):
        block = self.before_return_block()
        self.genop(block, 'leave_graph_%s' % (self.graphcolor,), [])

    # __________ handling of the various kinds of calls __________

    def graphs_from(self, spaceop):
        if spaceop.opname == 'direct_call':
            c_func = spaceop.args[0]
            fnobj = c_func.value._obj
            graphs = [fnobj.graph]
            args_v = spaceop.args[1:]
        elif spaceop.opname == 'indirect_call':
            graphs = spaceop.args[-1].value
            args_v = spaceop.args[1:-1]
        else:
            raise AssertionError(spaceop.opname)
        for graph in graphs:
            tsgraph = self.timeshifted_graph_of(graph, args_v)
            yield graph, tsgraph

    def guess_call_kind(self, spaceop):
        if spaceop.opname == 'direct_call':
            c_func = spaceop.args[0]
            fnobj = c_func.value._obj
            if hasattr(fnobj._callable, 'oopspec'):
                return 'oopspec'

        for v in spaceop.args:
            hs_arg = self.hannotator.binding(v)
            if not hs_arg.is_green():
                break
        else:
            hs_res = self.hannotator.binding(spaceop.result)
            if hs_res.is_green():
                # all-green arguments and result.
                # Does the function have side-effects?
                t = self.hannotator.base_translator
                if not rec_op_has_side_effects(t, spaceop):
                    return 'green'
        colors = {}
        for graph, tsgraph in self.graphs_from(spaceop):
            color = self.graph_calling_color(tsgraph)
            colors[color] = tsgraph
        assert len(colors) == 1, colors   # buggy normalization?
        return color

    def split_after_calls(self):
        for block in list(self.graph.iterblocks()):
            for i in range(len(block.operations)-1, -1, -1):
                op = block.operations[i]
                if op.opname in ('direct_call', 'indirect_call'):
                    call_kind = self.guess_call_kind(op)
                    handler = getattr(self, 'handle_%s_call' % (call_kind,))
                    handler(block, i)

    def make_call(self, block, op, save_locals_vars, color='red'):
        # the 'save_locals' pseudo-operation is used to save all
        # alive local variables into the current JITState
        self.genop(block, 'save_locals', save_locals_vars)
        targets = dict(self.graphs_from(op))
        for tsgraph in targets.values():
            if self.graph_global_mps(tsgraph):
                # make sure jitstate.resumepoint is set to zero
                self.genop(block, 'resetresumepoint', [])
                break
        args_v = op.args[1:]
        if op.opname == 'indirect_call':
            del args_v[-1]
        if len(targets) == 1:
            [tsgraph] = targets.values()
            c_tsgraph = inputconst(lltype.Void, tsgraph)
            self.genop(block, '%s_call' % (color,), [c_tsgraph] + args_v)
            # Void result, because the call doesn't return its redbox result,
            # but only has the hidden side-effect of putting it in the jitstate
        else:
            c_targets = inputconst(lltype.Void, targets)
            args_v = op.args[:1] + args_v + [c_targets]
            hs_func = self.hannotator.binding(args_v[0])
            if not hs_func.is_green():
                # XXX for now, assume that it will be a constant red box
                v_greenfunc = self.genop(block, 'revealconst', [args_v[0]],
                                  resulttype = originalconcretetype(hs_func))
                args_v[0] = v_greenfunc
            self.genop(block, 'indirect_%s_call' % (color,), args_v)

    def handle_red_call(self, block, pos, color='red'):
        varsalive = self.variables_alive(block, pos+1)
        op = block.operations.pop(pos)
        try:
            varsalive.remove(op.result)
            uses_retval = True      # it will be restored by 'fetch_return'
        except ValueError:
            uses_retval = False
        reds, greens = self.sort_by_color(varsalive)

        nextblock = self.naive_split_block(block, pos)

        v_func = op.args[0]
        hs_func = self.hannotator.binding(v_func)
        if hs_func.is_green():
            constantblock = block
            nonconstantblock = None
            blockset = {}
        else:
            constantblock = Block([])
            nonconstantblock = Block([])
            blockset = {constantblock: False,
                        nonconstantblock: False}
            v_is_constant = self.genop(block, 'is_constant', [v_func],
                                       resulttype = lltype.Bool)
            self.genswitch(block, v_is_constant, true  = constantblock,
                                                 false = nonconstantblock)
            constantblock.closeblock(Link([], nextblock))
            nonconstantblock.closeblock(Link([], nextblock))

        self.make_call(constantblock, op, reds, color)

        mapping = {}
        for i, var in enumerate(reds):
            c_index = Constant(i, concretetype=lltype.Signed)
            newvar = self.genop(constantblock, 'restore_local', [c_index],
                                result_like = var)
            mapping[var] = newvar

        if uses_retval:
            assert not self.hannotator.binding(op.result).is_green()
            var = op.result
            newvar = self.genop(constantblock, 'fetch_return', [],
                                result_like = var)
            mapping[var] = newvar

        nextblock.renamevariables(mapping)

        if nonconstantblock is not None:
            args_v = op.args[1:]
            if op.opname == 'indirect_call':
                del args_v[-1]
            # pseudo-obscure: the arguments for the call go in save_locals
            self.genop(nonconstantblock, 'save_locals', args_v)
            v_res = self.genop(nonconstantblock, 'residual_%s_call' % (color,),
                               [op.args[0]], result_like = op.result)

            oldvars = mapping.keys()
            newvars = [mapping[v] for v in oldvars]
            constantblock.exits[0].args = newvars
            nextblock.inputargs = newvars

            mapping2 = dict([(v, copyvar(self.hannotator, v))
                             for v in newvars])
            nextblock.renamevariables(mapping2)

            mapping3 = {op.result: v_res}
            nonconstantblock.exits[0].args = [mapping3.get(v, v)
                                              for v in oldvars]

        blockset[block] = True    # reachable from outside
        blockset[nextblock] = False
        SSA_to_SSI(blockset, self.hannotator)

    def handle_gray_call(self, block, pos):
        self.handle_red_call(block, pos, color='gray')

    def handle_oopspec_call(self, block, pos):
        op = block.operations[pos]
        assert op.opname == 'direct_call'
        op.opname = 'oopspec_call'

    def handle_green_call(self, block, pos):
        # green-returning call, for now (XXX) we assume it's an
        # all-green function that we can just call
        op = block.operations[pos]
        assert op.opname == 'direct_call'
        op.opname = 'green_call'

    def handle_yellow_call(self, block, pos):
        op = block.operations[pos]
        hs_result = self.hannotator.binding(op.result)
        if not hs_result.is_green():
            # yellow calls are supposed to return greens,
            # add an indirection if it's not the case
            # XXX a bit strange
            RESULT = originalconcretetype(hs_result)
            v_tmp = varoftype(RESULT)
            hs = hintmodel.SomeLLAbstractConstant(RESULT, {})
            self.hannotator.setbinding(v_tmp, hs)
            v_real_result = op.result
            op.result = v_tmp
            newop = SpaceOperation('same_as', [v_tmp], v_real_result)
            block.operations.insert(pos+1, newop)

        link = support.split_block_with_keepalive(block, pos+1,
                                                  annotator=self.hannotator)
        op1 = block.operations.pop(pos)
        assert op1 is op
        assert len(block.operations) == pos
        nextblock = link.target
        varsalive = link.args
        try:
            index = varsalive.index(op.result)
        except ValueError:
            XXX-later

        del varsalive[index]
        v_result = nextblock.inputargs.pop(index)
        nextblock.inputargs.insert(0, v_result)

        reds, greens = self.sort_by_color(varsalive)
        self.make_call(block, op, reds, 'yellow')

        resumepoint = self.get_resume_point(nextblock)
        c_resumepoint = inputconst(lltype.Signed, resumepoint)
        self.genop(block, 'collect_split', [c_resumepoint] + greens)
        link.args = []
        link.target = self.get_resume_point_link(nextblock).target

        self.mergepoint_set[nextblock] = True  # to merge some of the possibly
                                               # many return jitstates

    # __________ hints __________

    def handle_hints(self):
        for block in list(self.graph.iterblocks()):
            for i in range(len(block.operations)-1, -1, -1):
                op = block.operations[i]
                if op.opname == 'hint':
                    hints = op.args[1].value
                    for key, value in hints.items():
                        if value == True:
                            methname = 'handle_%s_hint' % (key,)
                            if hasattr(self, methname):
                                handler = getattr(self, methname)
                                break
                    else:
                        handler = self.handle_default_hint
                    handler(block, i)

    def handle_default_hint(self, block, i):
        # just discard the hint by default
        op = block.operations[i]
        newop = SpaceOperation('same_as', [op.args[0]], op.result)
        block.operations[i] = newop

    def handle_forget_hint(self, block, i):
        # a hint for testing only
        op = block.operations[i]
        assert self.hannotator.binding(op.result).is_green()
        assert not self.hannotator.binding(op.args[0]).is_green()
        newop = SpaceOperation('revealconst', [op.args[0]], op.result)
        block.operations[i] = newop

    def handle_promote_hint(self, block, i):
        op = block.operations[i]
        v_promote = op.args[0]
        newop = SpaceOperation('revealconst', [v_promote], op.result)
        block.operations[i] = newop

        link = support.split_block_with_keepalive(block, i,
                                                  annotator=self.hannotator)
        nextblock = link.target

        reds, greens = self.sort_by_color(link.args)
        self.genop(block, 'save_locals', reds)
        v_finished_flag = self.genop(block, 'promote', [v_promote],
                                     resulttype = lltype.Bool)
        self.go_to_dispatcher_if(block, v_finished_flag)
