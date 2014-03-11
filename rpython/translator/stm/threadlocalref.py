from rpython.annotator import model as annmodel
from rpython.rtyper import llannotation
from rpython.rtyper import annlowlevel
from rpython.rtyper.lltypesystem import lltype, rclass
from rpython.rtyper.lltypesystem.lloperation import llop
from rpython.flowspace.model import SpaceOperation, Constant


def transform_tlref(t):
    ids = set()
    graphs = t.graphs
    #
    for graph in graphs:
        for block in graph.iterblocks():
            for i in range(len(block.operations)):
                op = block.operations[i]
                if (op.opname == 'stm_threadlocalref_set' or
                    op.opname == 'stm_threadlocalref_get'):
                    ids.add(op.args[0].value)
    if not ids:
        return
    #
    ids = sorted(ids)
    total = len(ids)
    ARRAY = lltype.GcArray(rclass.OBJECTPTR)
    #
    def ll_threadlocalref_get(index):
        array = llop.stm_threadlocal_get(lltype.Ptr(ARRAY))
        if not array:
            return lltype.nullptr(rclass.OBJECTPTR.TO)
        else:
            llop.stm_read(lltype.Void, array)
            # ^^^ might not actually be needed, because this array is
            # only ever seen from the current transaction; but better
            # safe than sorry
            return array[index]
    #
    def ll_threadlocalref_set(index, newvalue):
        array = llop.stm_threadlocal_get(lltype.Ptr(ARRAY))
        if not array:
            array = lltype.malloc(ARRAY, total) # llop may allocate!
            llop.stm_threadlocal_set(lltype.Void, array)
        else:
            llop.stm_write(lltype.Void, array)
            # ^^^ might not actually be needed, because this array is
            # only ever seen from the current transaction; but better
            # safe than sorry
        # invalidating other barriers after an llop.threadlocalref_set
        # is not necessary since no other variable should contain
        # a reference to stm_threadlocal_obj
        array[index] = newvalue
    #
    annhelper = annlowlevel.MixLevelHelperAnnotator(t.rtyper)
    s_Int = annmodel.SomeInteger()
    s_Ptr = llannotation.SomePtr(rclass.OBJECTPTR)
    c_getter_ptr = annhelper.constfunc(ll_threadlocalref_get,
                                       [s_Int], s_Ptr)
    c_setter_ptr = annhelper.constfunc(ll_threadlocalref_set,
                                       [s_Int, s_Ptr], annmodel.s_None)
    annhelper.finish()
    #
    for graph in graphs:
        for block in graph.iterblocks():
            for i in range(len(block.operations)-1, -1, -1):
                op = block.operations[i]
                if op.opname == 'stm_threadlocalref_set':
                    id = op.args[0].value
                    c_num = Constant(ids.index(id), lltype.Signed)
                    ops = [
                        SpaceOperation('direct_call', [c_setter_ptr, c_num,
                                                       op.args[1]],
                                       op.result)
                        ]
                    block.operations[i:i+1] = ops
                elif op.opname == 'stm_threadlocalref_get':
                    id = op.args[0].value
                    c_num = Constant(ids.index(id), lltype.Signed)
                    ops = [
                        SpaceOperation('direct_call', [c_getter_ptr, c_num],
                                       op.result)
                        ]
                    block.operations[i:i+1] = ops
