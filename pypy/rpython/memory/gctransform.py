from pypy.rpython.lltypesystem import lltype
from pypy.objspace.flow.model import SpaceOperation, Variable
from pypy.translator.unsimplify import insert_empty_block
from pypy.rpython import rmodel
import sets

"""
thought experiments

'setfield' obj field value ->
  a1 <- 'cast_ptr_to_adr' obj
  a2 <- 'cast_ptr_to_adr' value
  'direct_call' write_barrier a1, offset(TYPE(obj), field), a2

operations that need hooks:

setfield, setarrayitem, direct_call, indirect_call, malloc, getfield,
getarrayitem, getsubstruct?

push_alive, pop_alive,

"""

EXCEPTION_RAISING_OPS = ['direct_call', 'indirect_call']

def var_needsgc(var):
    vartype = var.concretetype
    return isinstance(vartype, lltype.Ptr) and vartype._needsgc()

class GCTransformer:
    def __init__(self, graphs):
        self.graphs = graphs

    def transform(self):
        for graph in self.graphs:
            self.transform_graph(graph)

    def transform_graph(self, graph):
        self.links_to_split = {} # link -> vars to pop_alive across the link

        newops = []
        for var in graph.startblock.inputargs:
            if var_needsgc(var):
                newops.extend(self.push_alive(var))
        graph.startblock.operations[0:0] = newops
        
        for block in graph.iterblocks():
            self.transform_block(block)
        for link, livecounts in self.links_to_split.iteritems():
            newops = []
            for var, livecount in livecounts.iteritems():
                for i in range(livecount):
                    newops.extend(self.pop_alive(var))
                for i in range(-livecount):
                    newops.extend(self.push_alive(var))
            if newops:
                if len(link.prevblock.exits) == 1:
                    link.prevblock.operations.extend(newops)
                else:
                    insert_empty_block(None, link, newops)

    def transform_block(self, block):
        newops = []
        livevars = [var for var in block.inputargs if var_needsgc(var)]
        for op in block.operations:
            newops.extend(self.replacement_operations(op))
            if op.opname in EXCEPTION_RAISING_OPS and livevars:
                cleanup_on_exception = []
                for var in livevars:
                    cleanup_on_exception.extend(self.pop_alive(var))
                op.cleanup = cleanup_on_exception
            if var_needsgc(op.result):
                if op.opname not in ('direct_call', 'indirect_call'):
                    newops.extend(self.push_alive(op.result))
                livevars.append(op.result)
        if len(block.exits) == 0:
            # everything is fine already for returnblocks and exceptblocks
            pass
        else:
            deadinallexits = sets.Set(livevars)
            for link in block.exits:
                deadinallexits.difference_update(sets.Set(link.args))
            for var in deadinallexits:
                newops.extend(self.pop_alive(var))
            for link in block.exits:
                livecounts = dict.fromkeys(sets.Set(livevars) - deadinallexits, 1)
                for v in link.args:
                    if v in livecounts:
                        livecounts[v] -= 1
                self.links_to_split[link] = livecounts
        if newops:
            block.operations = newops

    def replacement_operations(self, op):
        m = getattr(self, 'replace_' + op.opname, None)
        if m:
            return m(op)
        else:
            return [op]

    def push_alive(self, var):
        if var.concretetype.TO is lltype.PyObject:
            return self.push_alive_pyobj(var)
        else:
            return self.push_alive_nopyobj(var)

    def push_alive_nopyobj(self, var):
        result = Variable()
        result.concretetype = lltype.Void
        return [SpaceOperation("gc_push_alive", [var], result)]

    def push_alive_pyobj(self, var):
        result = Variable()
        result.concretetype = lltype.Void
        return [SpaceOperation("gc_push_alive_pyobj", [var], result)]

    def pop_alive(self, var):
        if var.concretetype.TO is lltype.PyObject:
            return self.pop_alive_pyobj(var)
        else:
            return self.pop_alive_nopyobj(var)

    def pop_alive_nopyobj(self, var):
        result = Variable()
        result.concretetype = lltype.Void
        return [SpaceOperation("gc_pop_alive", [var], result)]

    def pop_alive_pyobj(self, var):
        result = Variable()
        result.concretetype = lltype.Void
        return [SpaceOperation("gc_pop_alive_pyobj", [var], result)]

