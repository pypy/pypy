
from pypy.rpython.lltypesystem.lloperation import llop

def has_side_effects(op):
    if op.opname == 'debug_assert':
        return False
    try:
        return getattr(llop, op.opname).sideeffects
    except AttributeError:
        return True

def storesink_graph(graph):
    def rename(op, renaming):
        for i, arg in enumerate(op.args):
            r = renaming.get(arg, None)
            if r is not None:
                op.args[i] = r
        return op

    def clear_cache_for(cache, concretetype, fieldname):
        for k in cache.keys():
            if k[0].concretetype == concretetype and k[1] == fieldname:
                del cache[k]
    
    for block in graph.iterblocks():
        newops = []
        cache = {}
        renaming = {}
        for op in block.operations:
            if op.opname == 'getfield':
                tup = (op.args[0], op.args[1].value)
                res = cache.get(tup, None)
                if res is not None:
                    renaming[op.result] = res
                    continue
                cache[tup] = op.result
            elif op.opname in ['setarrayitem', 'setinteriorfield']:
                pass
            elif op.opname == 'setfield':
                clear_cache_for(cache, op.args[0].concretetype,
                                op.args[1].value)
            elif has_side_effects(op):
                cache = {}
            newops.append(rename(op, renaming))
        if block.operations:
            block.operations = newops
        for exit in block.exits:
            rename(exit, renaming)
        
