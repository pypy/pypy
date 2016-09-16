import collections

from rpython.translator.backendopt import support
from rpython.rtyper.lltypesystem.lloperation import llop
from rpython.rtyper.lltypesystem import lltype
from rpython.flowspace.model import mkentrymap, Variable, Constant
from rpython.translator.backendopt import removenoops
from rpython.translator import simplify
from rpython.translator.backendopt import ssa, constfold
from rpython.translator.backendopt.writeanalyze import WriteAnalyzer
from rpython.tool.algo import unionfind

from rpython.translator.backendopt.support import log

def has_side_effects(op):
    try:
        return getattr(llop, op.opname).sideeffects
    except AttributeError:
        return True

def common_subexpression_elimination(t, graphs=None):
    if graphs is None:
        graphs = t.graphs
    cse = CSE(t)

    removed_ops = 0
    for graph in graphs:
        removed_ops += cse.transform(graph)
    log.cse("cse removed %s ops" % (removed_ops, ))

def can_fold(op):
    return getattr(llop, op.opname).canfold

class Cache(object):
    def __init__(self, variable_families, analyzer, new_unions=None,
                 purecache=None, heapcache=None):
        if purecache is None:
            purecache = {}
        if heapcache is None:
            heapcache = {}
        if new_unions is None:
            new_unions = unionfind.UnionFind()
        self.purecache = purecache
        self.heapcache = heapcache
        self.variable_families = variable_families
        self.analyzer = analyzer
        self.new_unions = new_unions

    def copy(self):
        return Cache(
                self.variable_families, self.analyzer, self.new_unions,
                self.purecache.copy(),
                self.heapcache.copy())

    def _var_rep(self, var):
        var = self.new_unions.find_rep(var)
        return self.variable_families.find_rep(var)

    def _key_with_replacement(self, key, index, var):
        (opname, concretetype, args) = key
        listargs = list(args)
        listargs[index] = self._var_rep(var)
        return (opname, concretetype, tuple(listargs))

    def _find_new_res(self, results):
        # helper function for _merge_results
        first = self._var_rep(results[0])
        newres = None
        for result in results:
            if newres is None and isinstance(result, Variable):
                # some extra work to get nice var names
                newres = result.copy()
            result = self._var_rep(result)
            if result != first:
                break
        else:
            # all the same!
            return first, False
        if newres is None:
            newres = Variable()
            newres.concretetype = first.concretetype
        return newres, True

    def _merge_results(self, tuples, results, backedges):
        assert len(results) == len(tuples)
        newres, needs_adding = self._find_new_res(results)
        if not needs_adding:
            return newres
        for linkindex, (link, _) in enumerate(tuples):
            link.args.append(results[linkindex])
        tuples[0][0].target.inputargs.append(newres)
        for backedge in backedges:
            backedge.args.append(newres)
        return newres

    def merge(self, firstlink, tuples, backedges):
        purecache = {}
        block = firstlink.target
        # copy all operations that exist in *all* blocks over. need to add a new
        # inputarg if the result is really a variable

        # note that a backedge is not a problem for regular pure operations:
        # since the argument is a phi node iff it is not loop invariant,
        # copying things over is always save (yay SSA form!)

        # try non-straight merges
        for argindex in range(len(block.inputargs)):
            inputarg = block.inputargs[argindex]
            # bit slow, but probably ok
            firstlinkarg = self._var_rep(firstlink.args[argindex])
            for key, res in self.purecache.iteritems():
                (opname, concretetype, args) = key
                if self._var_rep(args[0]) != firstlinkarg: # XXX other args
                    continue
                results = [res]
                for linkindex, (link, cache) in enumerate(tuples):
                    if linkindex == 0:
                        continue
                    newkey = cache._key_with_replacement(
                            key, 0, link.args[argindex])
                    otherres = cache.purecache.get(newkey, None)
                    if otherres is None:
                        break
                    results.append(otherres)
                else:
                    newkey = self._key_with_replacement(
                            key, 0, inputarg)
                    newres = self._merge_results(tuples, results, backedges)
                    purecache[newkey] = newres

        for key, res in self.purecache.iteritems():
            # "straight" merge: the variable is in all other caches
            results = [res]
            for link, cache in tuples[1:]:
                val = cache.purecache.get(key, None)
                if val is None:
                    break
                results.append(val)
            else:
                newres = self._merge_results(tuples, results, backedges)
                purecache[key] = newres

        # ______________________
        # merge heapcache
        heapcache = {}

        # try non-straight merges
        for argindex in range(len(block.inputargs)):
            inputarg = block.inputargs[argindex]
            # bit slow, but probably ok
            firstlinkarg = self._var_rep(firstlink.args[argindex])
            for key, res in self.heapcache.iteritems():
                (arg, concretetype, fieldname) = key
                if self._var_rep(arg) != firstlinkarg:
                    continue
                results = [res]
                for linkindex, (link, cache) in enumerate(tuples):
                    if linkindex == 0:
                        continue
                    otherarg = cache._var_rep(link.args[argindex])
                    newkey = (otherarg, concretetype, fieldname)
                    otherres = cache.heapcache.get(newkey, None)
                    if otherres is None:
                        break
                    results.append(otherres)
                else:
                    newkey = (self._var_rep(inputarg), concretetype, fieldname)
                    newres = self._merge_results(tuples, results, backedges)
                    heapcache[newkey] = newres

        # regular merge
        for key, res in self.heapcache.iteritems():
            results = [res]
            for link, cache in tuples[1:]:
                val = cache.heapcache.get(key, None)
                if val is None:
                    break
                results.append(val)
            else:
                newres = self._merge_results(tuples, results, backedges)
                heapcache[key] = newres
        return Cache(
                self.variable_families, self.analyzer, self.new_unions,
                purecache, heapcache)

    def _clear_heapcache_for(self, concretetype, fieldname):
        for k in self.heapcache.keys():
            if k[1] == concretetype and k[2] == fieldname:
                del self.heapcache[k]

    def _clear_heapcache_for_effects_of_op(self, op):
        if not self.heapcache:
            return
        effects = self.analyzer.analyze(op)
        self._clear_heapcache_for_effects(effects)

    def _clear_heapcache_for_effects(self, effects):
        if self.analyzer.is_top_result(effects):
            self.heapcache.clear()
        else:
            for k in self.heapcache.keys():
                # XXX slow
                key = ('struct', k[1], k[2])
                if key in effects:
                    del self.heapcache[k]

    def _clear_heapcache_for_loop_blocks(self, blocks):
        # XXX use result builder
        effects = self.analyzer.bottom_result()
        for block in blocks:
            for op in block.operations:
                effects = self.analyzer.join_two_results(
                    effects, self.analyzer.analyze(op))
        self._clear_heapcache_for_effects(effects)

    def _replace_with_result(self, op, res):
        assert op.result.concretetype == res.concretetype
        op.opname = 'same_as'
        op.args = [res]
        self.new_unions.union(res, op.result)

    def cse_block(self, block):
        def representative_arg(arg):
            if isinstance(arg, Variable):
                return self._var_rep(arg)
            return arg
        added_same_as = 0
        for op in block.operations:
            # heap operations
            if op.opname == 'getfield':
                fieldname = op.args[1].value
                concretetype = op.args[0].concretetype
                arg0 = representative_arg(op.args[0])
                tup = (arg0, op.args[0].concretetype, fieldname)
                res = self.heapcache.get(tup, None)
                if res is not None:
                    self._replace_with_result(op, res)
                    added_same_as += 1
                else:
                    self.heapcache[tup] = op.result
                continue
            if op.opname == 'setfield':
                # XXX check whether value is the same already
                concretetype = op.args[0].concretetype
                target = representative_arg(op.args[0])
                fieldname = op.args[1].value
                self._clear_heapcache_for(concretetype, fieldname)
                self.heapcache[target, concretetype, fieldname] = op.args[2]
                continue
            if has_side_effects(op):
                self._clear_heapcache_for_effects_of_op(op)
                continue

            # foldable operations
            if not can_fold(op):
                continue
            key = (op.opname, op.result.concretetype,
                   tuple([representative_arg(arg) for arg in op.args]))
            res = self.purecache.get(key, None)
            if res is not None:
                self._replace_with_result(op, res)
                added_same_as += 1
            else:
                self.purecache[key] = op.result
            if op.opname == "cast_pointer":
                # cast_pointer is a pretty strange operation! it introduces
                # more aliases, that confuse the CSE pass. Therefore we unify
                # the two variables in new_unions, to improve the folding.
                self.new_unions.union(op.args[0], op.result)
        return added_same_as

def _merge(tuples, variable_families, analyzer, loop_blocks, backedges):
    if not tuples:
        return Cache(variable_families, analyzer)
    if len(tuples) == 1:
        (link, cache), = tuples
        result = cache.copy()
    else:
        firstlink, firstcache = tuples[0]
        result = firstcache.merge(firstlink, tuples, backedges)
    if loop_blocks:
        # for all blocks in the loop, clean the heapcache for their effects
        # that way, loop-invariant reads can be removed, if no one writes to
        # anything that can alias with them.
        result._clear_heapcache_for_loop_blocks(loop_blocks)
    return result

def loop_blocks(graph):
    loop_blocks = support.find_loop_blocks(graph)
    result = {}
    for loop_block, start in loop_blocks.iteritems():
        result.setdefault(start, []).append(loop_block)
    return result

class CSE(object):
    def __init__(self, translator):
        self.translator = translator
        self.analyzer = WriteAnalyzer(translator)

    def transform(self, graph):
        variable_families = ssa.DataFlowFamilyBuilder(graph).get_variable_families()
        entrymap = mkentrymap(graph)
        loops = loop_blocks(graph)
        backedges = support.find_backedges(graph)
        todo = collections.deque([graph.startblock])
        caches_to_merge = collections.defaultdict(list)
        done = set()

        added_same_as = 0

        while todo:
            block = todo.popleft()
            assert block not in done

            current_backedges = [link for link in entrymap[block]
                                    if link in backedges]

            if not block.is_final_block():
                cache = _merge(
                    caches_to_merge[block], variable_families, self.analyzer,
                    loops.get(block, None), current_backedges)
                added_same_as += cache.cse_block(block)
            else:
                cache = Cache(variable_families, self.analyzer)
            done.add(block)
            # add all target blocks where all predecessors are already done
            for exit in block.exits:
                for lnk in entrymap[exit.target]:
                    if lnk.prevblock not in done and lnk not in backedges:
                        break
                else:
                    if exit.target not in done and exit.target not in todo: # XXX
                        todo.append(exit.target)
                caches_to_merge[exit.target].append((exit, cache))
        simplify.transform_dead_op_vars(graph)
        if added_same_as:
            ssa.SSA_to_SSI(graph)
            removenoops.remove_same_as(graph)
            constfold.constant_fold_graph(graph) # make use of extra constants
        simplify.transform_dead_op_vars(graph)
        if added_same_as:
            if self.translator.config.translation.verbose:
                log.cse("cse removed %s ops in graph %s" % (added_same_as, graph))
            else:
                log.dot()
        return added_same_as

