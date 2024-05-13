
from rpython.rtyper.lltypesystem.lloperation import llop
from rpython.rtyper.lltypesystem import lltype
from rpython.flowspace.model import mkentrymap, Variable, Constant
from rpython.translator.backendopt import removenoops
from rpython.translator import simplify

OK_OPS = frozenset(['debug_assert', 'debug_assert_not_none', 'jit_force_virtualizable'])

def has_side_effects(op):
    if op.opname in OK_OPS:
        return False
    try:
        return getattr(llop, op.opname).sideeffects
    except AttributeError:
        return True


def storesink_graph(graph):
    """ remove superfluous getfields. use a super-local method: all non-join
    blocks inherit the heap information from their (single) predecessor
    """
    added_some_same_as = False
    entrymap = mkentrymap(graph)

    # all merge blocks are starting points
    todo = [(block, None, None) for (block, prev_blocks) in entrymap.iteritems()
                if len(prev_blocks) > 1 or block is graph.startblock]

    visited = 0

    while todo:
        block, cache, inputlink = todo.pop()
        visited += 1
        if cache is None:
            cache = {}

        if block.operations:
            changed_block = _storesink_block(block, cache, inputlink)
            added_some_same_as = changed_block or added_some_same_as
        for link in block.exits:
            if len(entrymap[link.target]) == 1:
                new_cache = _translate_cache(cache, link)
                todo.append((link.target, new_cache, link))

    assert visited == len(entrymap)
    if added_some_same_as:
        removenoops.remove_same_as(graph)
        simplify.transform_dead_op_vars(graph)

def _translate_cache(cache, link):
    if link.target.operations == (): # exit or except block:
        return {}
    block = link.target
    local_versions = {var1: var2 for var1, var2 in zip(link.args, block.inputargs)}
    def _translate_arg(arg):
        if isinstance(arg, Variable):
            res = local_versions.get(arg, None)
            if res is None:
                res = Variable(arg)
                res.concretetype = arg.concretetype
                link.args.append(arg)
                block.inputargs.append(res)
                local_versions[arg] = res
            return res
        else:
            return arg
    new_cache = {}
    for (var, field), res in cache.iteritems():
        if var in local_versions or not isinstance(var, Variable):
            new_cache[_translate_arg(var), field] = _translate_arg(res)
    return new_cache

def _storesink_block(block, cache, inputlink):
    def clear_cache_for(cache, concretetype, fieldname):
        for k in cache.keys():
            if k[0].concretetype == concretetype and k[1] == fieldname:
                del cache[k]
    replacements = {}
    def replace(op, res):
        op.opname = 'same_as'
        op.args = [res]
        replacements[op.result] = res

    def get_rep(arg):
        return replacements.get(arg, arg)

    added_some_same_as = False
    for op in block.operations:
        if op.opname == 'getfield':
            arg0 = get_rep(op.args[0])
            field = op.args[1].value
            if (
                    isinstance(arg0, Constant) and
                    arg0.concretetype.TO._immutable_field(field) and
                    arg0.value and # exclude null ptrs
                    not isinstance(arg0.value._obj, int) # tagged int
            ):
                # reading an immutable field from a constant
                llres = getattr(arg0.value, field)
                concretetype = getattr(arg0.concretetype.TO, field)
                res = Constant(llres, concretetype)
                replace(op, res)
            else:
                tup = (arg0, op.args[1].value)
                res = cache.get(tup, None)
                if res is not None:
                    replace(op, res)
                else:
                    cache[tup] = op.result
        elif op.opname == 'cast_pointer':
            arg0 = get_rep(op.args[0])
            if isinstance(arg0, Constant):
                llres = lltype.cast_pointer(op.result.concretetype, arg0.value)
                res = Constant(llres, op.result.concretetype)
                replace(op, res)
            else:
                tup = (arg0, op.result.concretetype)
                res = cache.get(tup, None)
                if res is not None:
                    replace(op, res)
                else:
                    cache[tup] = op.result
        elif op.opname in ('setarrayitem', 'setinteriorfield', "malloc", "malloc_varsize"):
            pass
        elif op.opname == 'setfield':
            target = get_rep(op.args[0])
            field = op.args[1].value
            clear_cache_for(cache, target.concretetype, field)
            cache[target, field] = op.args[2]
        elif has_side_effects(op):
            cache.clear()
    return bool(replacements)
