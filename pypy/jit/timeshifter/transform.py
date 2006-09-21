from pypy.objspace.flow.model import Variable, Constant, Block, Link
from pypy.objspace.flow.model import SpaceOperation, mkentrymap
from pypy.annotation        import model as annmodel
from pypy.jit.hintannotator import model as hintmodel
from pypy.jit.hintannotator.model import originalconcretetype
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.rmodel import inputconst
from pypy.translator.unsimplify import varoftype, copyvar
from pypy.translator.unsimplify import split_block, split_block_at_start
from pypy.translator.backendopt.ssa import SSA_to_SSI
from pypy.translator.backendopt import support


class MergePointFamily(object):
    def __init__(self):
        self.count = 0
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
        self.resumepoints = {}
        self.mergepointfamily = MergePointFamily()
        self.c_mpfamily = inputconst(lltype.Void, self.mergepointfamily)

    def transform(self):
        mergepoints = list(self.enumerate_merge_points())
        self.insert_save_return()
        self.insert_splits()
        for block in mergepoints:
            self.insert_merge(block)
        self.split_after_calls()
        self.insert_dispatcher()
        self.insert_enter_graph()
        self.insert_leave_graph()

    def enumerate_merge_points(self):
        entrymap = mkentrymap(self.graph)
        for block, links in entrymap.items():
            if len(links) > 1 and block is not self.graph.returnblock:
                yield block

    # __________ helpers __________

    def genop(self, block, opname, args, result_type=None, result_like=None):
        # 'result_type' can be a LowLevelType (for green returns)
        # or a template variable whose hintannotation is copied
        if result_type is not None:
            v_res = varoftype(result_type)
            hs = hintmodel.SomeLLAbstractConstant(result_type, {})
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

    def sort_by_color(self, vars):
        reds = []
        greens = []
        for v in vars:
            if self.hannotator.binding(v).is_green():
                greens.append(v)
            else:
                reds.append(v)
        return reds, greens

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
        v_redswitch = block.exitswitch
        link_f, link_t = block.exits
        if link_f.exitcase:
            link_f, link_t = link_t, link_f
        assert link_f.exitcase is False
        assert link_t.exitcase is True

        constant_block = Block([])
        nonconstant_block = Block([])

        v_flag = self.genop(block, 'is_constant', [v_redswitch],
                            result_type = lltype.Bool)
        self.genswitch(block, v_flag, true  = constant_block,
                                      false = nonconstant_block)

        v_greenswitch = self.genop(constant_block, 'revealconst',
                                   [v_redswitch],
                                   result_type = lltype.Bool)
        constant_block.exitswitch = v_greenswitch
        constant_block.closeblock(link_f, link_t)

        reds, greens = self.sort_by_color(link_f.args)
        self.genop(nonconstant_block, 'save_locals', reds)
        resumepoint = self.get_resume_point(link_f.target)
        c_resumepoint = inputconst(lltype.Signed, resumepoint)
        self.genop(nonconstant_block, 'split',
                   [v_redswitch, c_resumepoint] + greens)

        reds, greens = self.sort_by_color(link_t.args)
        self.genop(nonconstant_block, 'save_locals', reds)
        self.genop(nonconstant_block, 'enter_block', [])
        nonconstant_block.closeblock(Link(link_t.args, link_t.target))

        SSA_to_SSI({block            : True,    # reachable from outside
                    constant_block   : False,
                    nonconstant_block: False}, self.hannotator)

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

    def insert_merge(self, block):
        reds, greens = self.sort_by_color(block.inputargs)
        nextblock = self.naive_split_block(block, 0)

        self.genop(block, 'save_locals', reds)
        mp   = self.mergepointfamily.add()
        c_mp = inputconst(lltype.Void, mp)
        v_finished_flag = self.genop(block, 'merge_point',
                                     [self.c_mpfamily, c_mp] + greens,
                                     result_type = lltype.Bool)
        block.exitswitch = v_finished_flag
        [link_f] = block.exits
        link_t = Link([self.c_dummy], self.graph.returnblock)
        link_f.exitcase = False
        link_t.exitcase = True
        block.recloseblock(link_f, link_t)

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

    def insert_dispatcher(self):
        if self.resumepoints:
            block = self.before_return_block()
            v_switchcase = self.genop(block, 'dispatch_next', [],
                                      result_type = lltype.Signed)
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
        hs_retbox = self.hannotator.binding(v_retbox)
        if originalconcretetype(hs_retbox) is lltype.Void:
            self.leave_graph_opname = 'leave_graph_void'
            self.genop(block, 'save_locals', [])
        elif hs_retbox.is_green():
            self.leave_graph_opname = 'leave_graph_yellow'
            self.genop(block, 'save_greens', [v_retbox])
        else:
            self.leave_graph_opname = 'leave_graph_red'
            self.genop(block, 'save_locals', [v_retbox])
        self.genop(block, 'save_return', [])

    def insert_enter_graph(self):
        entryblock = self.new_block_before(self.graph.startblock)
        entryblock.isstartblock = True
        self.graph.startblock.isstartblock = False
        self.graph.startblock = entryblock

        self.genop(entryblock, 'enter_graph', [self.c_mpfamily])

    def insert_leave_graph(self):
        block = self.before_return_block()
        self.genop(block, self.leave_graph_opname, [])

    # __________ handling of the various kinds of calls __________

    def guess_call_kind(self, spaceop):
        if spaceop.opname == 'indirect_call':
            return 'red'  # for now
        assert spaceop.opname == 'direct_call'
        c_func = spaceop.args[0]
        fnobj = c_func.value._obj
        s_result = self.hannotator.binding(spaceop.result)
        if hasattr(fnobj._callable, 'oopspec'):
            return 'oopspec'
        elif (originalconcretetype(s_result) is not lltype.Void and
              s_result.is_green()):
            for v in spaceop.args:
                s_arg = self.hannotator.binding(v)
                if not s_arg.is_green():
                    return 'yellow'
            return 'green'
        else:
            return 'red'

    def split_after_calls(self):
        for block in list(self.graph.iterblocks()):
            for i in range(len(block.operations)-1, -1, -1):
                op = block.operations[i]
                if op.opname in ('direct_call', 'indirect_call'):
                    call_kind = self.guess_call_kind(op)
                    handler = getattr(self, 'handle_%s_call' % (call_kind,))
                    handler(block, i)

    def handle_red_call(self, block, pos):
        # the 'save_locals' pseudo-operation is used to save all
        # alive local variables into the current JITState
        beforeops = block.operations[:pos]
        op        = block.operations[pos]
        afterops  = block.operations[pos+1:]

        varsalive = self.variables_alive(block, pos+1)
        try:
            varsalive.remove(op.result)
            uses_retval = True      # it will be restored by 'fetch_return'
        except ValueError:
            uses_retval = False
        reds, greens = self.sort_by_color(varsalive)

        newops = []
        self.genop(newops, 'save_locals', reds)
        self.genop(newops, 'red_call', op.args)    # Void result,
        # because the call doesn't return its redbox result, but only
        # has the hidden side-effect of putting it in the jitstate
        mapping = {}
        for i, var in enumerate(reds):
            c_index = Constant(i, concretetype=lltype.Signed)
            newvar = self.genop(newops, 'restore_local', [c_index],
                                result_like = var)
            mapping[var] = newvar

        if uses_retval and not self.hannotator.binding(op.result).is_green():
            var = op.result
            newvar = self.genop(newops, 'fetch_return', [],
                                result_like = var)
            mapping[var] = newvar

        saved = block.inputargs
        block.inputargs = []     # don't rename these!
        block.operations = afterops
        block.renamevariables(mapping)
        block.inputargs = saved
        block.operations[:0] = beforeops + newops

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
        link = support.split_block_with_keepalive(block, pos+1,
                                                  annotator=self.hannotator)
        op = block.operations.pop(pos)
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
        self.genop(block, 'save_locals', reds)
        self.genop(block, 'yellow_call', op.args)  # Void result, like red_call

        resumepoint = self.get_resume_point(nextblock)
        c_resumepoint = inputconst(lltype.Signed, resumepoint)
        self.genop(block, 'collect_split', [c_resumepoint] + greens)
        link.args = []
        link.target = self.get_resume_point_link(nextblock).target

        self.insert_merge(nextblock)  # to merge some of the possibly many
                                      # return jitstates
