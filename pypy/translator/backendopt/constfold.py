from pypy.objspace.flow.model import Constant, Variable, SpaceOperation
from pypy.objspace.flow.model import c_last_exception
from pypy.translator.backendopt.support import split_block_with_keepalive
from pypy.translator.backendopt.support import log
from pypy.translator.simplify import eliminate_empty_blocks
from pypy.translator.unsimplify import insert_empty_block
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rpython.lltypesystem import lltype


def fold_op_list(operations, constants, exit_early=False, exc_catch=False):
    newops = []
    keepalives = []
    folded_count = 0
    first_sideeffect_index = None
    for spaceop in operations:
        vargsmodif = False
        vargs = []
        args = []
        for v in spaceop.args:
            if isinstance(v, Constant):
                args.append(v.value)
            elif v in constants:
                v = constants[v]
                vargsmodif = True
                args.append(v.value)
            vargs.append(v)
        try:
            op = getattr(llop, spaceop.opname)
        except AttributeError:
            sideeffects = True
        else:
            if len(args) == len(vargs):
                RESTYPE = spaceop.result.concretetype
                try:
                    result = op(RESTYPE, *args)
                except TypeError:
                    pass
                except (KeyboardInterrupt, SystemExit):
                    raise
                except Exception, e:
                    log.WARNING('constant-folding %r:' % (spaceop,))
                    log.WARNING('  %s: %s' % (e.__class__.__name__, e))
                else:
                    # success in folding this space operation
                    constants[spaceop.result] = Constant(result, RESTYPE)
                    folded_count += 1
                    continue
            sideeffects = op.sideeffects
        # failed to fold an operation, exit early if requested
        if exit_early:
            return folded_count
        if spaceop.opname == 'keepalive' and first_sideeffect_index is None:
            if vargsmodif:
                continue    # keepalive(constant) is not useful
            keepalives.append(spaceop)
        else:
            if vargsmodif:
                if (spaceop.opname == 'indirect_call'
                    and isinstance(vargs[0], Constant)):
                    spaceop = SpaceOperation('direct_call', vargs[:-1],
                                             spaceop.result)
                else:
                    spaceop = SpaceOperation(spaceop.opname, vargs,
                                             spaceop.result)
            if sideeffects and first_sideeffect_index is None:
                first_sideeffect_index = len(newops)
            newops.append(spaceop)
    # end
    if exit_early:
        return folded_count
    else:
        # move the keepalives to the end of the block, which makes the life
        # of prepare_constant_fold_link() easier.  Don't put them past the
        # exception-raising operation, though.  There is also no point in
        # moving them past the first sideeffect-ing operation.
        if first_sideeffect_index is None:
            first_sideeffect_index = len(newops) - exc_catch
        newops[first_sideeffect_index:first_sideeffect_index] = keepalives
        return newops

def constant_fold_block(block):
    constants = {}
    block.operations = fold_op_list(block.operations, constants,
                           exc_catch = block.exitswitch == c_last_exception)
    if constants:
        if block.exitswitch in constants:
            switch = constants[block.exitswitch].value
            remaining_exits = [link for link in block.exits
                                    if link.llexitcase == switch]
            assert len(remaining_exits) == 1
            remaining_exits[0].exitcase = None
            remaining_exits[0].llexitcase = None
            block.exitswitch = None
            block.recloseblock(*remaining_exits)
        for link in block.exits:
            link.args = [constants.get(v, v) for v in link.args]


def complete_constants(link, constants):
    # 'constants' maps some Variables of 'block' to Constants.
    # Some input args of 'block' may be absent from 'constants'
    # and must be fixed in the link to be passed directly from
    # 'link.prevblock' instead of via 'block'.
    for v1, v2 in zip(link.args, link.target.inputargs):
        if v2 in constants:
            assert constants[v2] is v1
        else:
            constants[v2] = v1

def prepare_constant_fold_link(link, constants, splitblocks):
    block = link.target
    folded_count = fold_op_list(block.operations, constants, exit_early=True)

    n = len(block.operations)
    if block.exitswitch == c_last_exception:
        n -= 1
    # is the next, non-folded operation an indirect_call?
    m = folded_count
    while m < n and block.operations[m].opname == 'keepalive':
        m += 1
    if m < n:
        nextop = block.operations[m]
        if nextop.opname == 'indirect_call' and nextop.args[0] in constants:
            # indirect_call -> direct_call
            callargs = [constants[nextop.args[0]]]
            constants1 = constants.copy()
            complete_constants(link, constants1)
            newkeepalives = []
            for i in range(folded_count, m):
                [v] = block.operations[i].args
                v = constants1.get(v, v)
                v_void = Variable()
                v_void.concretetype = lltype.Void
                newkeepalives.append(SpaceOperation('keepalive', [v], v_void))
            for v in nextop.args[1:-1]:
                callargs.append(constants1.get(v, v))
            v_result = Variable(nextop.result)
            v_result.concretetype = nextop.result.concretetype
            constants[nextop.result] = v_result
            callop = SpaceOperation('direct_call', callargs, v_result)
            newblock = insert_empty_block(None, link, newkeepalives + [callop])
            [link] = newblock.exits
            assert link.target is block
            folded_count = m+1

    if folded_count > 0:
        splits = splitblocks.setdefault(block, [])
        splits.append((folded_count, link, constants))

def rewire_links(splitblocks, graph):
    for block, splits in splitblocks.items():
        # A splitting position is given by how many operations were
        # folded with the knowledge of an incoming link's constant.
        # Various incoming links may cause various splitting positions.
        # We split the block gradually, starting from the end.
        splits.sort()
        splits.reverse()
        for position, link, constants in splits:
            assert link.target is block
            if position == len(block.operations) and block.exitswitch is None:
                # a split here would leave nothing in the 2nd part, so
                # directly rewire the links
                assert len(block.exits) == 1
                splitlink = block.exits[0]
            else:
                # split the block at the given position
                splitlink = split_block_with_keepalive(block, position)
                assert block.exits == [splitlink]
            assert link.target is block
            assert splitlink.prevblock is block
            complete_constants(link, constants)
            args = [constants.get(v, v) for v in splitlink.args]
            link.args = args
            link.target = splitlink.target


def constant_fold_graph(graph):
    # first fold inside the blocks
    for block in graph.iterblocks():
        if block.operations:
            constant_fold_block(block)
    # then fold along the links - a fixpoint process, because new links
    # with new constants show up, even though we can probably prove that
    # a single iteration is enough under some conditions, like the graph
    # is in a join_blocks() form.
    while 1:
        splitblocks = {}
        for link in list(graph.iterlinks()):
            constants = {}
            for v1, v2 in zip(link.args, link.target.inputargs):
                if isinstance(v1, Constant):
                    constants[v2] = v1
            if constants:
                prepare_constant_fold_link(link, constants, splitblocks)
        if not splitblocks:
            break   # finished
        rewire_links(splitblocks, graph)
