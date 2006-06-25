from pypy.objspace.flow.model import Constant, Variable, SpaceOperation
from pypy.translator.backendopt.support import split_block_with_keepalive
from pypy.translator.simplify import eliminate_empty_blocks
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rpython.lltypesystem import lltype


def fold_op_list(operations, constants, exit_early=False):
    newops = []
    folded_count = 0
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
        if len(args) == len(vargs):
            RESTYPE = spaceop.result.concretetype
            op = getattr(llop, spaceop.opname)
            try:
                result = op(RESTYPE, *args)
            except TypeError:
                pass
            else:
                # success in folding this space operation
                constants[spaceop.result] = Constant(result, RESTYPE)
                folded_count += 1
                continue
        # failed to fold an operation, exit early if requested
        if exit_early:
            return folded_count
        if vargsmodif:
            spaceop = SpaceOperation(spaceop.opname, vargs, spaceop.result)
        newops.append(spaceop)
    # end
    if exit_early:
        return folded_count
    else:
        return newops

def constant_fold_block(block):
    constants = {}
    block.operations = fold_op_list(block.operations, constants)
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

def prepare_constant_fold_link(link, constants, splitblocks):
    folded_count = fold_op_list(link.target.operations, constants,
                                exit_early=True)
    if folded_count > 0:
        splits = splitblocks.setdefault(link.target, [])
        splits.append((folded_count, link, constants))

def rewire_links(splitblocks):
    for block, splits in splitblocks.items():
        # A splitting position is given by how many operations were
        # folded with the knowledge of an incoming link's constant.
        # Various incoming links may cause various splitting positions.
        # We split the block gradually, starting from the end.
        splits.sort()
        splits.reverse()
        for position, link, constants in splits:
            if position == len(block.operations) and block.exitswitch is None:
                # a split here would leave nothing in the 2nd part, so
                # directly rewire the links
                assert len(block.exits) == 1
                splitlink = block.exits[0]
            else:
                # split the block at the given position
                splitlink = split_block_with_keepalive(block, position)
                assert block.exits == [splitlink]
            # 'constants' maps some Variables of 'block' to Constants.
            # Some input args of 'block' may be absent from 'constants'
            # and must be fixed in the link to be passed directly from
            # the origin of the link instead of via 'block'.
            for v1, v2 in zip(link.args, link.target.inputargs):
                constants.setdefault(v2, v1)
            args = [constants.get(v, v) for v in splitlink.args]
            link.args = args
            link.target = splitlink.target


def constant_fold_graph(graph):
    # first fold inside the blocks
    for block in graph.iterblocks():
        if block.operations:
            constant_fold_block(block)
    # then fold along the links - a fixpoint process, because new links
    # with new constants show up
    while 1:
        splitblocks = {}
        for link in graph.iterlinks():
            constants = {}
            for v1, v2 in zip(link.args, link.target.inputargs):
                if isinstance(v1, Constant):
                    constants[v2] = v1
            if constants:
                prepare_constant_fold_link(link, constants, splitblocks)
        if not splitblocks:
            break   # finished
        rewire_links(splitblocks)
