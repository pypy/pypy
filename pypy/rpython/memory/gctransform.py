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
        for block in graph.iterblocks():
            self.transform_block(block)
        for link, vars in self.links_to_split.iteritems():
            newops = []
            for var in vars:
                newops.extend(self.pop_alive(var))
            insert_empty_block(None, link, newops)

    def transform_block(self, block):
        newops = []
        livevars = [var for var in block.inputargs if var_needsgc(var)]
        for op in block.operations:
            newops.extend(self.replacement_operations(op))
            if op.opname in ('direct_call', 'indirect_call') and livevars:
                op.args.append(rmodel.inputconst(lltype.Void, livevars[:]))
            if var_needsgc(op.result):
                if op.opname not in ('direct_call', 'indirect_call'):
                    newops.extend(self.push_alive(op.result))
                livevars.append(op.result)
        if len(block.exits) == 0:
            # everything is fine already for returnblocks and exceptblocks
            pass
        elif len(block.exits) == 1:
            for var in livevars:
                if var not in block.exits[0].args:
                    newops.extend(self.pop_alive(var))
        else:
            deadinallexits = sets.Set(livevars)
            for link in block.exits:
                deadinallexits.difference_update(sets.Set(link.args))
            for var in deadinallexits:
                newops.extend(self.pop_alive(var))
            for link in block.exits:
                deadvarsforlink = sets.Set(livevars) - deadinallexits - sets.Set(link.args)
                if deadvarsforlink:
                    self.links_to_split[link] = deadvarsforlink
        if newops:
            block.operations = newops

    def replacement_operations(self, op):
        m = getattr(self, 'replace_' + op.opname, None)
        if m:
            return m(op)
        else:
            return [op]

    def push_alive(self, var):
        result = Variable()
        result.concretetype = lltype.Void
        return [SpaceOperation("push_alive", [var], result)]

    def pop_alive(self, var):
        result = Variable()
        result.concretetype = lltype.Void
        return [SpaceOperation("pop_alive", [var], result)]

