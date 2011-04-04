"""Flow Graph Simplification

'Syntactic-ish' simplifications on a flow graph.

simplify_graph() applies all simplifications defined in this file.
"""

import py
from pypy.objspace.flow import operation
from pypy.objspace.flow.model import (SpaceOperation, Variable, Constant, Block,
                                      Link, c_last_exception, checkgraph,
                                      mkentrymap)
from pypy.rlib import rarithmetic
from pypy.translator import unsimplify
from pypy.translator.backendopt import ssa
from pypy.rpython.lltypesystem import lloperation, lltype
from pypy.rpython.ootypesystem import ootype

def get_funcobj(func):
    """
    Return an object which is supposed to have attributes such as graph and
    _callable
    """
    if hasattr(func, '_obj'): 
        return func._obj # lltypesystem
    else:
        return func # ootypesystem

def get_functype(TYPE):
    if isinstance(TYPE, lltype.Ptr):
        return TYPE.TO
    elif isinstance(TYPE, (ootype.StaticMethod, ootype.ForwardReference)):
        return TYPE
    assert False

def get_graph(arg, translator):
    if isinstance(arg, Variable):
        return None
    f = arg.value
    if not isinstance(f, lltype._ptr) and not isinstance(f, ootype._callable):
        return None
    funcobj = get_funcobj(f)
    try:
        callable = funcobj._callable
    except (AttributeError, KeyError, AssertionError):
        return None
    try:
        return funcobj.graph
    except AttributeError:
        return None
    try:
        callable = funcobj._callable
        return translator._graphof(callable)
    except (AttributeError, KeyError, AssertionError):
        return None


def replace_exitswitch_by_constant(block, const):
    assert isinstance(const, Constant)
    assert const != c_last_exception
    newexits = [link for link in block.exits
                     if link.exitcase == const.value]
    if len(newexits) == 0:
        newexits = [link for link in block.exits
                     if link.exitcase == 'default']
    assert len(newexits) == 1
    newexits[0].exitcase = None
    if hasattr(newexits[0], 'llexitcase'):
        newexits[0].llexitcase = None
    block.exitswitch = None
    block.recloseblock(*newexits)
    return newexits

# ____________________________________________________________

def desugar_isinstance(graph):
    """Replace isinstance operation with a call to isinstance."""
    constant_isinstance = Constant(isinstance)
    for block in graph.iterblocks():
        for i in range(len(block.operations) - 1, -1, -1):
            op = block.operations[i]
            if op.opname == "isinstance":
                args = [constant_isinstance, op.args[0], op.args[1]]
                new_op = SpaceOperation("simple_call", args, op.result)
                block.operations[i] = new_op

def eliminate_empty_blocks(graph):
    """Eliminate basic blocks that do not contain any operations.
    When this happens, we need to replace the preceeding link with the
    following link.  Arguments of the links should be updated."""
    for link in list(graph.iterlinks()):
            while not link.target.operations:
                block1 = link.target
                if block1.exitswitch is not None:
                    break
                if not block1.exits:
                    break
                exit = block1.exits[0]
                assert block1 is not exit.target, (
                    "the graph contains an empty infinite loop")
                outputargs = []
                for v in exit.args:
                    if isinstance(v, Variable):
                        # this variable is valid in the context of block1
                        # but it must come from 'link'
                        i = block1.inputargs.index(v)
                        v = link.args[i]
                    outputargs.append(v)
                link.args = outputargs
                link.target = exit.target
                # the while loop above will simplify recursively the new link

def transform_ovfcheck(graph):
    """The special function calls ovfcheck and ovfcheck_lshift need to
    be translated into primitive operations. ovfcheck is called directly
    after an operation that should be turned into an overflow-checked
    version. It is considered a syntax error if the resulting <op>_ovf
    is not defined in objspace/flow/objspace.py.
    ovfcheck_lshift is special because there is no preceding operation.
    Instead, it will be replaced by an OP_LSHIFT_OVF operation.
    """
    covf = Constant(rarithmetic.ovfcheck)
    covfls = Constant(rarithmetic.ovfcheck_lshift)

    def check_syntax(opname):
        exlis = operation.implicit_exceptions.get("%s_ovf" % (opname,), [])
        if OverflowError not in exlis:
            raise Exception("ovfcheck in %s: Operation %s has no"
                            " overflow variant" % (graph.name, opname))

    for block in graph.iterblocks():
        for i in range(len(block.operations)-1, -1, -1):
            op = block.operations[i]
            if op.opname != 'simple_call':
                continue
            if op.args[0] == covf:
                if i == 0:
                    # hard case: ovfcheck() on an operation that occurs
                    # in the previous block, like 'floordiv'.  The generic
                    # exception handling around the ovfcheck() is enough
                    # to cover all cases; kill the one around the previous op.
                    entrymap = mkentrymap(graph)
                    links = entrymap[block]
                    assert len(links) == 1
                    prevblock = links[0].prevblock
                    assert prevblock.exits[0].target is block
                    prevblock.exitswitch = None
                    prevblock.exits = (links[0],)
                    join_blocks(graph)         # merge the two blocks together
                    transform_ovfcheck(graph)  # ...and try again
                    return
                op1 = block.operations[i-1]
                check_syntax(op1.opname)
                op1.opname += '_ovf'
                del block.operations[i]
                block.renamevariables({op.result: op1.result})
            elif op.args[0] == covfls:
                op.opname = 'lshift_ovf'
                del op.args[0]

def simplify_exceptions(graph):
    """The exception handling caused by non-implicit exceptions
    starts with an exitswitch on Exception, followed by a lengthy
    chain of is_/issubtype tests. We collapse them all into
    the block's single list of exits.
    """
    clastexc = c_last_exception
    renaming = {}
    def rename(v):
        return renaming.get(v, v)

    for block in graph.iterblocks():
        if not (block.exitswitch == clastexc
                and block.exits[-1].exitcase is Exception):
            continue
        covered = [link.exitcase for link in block.exits[1:-1]]
        seen = []
        preserve = list(block.exits[:-1])
        exc = block.exits[-1]
        last_exception = exc.last_exception
        last_exc_value = exc.last_exc_value
        query = exc.target
        switches = []
        # collect the targets
        while len(query.exits) == 2:
            newrenaming = {}
            for lprev, ltarg in zip(exc.args, query.inputargs):
                newrenaming[ltarg] = rename(lprev)
            op = query.operations[0]
            if not (op.opname in ("is_", "issubtype") and
                    newrenaming.get(op.args[0]) == last_exception):
                break
            renaming.update(newrenaming)
            case = query.operations[0].args[-1].value
            assert issubclass(case, py.builtin.BaseException)
            lno, lyes = query.exits
            assert lno.exitcase == False and lyes.exitcase == True
            if case not in seen:
                is_covered = False
                for cov in covered:
                    if issubclass(case, cov):
                        is_covered = True
                        break
                if not is_covered:
                    switches.append( (case, lyes) )
                seen.append(case)
            exc = lno
            query = exc.target
        if Exception not in seen:
            switches.append( (Exception, exc) )
        # construct the block's new exits
        exits = []
        for case, oldlink in switches:
            link = oldlink.copy(rename)
            assert case is not None
            link.last_exception = last_exception
            link.last_exc_value = last_exc_value
            # make the above two variables unique
            renaming2 = {}
            def rename2(v):
                return renaming2.get(v, v)
            for v in link.getextravars():
                renaming2[v] = Variable(v)
            link = link.copy(rename2)
            link.exitcase = case
            link.prevblock = block
            exits.append(link)
        block.recloseblock(*(preserve + exits))

def transform_xxxitem(graph):
    # xxx setitem too
    for block in graph.iterblocks():
        if block.operations and block.exitswitch == c_last_exception:
            last_op = block.operations[-1]
            if last_op.opname == 'getitem':
                postfx = []
                for exit in block.exits:
                    if exit.exitcase is IndexError:
                        postfx.append('idx')
                    elif exit.exitcase is KeyError:
                        postfx.append('key')
                if postfx:
                    last_op.opname = last_op.opname + '_' + '_'.join(postfx)


def remove_dead_exceptions(graph):
    """Exceptions can be removed if they are unreachable"""

    clastexc = c_last_exception

    def issubclassofmember(cls, seq):
        for member in seq:
            if member and issubclass(cls, member):
                return True
        return False

    for block in list(graph.iterblocks()):
        if block.exitswitch != clastexc:
            continue
        exits = []
        seen = []
        for link in block.exits:
            case = link.exitcase
            # check whether exceptions are shadowed
            if issubclassofmember(case, seen):
                continue
            # see if the previous case can be merged
            while len(exits) > 1:
                prev = exits[-1]
                if not (issubclass(prev.exitcase, link.exitcase) and
                    prev.target is link.target and prev.args == link.args):
                    break
                exits.pop()
            exits.append(link)
            seen.append(case)
        block.recloseblock(*exits)

def join_blocks(graph):
    """Links can be deleted if they are the single exit of a block and
    the single entry point of the next block.  When this happens, we can
    append all the operations of the following block to the preceeding
    block (but renaming variables with the appropriate arguments.)
    """
    entrymap = mkentrymap(graph)
    block = graph.startblock
    seen = {block: True}
    stack = list(block.exits)
    while stack:
        link = stack.pop()
        if (link.prevblock.exitswitch is None and
            len(entrymap[link.target]) == 1 and
            link.target.exits):  # stop at the returnblock
            assert len(link.prevblock.exits) == 1
            renaming = {}
            for vprev, vtarg in zip(link.args, link.target.inputargs):
                renaming[vtarg] = vprev
            def rename(v):
                return renaming.get(v, v)
            def rename_op(op):
                args = [rename(a) for a in op.args]
                op = SpaceOperation(op.opname, args, rename(op.result), op.offset)
                # special case...
                if op.opname == 'indirect_call':
                    if isinstance(op.args[0], Constant):
                        assert isinstance(op.args[-1], Constant)
                        del op.args[-1]
                        op.opname = 'direct_call'
                return op
            for op in link.target.operations:
                link.prevblock.operations.append(rename_op(op))
            exits = []
            for exit in link.target.exits:
                newexit = exit.copy(rename)
                exits.append(newexit)
            newexitswitch = rename(link.target.exitswitch)
            link.prevblock.exitswitch = newexitswitch
            link.prevblock.recloseblock(*exits)
            if isinstance(newexitswitch, Constant) and newexitswitch != c_last_exception:
                exits = replace_exitswitch_by_constant(link.prevblock,
                                                       newexitswitch)
            stack.extend(exits)
        else:
            if link.target not in seen:
                stack.extend(link.target.exits)
                seen[link.target] = True

def remove_assertion_errors(graph):
    """Remove branches that go directly to raising an AssertionError,
    assuming that AssertionError shouldn't occur at run-time.  Note that
    this is how implicit exceptions are removed (see _implicit_ in
    flowcontext.py).
    """
    for block in list(graph.iterblocks()):
            for i in range(len(block.exits)-1, -1, -1):
                exit = block.exits[i]
                if not (exit.target is graph.exceptblock and
                        exit.args[0] == Constant(AssertionError)):
                    continue
                # can we remove this exit without breaking the graph?
                if len(block.exits) < 2:
                    break
                if block.exitswitch == c_last_exception:
                    if exit.exitcase is None:
                        break
                    if len(block.exits) == 2:
                        # removing the last non-exceptional exit
                        block.exitswitch = None
                        exit.exitcase = None
                # remove this exit
                lst = list(block.exits)
                del lst[i]
                block.recloseblock(*lst)


# _____________________________________________________________________
# decide whether a function has side effects

def op_has_side_effects(op):
    return lloperation.LL_OPERATIONS[op.opname].sideeffects

def has_no_side_effects(translator, graph, seen=None):
    #is the graph specialized? if no we can't say anything
    #don't cache the result though
    if translator.rtyper is None:
        return False
    else:
        if graph.startblock not in translator.rtyper.already_seen:
            return False
    if seen is None:
        seen = {}
    elif graph in seen:
        return True
    newseen = seen.copy()
    newseen[graph] = True
    for block in graph.iterblocks():
        if block is graph.exceptblock:
            return False     # graphs explicitly raising have side-effects
        for op in block.operations:
            if rec_op_has_side_effects(translator, op, newseen):
                return False
    return True

def rec_op_has_side_effects(translator, op, seen=None):
    if op.opname == "direct_call":
        g = get_graph(op.args[0], translator)
        if g is None:
            return True
        if not has_no_side_effects(translator, g, seen):
            return True
    elif op.opname == "indirect_call":
        graphs = op.args[-1].value
        if graphs is None:
            return True
        for g in graphs:
            if not has_no_side_effects(translator, g, seen):
                return True
    else:
        return op_has_side_effects(op)

# ___________________________________________________________________________
# remove operations if their result is not used and they have no side effects

def transform_dead_op_vars(graph, translator=None):
    """Remove dead operations and variables that are passed over a link
    but not used in the target block. Input is a graph."""
    return transform_dead_op_vars_in_blocks(list(graph.iterblocks()), translator)

# the set of operations that can safely be removed
# (they have no side effects, at least in R-Python)
CanRemove = {}
for _op in '''
        newtuple newlist newdict is_true
        is_ id type issubtype repr str len hash getattr getitem
        pos neg nonzero abs hex oct ord invert add sub mul
        truediv floordiv div mod divmod pow lshift rshift and_ or_
        xor int float long lt le eq ne gt ge cmp coerce contains
        iter get'''.split():
    CanRemove[_op] = True
from pypy.rpython.lltypesystem.lloperation import enum_ops_without_sideeffects
for _op in enum_ops_without_sideeffects():
    CanRemove[_op] = True
del _op
CanRemoveBuiltins = {
    isinstance: True,
    hasattr: True,
    }

def transform_dead_op_vars_in_blocks(blocks, translator=None):
    """Remove dead operations and variables that are passed over a link
    but not used in the target block. Input is a set of blocks"""
    read_vars = {}  # set of variables really used
    variable_flow = {}  # map {Var: list-of-Vars-it-depends-on}

    def canremove(op, block):
        if op.opname not in CanRemove:
            return False
        if block.exitswitch != c_last_exception:
            return True
        # cannot remove the exc-raising operation
        return op is not block.operations[-1]

    # compute variable_flow and an initial read_vars
    for block in blocks:
        # figure out which variables are ever read
        for op in block.operations:
            if not canremove(op, block):   # mark the inputs as really needed
                for arg in op.args:
                    read_vars[arg] = True
            else:
                # if CanRemove, only mark dependencies of the result
                # on the input variables
                deps = variable_flow.setdefault(op.result, [])
                deps.extend(op.args)

        if isinstance(block.exitswitch, Variable):
            read_vars[block.exitswitch] = True

        if block.exits:
            for link in block.exits:
                if link.target not in blocks:
                    for arg, targetarg in zip(link.args, link.target.inputargs):
                        read_vars[arg] = True
                        read_vars[targetarg] = True
                else:
                    for arg, targetarg in zip(link.args, link.target.inputargs):
                        deps = variable_flow.setdefault(targetarg, [])
                        deps.append(arg)
        else:
            # return and except blocks implicitely use their input variable(s)
            for arg in block.inputargs:
                read_vars[arg] = True
        # an input block's inputargs should not be modified, even if some
        # of the function's input arguments are not actually used
        if block.isstartblock:
            for arg in block.inputargs:
                read_vars[arg] = True

    # flow read_vars backwards so that any variable on which a read_vars
    # depends is also included in read_vars
    def flow_read_var_backward(pending):
        pending = list(pending)
        for var in pending:
            for prevvar in variable_flow.get(var, []):
                if prevvar not in read_vars:
                    read_vars[prevvar] = True
                    pending.append(prevvar)

    flow_read_var_backward(read_vars)
    
    for block in blocks:

        # look for removable operations whose result is never used
        for i in range(len(block.operations)-1, -1, -1):
            op = block.operations[i]
            if op.result not in read_vars: 
                if canremove(op, block):
                    del block.operations[i]
                elif op.opname == 'simple_call': 
                    # XXX we want to have a more effective and safe 
                    # way to check if this operation has side effects
                    # ... 
                    if op.args and isinstance(op.args[0], Constant):
                        func = op.args[0].value
                        try:
                            if func in CanRemoveBuiltins:
                                del block.operations[i]
                        except TypeError:   # func is not hashable
                            pass
                elif op.opname == 'direct_call':
                    if translator is not None:
                        graph = get_graph(op.args[0], translator)
                        if (graph is not None and
                            has_no_side_effects(translator, graph) and
                            (block.exitswitch != c_last_exception or
                             i != len(block.operations)- 1)):
                            del block.operations[i]
        # look for output variables never used
        # warning: this must be completely done *before* we attempt to
        # remove the corresponding variables from block.inputargs!
        # Otherwise the link.args get out of sync with the
        # link.target.inputargs.
        for link in block.exits:
            assert len(link.args) == len(link.target.inputargs)
            for i in range(len(link.args)-1, -1, -1):
                if link.target.inputargs[i] not in read_vars:
                    del link.args[i]
            # the above assert would fail here

    for block in blocks:
        # look for input variables never used
        # The corresponding link.args have already been all removed above
        for i in range(len(block.inputargs)-1, -1, -1):
            if block.inputargs[i] not in read_vars:
                del block.inputargs[i]

def remove_identical_vars(graph):
    """When the same variable is passed multiple times into the next block,
    pass it only once.  This enables further optimizations by the annotator,
    which otherwise doesn't realize that tests performed on one of the copies
    of the variable also affect the other."""

    # This algorithm is based on DataFlowFamilyBuilder, used as a
    # "phi node remover" (in the SSA sense).  'variable_families' is a
    # UnionFind object that groups variables by families; variables from the
    # same family can be identified, and if two input arguments of a block
    # end up in the same family, then we really remove one of them in favor
    # of the other.
    #
    # The idea is to identify as much variables as possible by trying
    # iteratively two kinds of phi node removal:
    #
    #  * "vertical", by identifying variables from different blocks, when
    #    we see that a value just flows unmodified into the next block without
    #    needing any merge (this is what backendopt.ssa.SSI_to_SSA() would do
    #    as well);
    #
    #  * "horizontal", by identifying two input variables of the same block,
    #    when these two variables' phi nodes have the same argument -- i.e.
    #    when for all possible incoming paths they would get twice the same
    #    value (this is really the purpose of remove_identical_vars()).
    #
    builder = ssa.DataFlowFamilyBuilder(graph)
    variable_families = builder.get_variable_families()  # vertical removal
    while True:
        if not builder.merge_identical_phi_nodes():    # horizontal removal
            break
        if not builder.complete():                     # vertical removal
            break

    for block, links in mkentrymap(graph).items():
        if block is graph.startblock:
            continue
        renaming = {}
        family2blockvar = {}
        kills = []
        for i, v in enumerate(block.inputargs):
            v1 = variable_families.find_rep(v)
            if v1 in family2blockvar:
                # already seen -- this variable can be shared with the
                # previous one
                renaming[v] = family2blockvar[v1]
                kills.append(i)
            else:
                family2blockvar[v1] = v
        if renaming:
            block.renamevariables(renaming)
            # remove the now-duplicate input variables
            kills.reverse()   # starting from the end
            for i in kills:
                del block.inputargs[i]
                for link in links:
                    del link.args[i]


def coalesce_is_true(graph):
    """coalesce paths that go through an is_true and a directly successive
       is_true both on the same value, transforming the link into the
       second is_true from the first to directly jump to the correct
       target out of the second."""
    candidates = []

    def has_is_true_exitpath(block):
        tgts = []
        start_op = block.operations[-1]
        cond_v = start_op.args[0]
        if block.exitswitch == start_op.result:
            for exit in block.exits:
                tgt = exit.target
                if tgt == block:
                    continue
                rrenaming = dict(zip(tgt.inputargs,exit.args))
                if len(tgt.operations) == 1 and tgt.operations[0].opname == 'is_true':
                    tgt_op = tgt.operations[0]
                    if tgt.exitswitch == tgt_op.result and rrenaming.get(tgt_op.args[0]) == cond_v:
                        tgts.append((exit.exitcase, tgt))
        return tgts

    for block in graph.iterblocks():
        if block.operations and block.operations[-1].opname == 'is_true':
            tgts = has_is_true_exitpath(block)
            if tgts:
                candidates.append((block, tgts))

    while candidates:
        cand, tgts = candidates.pop()
        newexits = list(cand.exits) 
        for case, tgt in tgts:
            exit = cand.exits[case]
            rrenaming = dict(zip(tgt.inputargs,exit.args))
            rrenaming[tgt.operations[0].result] = cand.operations[-1].result
            def rename(v):
                return rrenaming.get(v,v)
            newlink = tgt.exits[case].copy(rename)
            newexits[case] = newlink
        cand.recloseblock(*newexits)
        newtgts = has_is_true_exitpath(cand)
        if newtgts:
            candidates.append((cand, newtgts))

# ____________________________________________________________

def detect_list_comprehension(graph):
    """Look for the pattern:            Replace it with marker operations:

                                         v0 = newlist()
        v2 = newlist()                   v1 = hint(v0, iterable, {'maxlength'})
        loop start                       loop start
        ...                              ...
        exactly one append per loop      v1.append(..)
        and nothing else done with v2
        ...                              ...
        loop end                         v2 = hint(v1, {'fence'})
    """
    # NB. this assumes RPythonicity: we can only iterate over something
    # that has a len(), and this len() cannot change as long as we are
    # using the iterator.
    builder = ssa.DataFlowFamilyBuilder(graph)
    variable_families = builder.get_variable_families()
    c_append = Constant('append')
    newlist_v = {}
    iter_v = {}
    append_v = []
    loopnextblocks = []

    # collect relevant operations based on the family of their result
    for block in graph.iterblocks():
        if (len(block.operations) == 1 and
            block.operations[0].opname == 'next' and
            block.exitswitch == c_last_exception and
            len(block.exits) >= 2):
            cases = [link.exitcase for link in block.exits]
            if None in cases and StopIteration in cases:
                # it's a straightforward loop start block
                loopnextblocks.append((block, block.operations[0].args[0]))
                continue
        for op in block.operations:
            if op.opname == 'newlist' and not op.args:
                vlist = variable_families.find_rep(op.result)
                newlist_v[vlist] = block
            if op.opname == 'iter':
                viter = variable_families.find_rep(op.result)
                iter_v[viter] = block
    loops = []
    for block, viter in loopnextblocks:
        viterfamily = variable_families.find_rep(viter)
        if viterfamily in iter_v:
            # we have a next(viter) operation where viter comes from a
            # single known iter() operation.  Check that the iter()
            # operation is in the block just before.
            iterblock = iter_v[viterfamily]
            if (len(iterblock.exits) == 1 and iterblock.exitswitch is None
                and iterblock.exits[0].target is block):
                # yes - simple case.
                loops.append((block, iterblock, viterfamily))
    if not newlist_v or not loops:
        return

    # XXX works with Python >= 2.4 only: find calls to append encoded as
    # getattr/simple_call pairs, as produced by the LIST_APPEND bytecode.
    for block in graph.iterblocks():
        for i in range(len(block.operations)-1):
            op = block.operations[i]
            if op.opname == 'getattr' and op.args[1] == c_append:
                vlist = variable_families.find_rep(op.args[0])
                if vlist in newlist_v:
                    op2 = block.operations[i+1]
                    if (op2.opname == 'simple_call' and len(op2.args) == 2
                        and op2.args[0] is op.result):
                        append_v.append((op.args[0], op.result, block))
    if not append_v:
        return
    detector = ListComprehensionDetector(graph, loops, newlist_v,
                                         variable_families)
    graphmutated = False
    for location in append_v:
        if graphmutated:
            # new variables introduced, must restart the whole process
            return detect_list_comprehension(graph)
        try:
            detector.run(*location)
        except DetectorFailed:
            pass
        else:
            graphmutated = True

class DetectorFailed(Exception):
    pass

class ListComprehensionDetector(object):

    def __init__(self, graph, loops, newlist_v, variable_families):
        self.graph = graph
        self.loops = loops
        self.newlist_v = newlist_v
        self.variable_families = variable_families
        self.reachable_cache = {}

    def enum_blocks_with_vlist_from(self, fromblock, avoid):
        found = {avoid: True}
        pending = [fromblock]
        while pending:
            block = pending.pop()
            if block in found:
                continue
            if not self.vlist_alive(block):
                continue
            yield block
            found[block] = True
            for exit in block.exits:
                pending.append(exit.target)

    def enum_reachable_blocks(self, fromblock, stop_at, stay_within=None):
        if fromblock is stop_at:
            return
        found = {stop_at: True}
        pending = [fromblock]
        while pending:
            block = pending.pop()
            if block in found:
                continue
            found[block] = True
            for exit in block.exits:
                if stay_within is None or exit.target in stay_within:
                    yield exit.target
                    pending.append(exit.target)

    def reachable_within(self, fromblock, toblock, avoid, stay_within):
        if toblock is avoid:
            return False
        for block in self.enum_reachable_blocks(fromblock, avoid, stay_within):
            if block is toblock:
                return True
        return False

    def reachable(self, fromblock, toblock, avoid):
        if toblock is avoid:
            return False
        try:
            return self.reachable_cache[fromblock, toblock, avoid]
        except KeyError:
            pass
        future = [fromblock]
        for block in self.enum_reachable_blocks(fromblock, avoid):
            self.reachable_cache[fromblock, block, avoid] = True
            if block is toblock:
                return True
            future.append(block)
        # 'toblock' is unreachable from 'fromblock', so it is also
        # unreachable from any of the 'future' blocks
        for block in future:
            self.reachable_cache[block, toblock, avoid] = False
        return False

    def vlist_alive(self, block):
        # check if 'block' is in the "cone" of blocks where
        # the vlistfamily lives
        try:
            return self.vlistcone[block]
        except KeyError:
            result = bool(self.contains_vlist(block.inputargs))
            self.vlistcone[block] = result
            return result

    def vlist_escapes(self, block):
        # check if the vlist "escapes" to uncontrolled places in that block
        try:
            return self.escapes[block]
        except KeyError:
            for op in block.operations:
                if op.result is self.vmeth:
                    continue       # the single getattr(vlist, 'append') is ok
                if op.opname == 'getitem':
                    continue       # why not allow getitem(vlist, index) too
                if self.contains_vlist(op.args):
                    result = True
                    break
            else:
                result = False
            self.escapes[block] = result
            return result

    def contains_vlist(self, args):
        for arg in args:
            if self.variable_families.find_rep(arg) is self.vlistfamily:
                return arg
        else:
            return None

    def remove_vlist(self, args):
        removed = 0
        for i in range(len(args)-1, -1, -1):
            arg = self.variable_families.find_rep(args[i])
            if arg is self.vlistfamily:
                del args[i]
                removed += 1
        assert removed == 1

    def run(self, vlist, vmeth, appendblock):
        # first check that the 'append' method object doesn't escape
        for op in appendblock.operations:
            if op.opname == 'simple_call' and op.args[0] is vmeth:
                pass
            elif vmeth in op.args:
                raise DetectorFailed      # used in another operation
        for link in appendblock.exits:
            if vmeth in link.args:
                raise DetectorFailed      # escapes to a next block

        self.vmeth = vmeth
        self.vlistfamily = self.variable_families.find_rep(vlist)
        newlistblock = self.newlist_v[self.vlistfamily]
        self.vlistcone = {newlistblock: True}
        self.escapes = {self.graph.returnblock: True,
                        self.graph.exceptblock: True}

        # in which loop are we?
        for loopnextblock, iterblock, viterfamily in self.loops:
            # check that the vlist is alive across the loop head block,
            # which ensures that we have a whole loop where the vlist
            # doesn't change
            if not self.vlist_alive(loopnextblock):
                continue      # no - unrelated loop

            # check that we cannot go from 'newlist' to 'append' without
            # going through the 'iter' of our loop (and the following 'next').
            # This ensures that the lifetime of vlist is cleanly divided in
            # "before" and "after" the loop...
            if self.reachable(newlistblock, appendblock, avoid=iterblock):
                continue

            # ... with the possible exception of links from the loop
            # body jumping back to the loop prologue, between 'newlist' and
            # 'iter', which we must forbid too:
            if self.reachable(loopnextblock, iterblock, avoid=newlistblock):
                continue

            # there must not be a larger number of calls to 'append' than
            # the number of elements that 'next' returns, so we must ensure
            # that we cannot go from 'append' to 'append' again without
            # passing 'next'...
            if self.reachable(appendblock, appendblock, avoid=loopnextblock):
                continue

            # ... and when the iterator is exhausted, we should no longer
            # reach 'append' at all.
            stopblocks = [link.target for link in loopnextblock.exits
                                      if link.exitcase is not None]
            accepted = True
            for stopblock1 in stopblocks:
                if self.reachable(stopblock1, appendblock, avoid=newlistblock):
                    accepted = False
            if not accepted:
                continue

            # now explicitly find the "loop body" blocks: they are the ones
            # from which we can reach 'append' without going through 'iter'.
            # (XXX inefficient)
            loopbody = {}
            for block in self.graph.iterblocks():
                if (self.vlist_alive(block) and
                    self.reachable(block, appendblock, iterblock)):
                    loopbody[block] = True

            # if the 'append' is actually after a 'break' or on a path that
            # can only end up in a 'break', then it won't be recorded as part
            # of the loop body at all.  This is a strange case where we have
            # basically proved that the list will be of length 1...  too
            # uncommon to worry about, I suspect
            if appendblock not in loopbody:
                continue

            # This candidate loop is acceptable if the list is not escaping
            # too early, i.e. in the loop header or in the loop body.
            loopheader = list(self.enum_blocks_with_vlist_from(newlistblock,
                                                    avoid=loopnextblock))
            assert loopheader[0] is newlistblock
            escapes = False
            for block in loopheader + loopbody.keys():
                assert self.vlist_alive(block)
                if self.vlist_escapes(block):
                    escapes = True
                    break

            if not escapes:
                break      # accept this loop!

        else:
            raise DetectorFailed      # no suitable loop

        # Found a suitable loop, let's patch the graph:
        assert iterblock not in loopbody
        assert loopnextblock in loopbody
        for stopblock1 in stopblocks:
            assert stopblock1 not in loopbody

        # at StopIteration, the new list is exactly of the same length as
        # the one we iterate over if it's not possible to skip the appendblock
        # in the body:
        exactlength = not self.reachable_within(loopnextblock, loopnextblock,
                                                avoid = appendblock,
                                                stay_within = loopbody)

        # - add a hint(vlist, iterable, {'maxlength'}) in the iterblock,
        #   where we can compute the known maximum length
        link = iterblock.exits[0]
        vlist = self.contains_vlist(link.args)
        assert vlist
        for op in iterblock.operations:
            res = self.variable_families.find_rep(op.result)
            if res is viterfamily:
                break
        else:
            raise AssertionError("lost 'iter' operation")
        vlength = Variable('maxlength')
        vlist2 = Variable(vlist)
        chint = Constant({'maxlength': True})
        iterblock.operations += [
            SpaceOperation('hint', [vlist, op.args[0], chint], vlist2)]
        link.args = list(link.args)
        for i in range(len(link.args)):
            if link.args[i] is vlist:
                link.args[i] = vlist2

        # - wherever the list exits the loop body, add a 'hint({fence})'
        for block in loopbody:
            for link in block.exits:
                if link.target not in loopbody:
                    vlist = self.contains_vlist(link.args)
                    if vlist is None:
                        continue  # list not passed along this link anyway
                    hints = {'fence': True}
                    if (exactlength and block is loopnextblock and
                        link.target in stopblocks):
                        hints['exactlength'] = True
                    chints = Constant(hints)
                    newblock = unsimplify.insert_empty_block(None, link)
                    index = link.args.index(vlist)
                    vlist2 = newblock.inputargs[index]
                    vlist3 = Variable(vlist2)
                    newblock.inputargs[index] = vlist3
                    newblock.operations.append(
                        SpaceOperation('hint', [vlist3, chints], vlist2))
        # done!


# ____ all passes & simplify_graph

all_passes = [
    desugar_isinstance,
    eliminate_empty_blocks,
    remove_assertion_errors,
    join_blocks,
    coalesce_is_true,
    transform_dead_op_vars,
    remove_identical_vars,
    transform_ovfcheck,
    simplify_exceptions,
    transform_xxxitem,
    remove_dead_exceptions,
    ]

def simplify_graph(graph, passes=True): # can take a list of passes to apply, True meaning all
    """inplace-apply all the existing optimisations to the graph."""
    if passes is True:
        passes = all_passes
    checkgraph(graph)
    for pass_ in passes:
        pass_(graph)
    checkgraph(graph)

def cleanup_graph(graph):
    checkgraph(graph)
    eliminate_empty_blocks(graph)
    join_blocks(graph)
    remove_identical_vars(graph)
    checkgraph(graph)    
    
