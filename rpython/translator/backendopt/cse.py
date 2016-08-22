import collections

from rpython.translator.backendopt import support
from rpython.rtyper.lltypesystem.lloperation import llop
from rpython.flowspace.model import mkentrymap, Variable
from rpython.translator.backendopt import removenoops
from rpython.translator import simplify
from rpython.translator.backendopt import ssa

def has_side_effects(op):
    if op.opname == 'debug_assert' or op.opname == 'jit_force_virtualizable':
        return False
    try:
        return getattr(llop, op.opname).sideeffects
    except AttributeError:
        return True

def cse_graph(graph):
    return CSE([graph]).transform(graph)

def can_fold(op):
    return getattr(llop, op.opname).canfold

class Cache(object):
    def __init__(self, variable_families, purecache=None, heapcache=None):
        if purecache is None:
            purecache = {}
        if heapcache is None:
            heapcache = {}
        self.purecache = purecache
        self.heapcache = heapcache
        self.variable_families = variable_families

    def copy(self):
        return Cache(
                self.variable_families, self.purecache.copy(),
                self.heapcache.copy())


    def merge(self, firstlink, tuples):
        purecache = {}
        block = firstlink.target
        # copy all operations that exist in *all* blocks over. need to add a new
        # inputarg if the result is really a variable
        for key, res in self.purecache.iteritems():
            for link, cache in tuples[1:]:
                val = cache.purecache.get(key, None)
                if val is None:
                    break
            else:
                newres = res
                if isinstance(res, Variable):
                    newres = res.copy()
                    for link, cache in tuples:
                        link.args.append(cache.purecache[key])
                    block.inputargs.append(newres)
                purecache[key] = newres

        # merge heapcache
        heapcache = {}
        for key, res in self.heapcache.iteritems():
            for link, cache in tuples[1:]:
                val = cache.heapcache.get(key, None)
                if val is None:
                    break
            else:
                newres = res
                if isinstance(res, Variable):
                    newres = res.copy()
                    for link, cache in tuples:
                        link.args.append(cache.heapcache[key])
                    block.inputargs.append(newres)
                heapcache[key] = newres

        return Cache(self.variable_families, purecache, heapcache)

    def _clear_heapcache_for(self, concretetype, fieldname):
        for k in self.heapcache.keys():
            if k[0].concretetype == concretetype and k[1] == fieldname:
                del self.heapcache[k]

    def cse_block(self, block):
        def representative_arg(arg):
            if isinstance(arg, Variable):
                return self.variable_families.find_rep(arg)
            return arg
        added_some_same_as = False
        for op in block.operations:
            # heap operations
            if op.opname == 'getfield':
                tup = (representative_arg(op.args[0]), op.args[1].value)
                res = self.heapcache.get(tup, None)
                if res is not None:
                    op.opname = 'same_as'
                    op.args = [res]
                    added_some_same_as = True
                else:
                    self.heapcache[tup] = op.result
                continue
            if op.opname in ('setarrayitem', 'setinteriorfield', "malloc", "malloc_varsize"):
                continue
            if op.opname == 'setfield':
                target = representative_arg(op.args[0])
                field = op.args[1].value
                self._clear_heapcache_for(target.concretetype, field)
                self.heapcache[target, field] = op.args[2]
                continue
            if has_side_effects(op):
                self.heapcache.clear()
                continue

            # foldable operations
            if not can_fold(op):
                continue
            key = (op.opname, op.result.concretetype,
                   tuple([representative_arg(arg) for arg in op.args]))
            res = self.purecache.get(key, None)
            if res is not None:
                op.opname = 'same_as'
                op.args = [res]
                added_some_same_as = True
                self.variable_families.union(res, op.result)
            else:
                self.purecache[key] = op.result
        return added_some_same_as

def _merge(tuples, variable_families):
    if not tuples:
        return Cache(variable_families)
    if len(tuples) == 1:
        (link, cache), = tuples
        return cache.copy()
    firstlink, firstcache = tuples[0]
    return firstcache.merge(firstlink, tuples)

class CSE(object):
    def __init__(self, translator):
        self.translator = translator

    def transform(self, graph):
        variable_families = ssa.DataFlowFamilyBuilder(graph).get_variable_families()
        entrymap = mkentrymap(graph)
        backedges = support.find_backedges(graph)
        todo = collections.deque([graph.startblock])
        caches_to_merge = collections.defaultdict(list)
        done = set()

        added_some_same_as = False

        while todo:
            block = todo.popleft()
            can_cache = True
            for link in entrymap[block]:
                if link in backedges:
                    can_cache = False

            if block.operations:
                if not can_cache:
                    cache = Cache(variable_families)
                else:
                    cache = _merge(caches_to_merge[block], variable_families)
                changed_block = cache.cse_block(block)
                added_some_same_as = changed_block or added_some_same_as
            done.add(block)
            # add all target blocks where all predecessors are already done
            for exit in block.exits:
                for lnk in entrymap[exit.target]:
                    if lnk.prevblock not in done and lnk not in backedges:
                        break
                else:
                    if exit.target not in done:
                        todo.append(exit.target)
                caches_to_merge[exit.target].append((exit, cache))
        if added_some_same_as:
            ssa.SSA_to_SSI(graph)
            removenoops.remove_same_as(graph)
        simplify.transform_dead_op_vars(graph)

