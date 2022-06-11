
from rpython.rtyper.lltypesystem.lloperation import llop
from rpython.flowspace.model import mkentrymap, Variable
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

def can_fold(op):
    return getattr(llop, op.opname).canfold


class Cache(object):
    def __init__(self, purecache=None, heapcache=None):
        if purecache is None:
            purecache = {}
        if heapcache is None:
            heapcache = {}
        # (opname, concretetype of result, args) -> previous (life) result
        self.purecache = purecache
        self.heapcache = heapcache

    def translate_cache(self, link):
        if link.target.operations == (): # exit or except block:
            return None
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
        heapcache = {}
        for (var, field), res in self.heapcache.iteritems():
            if var in local_versions or not isinstance(var, Variable):
                heapcache[_translate_arg(var), field] = _translate_arg(res)
        purecache = {}
        for (var, concretetype, args), res in self.purecache.iteritems():
            if var in local_versions or not isinstance(var, Variable):
                args = tuple([_translate_arg(arg) for arg in args])
                purecache[_translate_arg(var), concretetype, args] = _translate_arg(res)
        return Cache(purecache, heapcache)

    def clear_for(self, concretetype, fieldname):
        for k in self.heapcache.keys():
            if k[0].concretetype == concretetype and k[1] == fieldname:
                del self.heapcache[k]

    def cse_block(self, block, inputlink):
        added_some_same_as = False
        for op in block.operations:
            if can_fold(op):
                key = (op.opname, op.result.concretetype,
                       tuple(op.args))
                res = self.purecache.get(key, None)
                if res is not None:
                    op.opname = 'same_as'
                    op.args = [res]
                    added_some_same_as = True
                else:
                    self.purecache[key] = op.result

            elif op.opname == 'getfield':
                tup = (op.args[0], op.args[1].value)
                res = self.heapcache.get(tup, None)
                if res is not None:
                    op.opname = 'same_as'
                    op.args = [res]
                    added_some_same_as = True
                else:
                    self.heapcache[tup] = op.result
            elif op.opname in ('setarrayitem', 'setinteriorfield', "malloc", "malloc_varsize"):
                pass
            elif op.opname == 'setfield':
                target = op.args[0]
                field = op.args[1].value
                self.clear_for(target.concretetype, field)
                self.heapcache[target, field] = op.args[2]
            elif has_side_effects(op):
                self.heapcache.clear()
        return added_some_same_as

def cse_graph(graph):
    """ remove superfluous getfields. use a super-local method: all non-join
    blocks inherit the heap information from their (single) predecessor
    """
    number_same_as = 0
    entrymap = mkentrymap(graph)

    # all merge blocks are starting points
    todo = [(block, None, None) for (block, prev_blocks) in entrymap.iteritems()
                if len(prev_blocks) > 1 or block is graph.startblock]

    visited = 0

    while todo:
        block, cache, inputlink = todo.pop()
        visited += 1
        if cache is None:
            cache = Cache()

        if block.operations:
            number_same_as += cache.cse_block(block, inputlink)
        for link in block.exits:
            if len(entrymap[link.target]) == 1:
                new_cache = cache.translate_cache(link)
                todo.append((link.target, new_cache, link))

    assert visited == len(entrymap)
    if number_same_as:
        removenoops.remove_same_as(graph)
        simplify.transform_dead_op_vars(graph)
    return number_same_as

