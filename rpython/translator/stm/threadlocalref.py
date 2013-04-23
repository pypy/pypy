from rpython.rtyper.lltypesystem import lltype, llmemory
from rpython.translator.unsimplify import varoftype
from rpython.flowspace.model import SpaceOperation, Constant


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
    ARRAY = lltype.FixedSizeArray(llmemory.Address, len(ids))
    S = lltype.Struct('THREADLOCALREF', ('ptr', ARRAY),
                      hints={'stm_thread_local': True})
    ll_threadlocalref = lltype.malloc(S, immortal=True)
    c_threadlocalref = Constant(ll_threadlocalref, lltype.Ptr(S))
    c_fieldname = Constant('ptr', lltype.Void)
    c_null = Constant(llmemory.NULL, llmemory.Address)
    #
    def getaddr(v_num, v_result):
        v_array = varoftype(lltype.Ptr(ARRAY))
        ops = [
            SpaceOperation('getfield', [c_threadlocalref, c_fieldname],
                           v_array),
            SpaceOperation('direct_ptradd', [v_array, v_num], v_result)]
        return ops
    #
    for graph in graphs:
        for block in graph.iterblocks():
            for i in range(len(block.operations)-1, -1, -1):
                op = block.operations[i]
                if op.opname == 'stm_threadlocalref_set':
                    id = op.args[0].value
                    c_num = Constant(ids.index(id), lltype.Signed)
                    v_addr = varoftype(lltype.Ptr(ARRAY))
                    ops = getaddr(c_num, v_addr)
                    ops.append(SpaceOperation('stm_threadlocalref_llset',
                                              [v_addr, op.args[1]],
                                              op.result))
                    block.operations[i:i+1] = ops
                elif op.opname == 'stm_threadlocalref_get':
                    id = op.args[0].value
                    c_num = Constant(ids.index(id), lltype.Signed)
                    v_array = varoftype(lltype.Ptr(ARRAY))
                    ops = [
                        SpaceOperation('getfield', [c_threadlocalref,
                                                    c_fieldname],
                                       v_array),
                        SpaceOperation('getarrayitem', [v_array, c_num],
                                       op.result)]
                    block.operations[i:i+1] = ops
                elif op.opname == 'stm_threadlocalref_lladdr':
                    block.operations[i:i+1] = getaddr(op.args[0], op.result)
                elif op.opname == 'stm_threadlocalref_llcount':
                    c_count = Constant(len(ids), lltype.Signed)
                    op = SpaceOperation('same_as', [c_count], op.result)
                    block.operations[i] = op
