from rpython.flowspace.model import (Constant, Variable, SpaceOperation,
    mkentrymap, c_last_exception, copygraph, summary)
from rpython.rtyper.lltypesystem import lltype
from rpython.rtyper.lltypesystem.lloperation import llop
from rpython.translator.unsimplify import insert_empty_block, split_block
from rpython.translator import simplify
from rpython.rlib import rarithmetic


def fold_op_list(block, constants, exit_early=False, exc_catch=False):
    operations = block.operations
    newops = []
    folded_count = 0
    for index, spaceop in enumerate(operations):
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
            pass
        else:
            if not op.sideeffects and len(args) == len(vargs):
                RESTYPE = spaceop.result.concretetype
                try:
                    result = op(RESTYPE, *args)
                except TypeError:
                    pass
                except (KeyboardInterrupt, SystemExit):
                    raise
                except Exception:
                    pass   # turn off reporting these as warnings: useless
                    #log.WARNING('constant-folding %r:' % (spaceop,))
                    #log.WARNING('  %s: %s' % (e.__class__.__name__, e))
                else:
                    # success in folding this space operation
                    if spaceop.opname in fixup_op_result:
                        result = fixup_op_result[spaceop.opname](result)
                    constants[spaceop.result] = Constant(result, RESTYPE)
                    folded_count += 1
                    continue
            if (index == len(operations) - 1 and
                    block.exitswitch == c_last_exception and
                    len(args) == len(vargs) == 2 and
                    spaceop.opname.endswith("_ovf") and not exit_early):
                # deal with int_add_ovf etc but only if exit_early is False
                RESTYPE = spaceop.result.concretetype
                result = fold_ovf_op(spaceop, args)
                if result is None:
                    # always overflows, remove op and link
                    block.exitswitch = None
                    assert block.exits[1].exitcase is OverflowError
                    block.exits[1].exitcase = None
                    block.exits[1].last_exception = None
                    block.exits[1].last_exc_value = None
                    block.recloseblock(block.exits[1])
                    folded_count += 1
                    continue
                else:
                    block.exitswitch = None
                    block.recloseblock(block.exits[0])
                    constants[spaceop.result] = Constant(result, RESTYPE)
                    folded_count += 1
                    continue
        # failed to fold an operation, exit early if requested
        if exit_early:
            return folded_count
        else:
            if vargsmodif:
                if (spaceop.opname == 'indirect_call'
                    and isinstance(vargs[0], Constant)):
                    spaceop = SpaceOperation('direct_call', vargs[:-1],
                                             spaceop.result)
                else:
                    spaceop = SpaceOperation(spaceop.opname, vargs,
                                             spaceop.result)
            newops.append(spaceop)
    # end
    if exit_early:
        return folded_count
    else:
        return newops

def fold_ovf_op(spaceop, args):
    a, b = args
    try:
        if spaceop.opname in ("int_add_ovf", "int_add_nonneg_ovf"):
            return rarithmetic.ovfcheck(a + b)
        elif spaceop.opname == "int_sub_ovf":
            return rarithmetic.ovfcheck(a - b)
        else:
            assert spaceop.opname == "int_mul_ovf"
            return rarithmetic.ovfcheck(a * b)
    except OverflowError:
        return None
    assert 0, "unreachable"

def constant_fold_block(block):
    constants = {}
    block.operations = fold_op_list(block, constants,
                                    exc_catch=block.canraise)
    if constants:
        if block.exitswitch in constants:
            switch = constants[block.exitswitch].value
            remaining_exits = [link for link in block.exits
                                    if link.llexitcase == switch]
            if not remaining_exits:
                assert block.exits[-1].exitcase == 'default'
                remaining_exits = [block.exits[-1]]
            assert len(remaining_exits) == 1
            remaining_exits[0].exitcase = None
            remaining_exits[0].llexitcase = None
            block.exitswitch = None
            block.recloseblock(*remaining_exits)
        for link in block.exits:
            link.args = [constants.get(v, v) for v in link.args]


def fixup_solid(p):
    # Operations returning pointers to inlined parts of a constant object
    # have to be tweaked so that the inlined part keeps the whole object alive.
    # XXX This is done with a hack.  (See test_keepalive_const_*())
    container = p._obj
    assert isinstance(container, lltype._parentable)
    container._keepparent = container._parentstructure()
    # Instead of 'p', return a solid pointer, to keep the inlined part
    # itself alive.
    return container._as_ptr()

fixup_op_result = {
    "getsubstruct":      fixup_solid,
    "getarraysubstruct": fixup_solid,
    "direct_fieldptr":   fixup_solid,
    "direct_arrayitems": fixup_solid,
    }


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

def rewire_link_for_known_exitswitch(link1, llexitvalue):
    # For the case where link1.target contains only a switch, rewire link1
    # to go directly to the correct exit based on a constant switch value.
    # This is a situation that occurs typically after inlining; see
    # test_fold_exitswitch_along_one_path.
    block = link1.target
    if block.exits[-1].exitcase == "default":
        defaultexit = block.exits[-1]
        nondefaultexits = block.exits[:-1]
    else:
        defaultexit = None
        nondefaultexits = block.exits
    for nextlink in nondefaultexits:
        if nextlink.llexitcase == llexitvalue:
            break   # found -- the result is in 'nextlink'
    else:
        if defaultexit is None:
            return    # exit case not found!  just ignore the problem here
        nextlink = defaultexit
    blockmapping = dict(zip(block.inputargs, link1.args))
    newargs = []
    for v in nextlink.args:
        if isinstance(v, Variable):
            v = blockmapping[v]
        newargs.append(v)
    link1.target = nextlink.target
    link1.args = newargs

def prepare_constant_fold_link(link, constants, splitblocks):
    block = link.target
    if not block.operations:
        # when the target block has no operation, there is nothing we can do
        # except trying to fold an exitswitch
        if block.exitswitch is not None and block.exitswitch in constants:
            llexitvalue = constants[block.exitswitch].value
            rewire_link_for_known_exitswitch(link, llexitvalue)
        return

    folded_count = fold_op_list(block, constants, exit_early=True)

    n = len(block.operations)
    if block.canraise:
        n -= 1
    # is the next, non-folded operation an indirect_call?
    if folded_count < n:
        nextop = block.operations[folded_count]
        if nextop.opname == 'indirect_call' and nextop.args[0] in constants:
            # indirect_call -> direct_call
            callargs = [constants[nextop.args[0]]]
            constants1 = constants.copy()
            complete_constants(link, constants1)
            for v in nextop.args[1:-1]:
                callargs.append(constants1.get(v, v))
            v_result = Variable(nextop.result)
            v_result.concretetype = nextop.result.concretetype
            constants[nextop.result] = v_result
            callop = SpaceOperation('direct_call', callargs, v_result)
            newblock = insert_empty_block(link, [callop])
            [link] = newblock.exits
            assert link.target is block
            folded_count += 1

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
                splitlink = split_block(block, position)
                assert list(block.exits) == [splitlink]
            assert link.target is block
            assert splitlink.prevblock is block
            complete_constants(link, constants)
            args = [constants.get(v, v) for v in splitlink.args]
            link.args = args
            link.target = splitlink.target


def constant_diffuse(graph):
    count = 0
    # after 'exitswitch vexit', replace 'vexit' with the corresponding constant
    # if it also appears on the outgoing links
    for block in graph.iterblocks():
        vexit = block.exitswitch
        if isinstance(vexit, Variable):
            for link in block.exits:
                if vexit in link.args and link.exitcase != 'default':
                    remap = {vexit: Constant(link.llexitcase,
                                             vexit.concretetype)}
                    link.args = [remap.get(v, v) for v in link.args]
                    count += 1
    # if the same constants appear at the same positions in all links
    # into a block remove them from the links, remove the corresponding
    # input variables and introduce equivalent same_as at the beginning
    # of the block then try to fold the block further
    for block, links in mkentrymap(graph).iteritems():
        if block is graph.startblock:
            continue
        if block.exits == ():
            continue
        firstlink = links[0]
        rest = links[1:]
        diffuse = []
        for i, c in enumerate(firstlink.args):
            if not isinstance(c, Constant):
                continue
            for lnk in rest:
                if not same_constant(lnk.args[i], c):
                    break
            else:
                diffuse.append((i, c))
        diffuse.reverse()
        same_as = []
        for i, c in diffuse:
            for lnk in links:
                del lnk.args[i]
            v = block.inputargs.pop(i)
            same_as.append(SpaceOperation('same_as', [c], v))
            count += 1
        block.operations = same_as + block.operations
        if same_as:
            constant_fold_block(block)
    return count

def same_constant(c1, c2):
    # concretype must be the same, the values flow into the same place
    assert c1.concretetype == c2.concretetype
    if not isinstance(c1, Constant) or not isinstance(c2, Constant):
        return False
    TYPE = c1.concretetype
    if isinstance(TYPE, lltype.Ptr) and TYPE.TO._gckind == 'gc':
        return c1.value == c2.value
    return c1 == c2

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
        diffused = constant_diffuse(graph)
        splitblocks = {}
        for link in list(graph.iterlinks()):
            constants = {}
            for v1, v2 in zip(link.args, link.target.inputargs):
                if isinstance(v1, Constant):
                    constants[v2] = v1
            if constants:
                lastop = link.target.operations[-1] if link.target.operations else None
                ovfflow_block =  (len(link.target.operations) == 1 and link.target.canraise
                        and lastop and lastop.opname.endswith("_ovf"))
                if not ovfflow_block:
                    # normal case
                    prepare_constant_fold_link(link, constants, splitblocks)
                    continue
                # need to treat the ovf case specially here
                constargs = []
                for arg in lastop.args:
                    if isinstance(arg, Constant):
                        constargs.append(arg.value)
                    elif arg in constants:
                        constargs.append(constants[arg].value)
                    else:
                        break
                else:
                    # can fold
                    res = fold_ovf_op(lastop, constargs)
                    if res is None:
                        # always overflows
                        targetlink = link.target.exits[1]
                        assert targetlink.exitcase is OverflowError
                    else:
                        # doesn't overflow
                        targetlink = link.target.exits[0]
                        assert targetlink.exitcase is None
                        constants[lastop.result] = Constant(res, lastop.result.concretetype)
                    complete_constants(link, constants)
                    link.args = [constants.get(v, v) for v in targetlink.args]
                    link.target = targetlink.target
        if splitblocks:
            rewire_links(splitblocks, graph)
        if not diffused and not splitblocks:
            break # finished
        simplify.eliminate_empty_blocks(graph)
        simplify.join_blocks(graph)

def replace_symbolic(graph, symbolic, value):
    result = False
    for block in graph.iterblocks():
        for op in block.operations:
            for i, arg in enumerate(op.args):
                if isinstance(arg, Constant) and arg.value is symbolic:
                    op.args[i] = value
                    result = True
        if block.exitswitch is symbolic:
            block.exitswitch = value
            result = True
    return result

def replace_we_are_jitted(graph):
    from rpython.rlib import jit
    replacement = Constant(0)
    replacement.concretetype = lltype.Signed
    did_replacement = replace_symbolic(graph, jit._we_are_jitted, replacement)
    if did_replacement:
        constant_fold_graph(graph)
    return did_replacement


