from rpython.rtyper.lltypesystem import lltype, llmemory
from rpython.translator.unsimplify import varoftype
from rpython.flowspace.model import SpaceOperation, Constant

#
# Note: all this slightly messy code is to have 'stm_threadlocalref_flush'
# which zeroes *all* thread-locals variables accessed with
# stm_threadlocalref_{get,set}.
#

def transform_tlref(graphs):
    ids = set()
    #
    for graph in graphs:
        for block in graph.iterblocks():
            for i in range(len(block.operations)):
                op = block.operations[i]
                if (op.opname == 'stm_threadlocalref_set' or
                    op.opname == 'stm_threadlocalref_get'):
                    ids.add(op.args[0].value)
    #
    ids = sorted(ids)
    fields = [('ptr%d' % id1, llmemory.Address) for id1 in ids]
    kwds = {'hints': {'stm_thread_local': True}}
    S = lltype.Struct('THREADLOCALREF', *fields, **kwds)
    ll_threadlocalref = lltype.malloc(S, immortal=True)
    c_threadlocalref = Constant(ll_threadlocalref, lltype.Ptr(S))
    c_fieldnames = {}
    for id1 in ids:
        fieldname = 'ptr%d' % id1
        c_fieldnames[id1] = Constant(fieldname, lltype.Void)
    c_null = Constant(llmemory.NULL, llmemory.Address)
    #
    for graph in graphs:
        for block in graph.iterblocks():
            for i in range(len(block.operations)-1, -1, -1):
                op = block.operations[i]
                if op.opname == 'stm_threadlocalref_set':
                    id1 = op.args[0].value
                    op = SpaceOperation('setfield', [c_threadlocalref,
                                                     c_fieldnames[id1],
                                                     op.args[1]],
                                        op.result)
                    block.operations[i] = op
                elif op.opname == 'stm_threadlocalref_get':
                    id1 = op.args[0].value
                    op = SpaceOperation('getfield', [c_threadlocalref,
                                                     c_fieldnames[id1]],
                                        op.result)
                    block.operations[i] = op
                elif op.opname == 'stm_threadlocalref_flush':
                    extra = []
                    for id1 in ids:
                        op = SpaceOperation('setfield', [c_threadlocalref,
                                                         c_fieldnames[id1],
                                                         c_null],
                                            varoftype(lltype.Void))
                        extra.append(op)
                    block.operations[i:i+1] = extra
