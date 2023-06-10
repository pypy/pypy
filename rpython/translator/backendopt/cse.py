from rpython.tool.algo.unionfind import UnionFind
from rpython.rtyper.lltypesystem.lloperation import llop
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

def can_fold(op):
    if getattr(llop, op.opname).canfold:
        return True
    if op.opname == "getfield":
        field = op.args[1].value
        return op.args[0].concretetype.TO._immutable_field(field)
    return False


class Cache(object):
    def __init__(self, purecache=None, heapcache=None):
        if purecache is None:
            purecache = {}
        if heapcache is None:
            heapcache = {}
        # (opname, concretetype of result, args) -> previous (life) result
        self.purecache = purecache
        self.heapcache = heapcache
        self.variable_families = UnionFind()

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
        for (op, concretetype, args), res in self.purecache.iteritems():
            args = tuple([_translate_arg(arg) for arg in args])
            purecache[op, concretetype, args] = _translate_arg(res)
        return Cache(purecache, heapcache)

    def clear_for(self, concretetype, fieldname):
        for k in self.heapcache.keys():
            if k[0].concretetype == concretetype and k[1] == fieldname:
                del self.heapcache[k]

    def _replace_with(self, op, res):
        op.opname = 'same_as'
        op.args = [res]
        self.variable_families.union(res, op.result)

    def _var_rep(self, var):
        # return the representative variable for var. All variables that must
        # be equal to each other always have the same representative. The
        # representative's definition dominates the use of all variables that
        # it represents. casted pointers are considered the same objects.
        # NB: it's very important to use _var_rep only when computing keys in
        # the *cache dictionaries, never to actually put any new variable into
        # the graph, because the concretetypes can change when calling
        # _var_rep.
        if not isinstance(var, Variable):
            return var
        return self.variable_families.find_rep(var)

    def is_const(self, arg, val):
        arg = self._var_rep(arg)
        return isinstance(arg, Constant) and arg == Constant(val, arg.concretetype)

    def cse_block(self, block, inputlink):
        number_same_as = 0
        for op in block.operations:
            # do a bunch of arithmetic rewrites
            if op.opname == "int_add":
                if self.is_const(op.args[0], 0):
                    self._replace_with(op, op.args[1])
                    continue
                if self.is_const(op.args[1], 0):
                    self._replace_with(op, op.args[0])
                    continue
            elif op.opname == "int_mul":
                if self.is_const(op.args[0], 1):
                    self._replace_with(op, op.args[1])
                    continue
                if self.is_const(op.args[1], 1):
                    self._replace_with(op, op.args[0])
                    continue
            elif op.opname == "int_sub":
                if self.is_const(op.args[1], 0):
                    self._replace_with(op, op.args[0])
                    continue
                if self._var_rep(op.args[0]) == self._var_rep(op.args[1]):
                    self._replace_with(op, Constant(0, op.result.concretetype))
            elif op.opname == "int_and":
                if self.is_const(op.args[0], 0):
                    self._replace_with(op, op.args[0])
                    continue
                if self.is_const(op.args[1], 0):
                    self._replace_with(op, op.args[1])
                    continue
            elif op.opname == "int_or":
                if self.is_const(op.args[0], 0):
                    self._replace_with(op, op.args[1])
                    continue
                if self.is_const(op.args[1], 0):
                    self._replace_with(op, op.args[0])
                    continue

            if op.opname == "cast_pointer":
                # cast_pointer is a pretty strange operation! it introduces
                # more aliases, that confuse the CSE pass. Therefore we unify
                # the two variables in variable_families, to improve the
                # folding.
                self.variable_families.union(op.args[0], op.result)
                # don't do anything further
                continue
            elif can_fold(op):
                key = (op.opname, op.result.concretetype,
                       tuple([self._var_rep(arg) for arg in op.args]))
                res = self.purecache.get(key, None)
                if res is not None:
                    self._replace_with(op, res)
                    number_same_as += 1
                else:
                    self.purecache[key] = op.result
            elif op.opname == 'getfield':
                key = (self._var_rep(op.args[0]), op.args[1].value)
                res = self.heapcache.get(key, None)
                if res is not None:
                    self._replace_with(op, res)
                    number_same_as += 1
                else:
                    self.heapcache[key] = op.result
            elif op.opname in ('setarrayitem', 'setinteriorfield', "malloc", "malloc_varsize"):
                pass
            elif op.opname == 'setfield':
                field = op.args[1].value
                if op.args[0].concretetype.TO._immutable_field(field):
                    # it's an initializing store
                    key = ('getfield', op.args[2].concretetype,
                           (self._var_rep(op.args[0]), self._var_rep(op.args[1])))
                    self.purecache[key] = op.args[2]
                else:
                    self.clear_for(op.args[0].concretetype, field)
                    target = self._var_rep(op.args[0])
                    self.heapcache[target, field] = op.args[2]
            elif has_side_effects(op):
                self.heapcache.clear()
        return number_same_as

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

