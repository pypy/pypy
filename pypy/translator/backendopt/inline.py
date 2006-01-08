import sys
from pypy.translator.simplify import eliminate_empty_blocks, join_blocks
from pypy.translator.simplify import remove_identical_vars, get_graph
from pypy.translator.unsimplify import copyvar, split_block
from pypy.objspace.flow.model import Variable, Constant, Block, Link
from pypy.objspace.flow.model import SpaceOperation, c_last_exception
from pypy.objspace.flow.model import traverse, mkentrymap, checkgraph
from pypy.annotation import model as annmodel
from pypy.rpython.lltypesystem.lltype import Bool, typeOf, Void
from pypy.rpython import rmodel
from pypy.tool.algo import sparsemat
from pypy.translator.backendopt.support import log

BASE_INLINE_THRESHOLD = 32.4    # just enough to inline add__Int_Int()
# and just small enough to prevend inlining of some rlist functions.

class CannotInline(Exception):
    pass


def collect_called_graphs(graph, translator):
    graphs_or_something = {}
    for block in graph.iterblocks():
        for op in block.operations:
            if op.opname == "direct_call":
                graph = get_graph(op.args[0], translator)
                if graph is not None:
                    graphs_or_something[graph] = True
                else:
                    graphs_or_something[op.args[0]] = True
            if op.opname == "indirect_call":
                graphs = op.args[-1].value
                if graphs is None:
                    graphs_or_something[op.args[0]] = True
                else:
                    for graph in graphs:
                        graphs_or_something[graph] = True
    return graphs_or_something

def find_callsites(graph, calling_what):
    callsites = []
    def visit(block):
        if isinstance(block, Block):
            for i, op in enumerate(block.operations):
                if not op.opname == "direct_call":
                    continue
                funcobj = op.args[0].value._obj
                graph = getattr(funcobj, 'graph', None)
                # accept a function or a graph as 'inline_func'
                if (graph is calling_what or
                    getattr(funcobj, '_callable', None) is calling_what):
                    callsites.append((graph, block, i))
    traverse(visit, graph)
    return callsites

def inline_function(translator, inline_func, graph):
    count = 0
    callsites = find_callsites(graph, inline_func)
    while callsites != []:
        subgraph, block, index_operation = callsites.pop()
        if find_callsites(subgraph, subgraph):
            raise CannotInline("inlining a recursive function")
        _inline_function(translator, graph, block, index_operation)
        checkgraph(graph)
        count += 1
        callsites = find_callsites(graph, inline_func)
    return count

def _find_exception_type(block):
    #XXX slightly brittle: find the exception type for simple cases
    #(e.g. if you do only raise XXXError) by doing pattern matching
    ops = [op for op in block.operations if op.opname != 'keepalive'] 
    if (len(ops) < 6 or
        ops[-6].opname != "malloc" or ops[-5].opname != "cast_pointer" or
        ops[-4].opname != "setfield" or ops[-3].opname != "cast_pointer" or
        ops[-2].opname != "getfield" or ops[-1].opname != "cast_pointer" or
        len(block.exits) != 1 or block.exits[0].args[0] != ops[-2].result or
        block.exitswitch is not None or
        block.exits[0].args[1] != ops[-1].result or
        not isinstance(ops[-4].args[1], Constant) or
        ops[-4].args[1].value != "typeptr"):
        return None, None
    return ops[-4].args[2].value, block.exits[0]


class Inliner(object):
    def __init__(self, translator, graph, block, index_operation):
        self.translator = translator
        self.graph = graph
        self.varmap = {}
        self.beforeblock = block
        self._copied_blocks = {}
        self.op = block.operations[index_operation]
        self.graph_to_inline = self.op.args[0].value._obj.graph
        self.exception_guarded = False
        if (block.exitswitch == c_last_exception and
            index_operation == len(block.operations) - 1):
            self.exception_guarded = True
            if len(collect_called_graphs(self.graph_to_inline, self.translator)) != 0:
                raise CannotInline("can't handle exceptions yet")
        self._passon_vars = {}
        self.entrymap = mkentrymap(self.graph_to_inline)
        self.do_inline(block, index_operation)
        self.cleanup()

    def get_new_name(self, var):
        if var is None:
            return None
        if isinstance(var, Constant):
            return var
        if var not in self.varmap:
            self.varmap[var] = copyvar(self.translator, var)
        return self.varmap[var]
        
    def passon_vars(self, cache_key):
        if cache_key in self._passon_vars:
            return self._passon_vars[cache_key]
        result = [copyvar(self.translator, var)
                      for var in self.original_passon_vars]
        self._passon_vars[cache_key] = result
        return result
        
    def copy_operation(self, op):
        args = [self.get_new_name(arg) for arg in op.args]
        return SpaceOperation(op.opname, args, self.get_new_name(op.result))

    def copy_block(self, block):
        if block in self._copied_blocks:
            return self._copied_blocks[block]
        args = ([self.get_new_name(var) for var in block.inputargs] +
                self.passon_vars(block))
        newblock = Block(args)
        self._copied_blocks[block] = newblock
        newblock.operations = [self.copy_operation(op) for op in block.operations]
        newblock.exits = [self.copy_link(link, block) for link in block.exits]
        newblock.exitswitch = self.get_new_name(block.exitswitch)
        newblock.exc_handler = block.exc_handler
        return newblock

    def copy_link(self, link, prevblock):
        newargs = [self.get_new_name(a) for a in link.args] + self.passon_vars(prevblock)
        newlink = Link(newargs, self.copy_block(link.target), link.exitcase)
        newlink.prevblock = self.copy_block(link.prevblock)
        newlink.last_exception = self.get_new_name(link.last_exception)
        newlink.last_exc_value = self.get_new_name(link.last_exc_value)
        if hasattr(link, 'llexitcase'):
            newlink.llexitcase = link.llexitcase
        return newlink
        
    def generate_keepalive(self, vars):
        keepalive_ops = []
        for v in vars:
            if isinstance(v, Constant):
                continue
            if v.concretetype._is_atomic():
                continue
            v_keepalive = Variable()
            v_keepalive.concretetype = Void
            keepalive_ops.append(SpaceOperation('keepalive', [v], v_keepalive))
        return keepalive_ops

    def find_args_in_exceptional_case(self, link, block, etype, evalue, afterblock, passon_vars):
        linkargs = []
        for arg in link.args:
            if arg == link.last_exception:
                linkargs.append(etype)
            elif arg == link.last_exc_value:
                linkargs.append(evalue)
            elif isinstance(arg, Constant):
                linkargs.append(arg)
            else:
                index = afterblock.inputargs.index(arg)
                linkargs.append(passon_vars[index - 1])
        return linkargs

    def rewire_returnblock(self, afterblock):
        copiedreturnblock = self.copy_block(self.graph_to_inline.returnblock)
        linkargs = ([copiedreturnblock.inputargs[0]] +
                    self.passon_vars(self.graph_to_inline.returnblock))
        linkfrominlined = Link(linkargs, afterblock)
        linkfrominlined.prevblock = copiedreturnblock
        copiedreturnblock.exitswitch = None
        copiedreturnblock.exits = [linkfrominlined]
        assert copiedreturnblock.exits[0].target == afterblock
       
    def rewire_exceptblock(self, afterblock):
        #let links to exceptblock of the graph to inline go to graphs exceptblock
        copiedexceptblock = self.copy_block(self.graph_to_inline.exceptblock)
        if not self.exception_guarded:
            self.rewire_exceptblock_no_guard(afterblock, copiedexceptblock)
        else:
            # first try to match exceptions using a very simple heuristic
            self.rewire_exceptblock_with_guard(afterblock, copiedexceptblock)
            # generate blocks that do generic matching for cases when the
            # heuristic did not work
            self.generic_exception_matching(afterblock, copiedexceptblock)

    def rewire_exceptblock_no_guard(self, afterblock, copiedexceptblock):
         # find all copied links that go to copiedexceptblock
        for link in self.entrymap[self.graph_to_inline.exceptblock]:
            copiedblock = self.copy_block(link.prevblock)
            for copiedlink in copiedblock.exits:
                if copiedlink.target is copiedexceptblock:
                    copiedlink.args = copiedlink.args[:2]
                    copiedlink.target = self.graph.exceptblock
                    for a1, a2 in zip(copiedlink.args,
                                      self.graph.exceptblock.inputargs):
                        if hasattr(a2, 'concretetype'):
                            assert a1.concretetype == a2.concretetype
                        else:
                            # if self.graph.exceptblock was never used before
                            a2.concretetype = a1.concretetype
    
    def rewire_exceptblock_with_guard(self, afterblock, copiedexceptblock):
        # this rewiring does not always succeed. in the cases where it doesn't
        # there will be generic code inserted
        exc_match = self.translator.rtyper.getexceptiondata().fn_exception_match
        for link in self.entrymap[self.graph_to_inline.exceptblock]:
            copiedblock = self.copy_block(link.prevblock)
            eclass, copiedlink = _find_exception_type(copiedblock)
            #print copiedblock.operations
            if eclass is None:
                continue
            etype = copiedlink.args[0]
            evalue = copiedlink.args[1]
            for exceptionlink in afterblock.exits[1:]:
                if exc_match(eclass, exceptionlink.llexitcase):
                    passon_vars = self.passon_vars(link.prevblock)
                    copiedblock.operations += self.generate_keepalive(passon_vars)
                    copiedlink.target = exceptionlink.target
                    linkargs = self.find_args_in_exceptional_case(
                        exceptionlink, link.prevblock, etype, evalue, afterblock, passon_vars)
                    copiedlink.args = linkargs
                    break

    def generic_exception_matching(self, afterblock, copiedexceptblock):
        #XXXXX don't look: insert blocks that do exception matching
        #for the cases where direct matching did not work
        exc_match = Constant(
            self.translator.rtyper.getexceptiondata().fn_exception_match)
        exc_match.concretetype = typeOf(exc_match.value)
        blocks = []
        for i, link in enumerate(afterblock.exits[1:]):
            etype = copyvar(self.translator, copiedexceptblock.inputargs[0])
            evalue = copyvar(self.translator, copiedexceptblock.inputargs[1])
            passon_vars = self.passon_vars(i)
            block = Block([etype, evalue] + passon_vars)
            res = Variable()
            res.concretetype = Bool
            self.translator.annotator.bindings[res] = annmodel.SomeBool()
            cexitcase = Constant(link.llexitcase)
            cexitcase.concretetype = typeOf(cexitcase.value)
            args = [exc_match, etype, cexitcase]
            block.operations.append(SpaceOperation("direct_call", args, res))
            block.exitswitch = res
            linkargs = self.find_args_in_exceptional_case(link, link.target,
                                                          etype, evalue, afterblock,
                                                          passon_vars)
            l = Link(linkargs, link.target)
            l.prevblock = block
            l.exitcase = True
            l.llexitcase = True
            block.exits.append(l)
            if i > 0:
                l = Link(blocks[-1].inputargs, block)
                l.prevblock = blocks[-1]
                l.exitcase = False
                l.llexitcase = False
                blocks[-1].exits.insert(0, l)
            blocks.append(block)
        blocks[-1].exits = blocks[-1].exits[:1]
        blocks[-1].operations = []
        blocks[-1].exitswitch = None
        blocks[-1].exits[0].exitcase = None
        del blocks[-1].exits[0].llexitcase
        linkargs = copiedexceptblock.inputargs
        copiedexceptblock.closeblock(Link(linkargs, blocks[0]))
        copiedexceptblock.operations += self.generate_keepalive(linkargs)

      
    def do_inline(self, block, index_operation):
        afterblock = split_block(self.translator, self.graph, block, index_operation)
        # these variables have to be passed along all the links in the inlined
        # graph because the original function needs them in the blocks after
        # the inlined function
        # for every inserted block we need a new copy of these variables,
        # this copy is created with the method passon_vars
        self.original_passon_vars = [arg for arg in self.beforeblock.exits[0].args
                                         if isinstance(arg, Variable)]
        assert afterblock.operations[0] is self.op
        #vars that need to be passed through the blocks of the inlined function
        linktoinlined = self.beforeblock.exits[0]
        assert linktoinlined.target is afterblock
        copiedstartblock = self.copy_block(self.graph_to_inline.startblock)
        copiedstartblock.isstartblock = False
        #find args passed to startblock of inlined function
        passon_args = []
        for arg in self.op.args[1:]:
            if isinstance(arg, Constant):
                passon_args.append(arg)
            else:
                index = afterblock.inputargs.index(arg)
                passon_args.append(linktoinlined.args[index])
        passon_args += self.original_passon_vars
        #rewire blocks
        linktoinlined.target = copiedstartblock
        linktoinlined.args = passon_args
        afterblock.inputargs = [self.op.result] + afterblock.inputargs
        afterblock.operations = self.generate_keepalive(afterblock.inputargs) + afterblock.operations[1:]
        if self.graph_to_inline.returnblock in self.entrymap:
            self.rewire_returnblock(afterblock) 
        if self.graph_to_inline.exceptblock in self.entrymap:
            self.rewire_exceptblock(afterblock)
        if self.exception_guarded:
            assert afterblock.exits[0].exitcase is None
            afterblock.exits = [afterblock.exits[0]]
            afterblock.exitswitch = None

    def cleanup(self):
        """ cleaning up -- makes sense to be done after inlining, because the
        inliner inserted quite some empty blocks and blocks that can be
        joined. """
        checkgraph(self.graph)
        eliminate_empty_blocks(self.graph)
        join_blocks(self.graph)
        remove_identical_vars(self.graph)


_inline_function = Inliner

# ____________________________________________________________
#
# Automatic inlining

OP_WEIGHTS = {'same_as': 0,
              'cast_pointer': 0,
              'keepalive': 0,
              'direct_call': 2,    # guess
              'indirect_call': 2,  # guess
              'yield_current_frame_to_caller': sys.maxint, # XXX bit extreme
              }

def block_weight(block, weights=OP_WEIGHTS):
    total = 0
    for op in block.operations:
        total += weights.get(op.opname, 1)
    if block.exitswitch is not None:
        total += 1
    return total


def measure_median_execution_cost(graph):
    blocks = []
    blockmap = {}
    for block in graph.iterblocks():
        blockmap[block] = len(blocks)
        blocks.append(block)
    M = sparsemat.SparseMatrix(len(blocks))
    vector = []
    for i, block in enumerate(blocks):
        vector.append(block_weight(block))
        M[i, i] = 1
        if block.exits:
            f = 1.0 / len(block.exits)
            for link in block.exits:
                M[i, blockmap[link.target]] -= f
    try:
        Solution = M.solve(vector)
    except ValueError:
        return sys.maxint
    else:
        res = Solution[blockmap[graph.startblock]]
        assert res >= 0
        return res

def static_instruction_count(graph):
    count = 0
    for block in graph.iterblocks():
        count += block_weight(block)
    return count

def inlining_heuristic(graph, callers=None, callees=None):
    # XXX ponderation factors?
    factor = 1
    if callers is not None:
        if len(callers) == 1:
            factor = 0.1
    return (0.9999 * measure_median_execution_cost(graph) +
            static_instruction_count(graph)) * factor


def static_callers(translator, ignore_primitives=False):
    result = []
    def build_call_graph(node):
        if isinstance(node, Block):
            for op in node.operations:
                if op.opname == "direct_call":
                    funcobj = op.args[0].value._obj
                    graph = getattr(funcobj, 'graph', None)
                    if graph is not None:
                        if ignore_primitives:
                            if getattr(getattr(funcobj, '_callable', None),
                                       'suggested_primitive', False):
                                continue
                        result.append((parentgraph, graph))
    for parentgraph in translator.graphs:
        traverse(build_call_graph, parentgraph)
    return result


def auto_inlining(translator, threshold=1):
    from heapq import heappush, heappop, heapreplace
    threshold *= BASE_INLINE_THRESHOLD
    callers = {}     # {graph: {graphs-that-call-it}}
    callees = {}     # {graph: {graphs-that-it-calls}}
    for graph1, graph2 in static_callers(translator, ignore_primitives=True):
        callers.setdefault(graph2, {})[graph1] = True
        callees.setdefault(graph1, {})[graph2] = True
    fiboheap = [(0.0, graph) for graph in callers]
    valid_weight = {}
    couldnt_inline = {}

    while fiboheap:
        weight, graph = fiboheap[0]
        if not valid_weight.get(graph):
            weight = inlining_heuristic(graph, callers.get(graph), callees.get(graph))
            #print '  + cost %7.2f %50s' % (weight, graph.name)
            heapreplace(fiboheap, (weight, graph))
            valid_weight[graph] = True
            continue

        if weight >= threshold:
            break   # finished

        heappop(fiboheap)
        log.inlining('%7.2f %50s' % (weight, graph.name))
        for parentgraph in callers[graph]:
            if parentgraph == graph:
                continue
            sys.stdout.flush()
            try:
                res = bool(inline_function(translator, graph, parentgraph))
            except CannotInline:
                couldnt_inline[graph] = True
                res = CannotInline
            if res is True:
                # the parentgraph should now contain all calls that were
                # done by 'graph'
                for graph2 in callees.get(graph, {}):
                    callees[parentgraph][graph2] = True
                    callers[graph2][parentgraph] = True
                if parentgraph in couldnt_inline:
                    # the parentgraph was previously uninlinable, but it has
                    # been modified.  Maybe now we can inline it into further
                    # parents?
                    del couldnt_inline[parentgraph]
                    heappush(fiboheap, (0.0, parentgraph))
                valid_weight[parentgraph] = False
