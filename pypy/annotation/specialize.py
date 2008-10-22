# specialization support
import py
from pypy.tool.uid import uid
from pypy.tool.sourcetools import func_with_new_name
from pypy.tool.algo.unionfind import UnionFind
from pypy.objspace.flow.model import Block, Link, Variable, SpaceOperation
from pypy.objspace.flow.model import Constant, checkgraph
from pypy.annotation import model as annmodel

def flatten_star_args(funcdesc, args_s):
    argnames, vararg, kwarg = funcdesc.signature
    assert not kwarg, "functions with ** arguments are not supported"
    if vararg:
        # calls to *arg functions: create one version per number of args
        assert len(args_s) == len(argnames) + 1
        s_tuple = args_s[-1]
        assert isinstance(s_tuple, annmodel.SomeTuple), (
            "calls f(..., *arg) require 'arg' to be a tuple")
        s_len = s_tuple.len()
        assert s_len.is_constant(), "calls require known number of args"
        nb_extra_args = s_len.const
        flattened_s = list(args_s[:-1])
        flattened_s.extend(s_tuple.items)
        
        def builder(translator, func):
            # build a hacked graph that doesn't take a *arg any more, but
            # individual extra arguments
            graph = translator.buildflowgraph(func)
            argnames, vararg, kwarg = graph.signature
            assert vararg, "graph should have a *arg at this point"
            assert not kwarg, "where does this **arg come from??"
            argscopy = [Variable(v) for v in graph.getargs()]
            starargs = [Variable('stararg%d'%i) for i in range(nb_extra_args)]
            newstartblock = Block(argscopy[:-1] + starargs)
            newtup = SpaceOperation('newtuple', starargs, argscopy[-1])
            newstartblock.operations.append(newtup)
            newstartblock.closeblock(Link(argscopy, graph.startblock))
            graph.startblock.isstartblock = False
            graph.startblock = newstartblock
            newstartblock.isstartblock = True
            argnames += tuple(['.star%d' % i for i in range(nb_extra_args)])
            graph.signature = argnames, None, None
            # note that we can mostly ignore defaults: if nb_extra_args > 0, 
            # then defaults aren't applied.  if nb_extra_args == 0, then this 
            # just removes the *arg and the defaults keep their meaning.
            if nb_extra_args > 0:
                graph.defaults = None   # shouldn't be used in this case
            checkgraph(graph)
            return graph

        key = nb_extra_args
        name_suffix = '_star%d' % (nb_extra_args,)
        return flattened_s, key, name_suffix, builder

    else:
        return args_s, None, '', None

def default_specialize(funcdesc, args_s):
    # first flatten the *args
    args_s, key, name_suffix, builder = flatten_star_args(funcdesc, args_s)
    # two versions: a regular one and one for instances with 'access_directly'
    for s_obj in args_s:
        if (isinstance(s_obj, annmodel.SomeInstance) and
            'access_directly' in s_obj.flags):
            key = (AccessDirect, key)
            name_suffix += '_AccessDirect'
            break
    # done
    if name_suffix:
        alt_name = '%s%s' % (funcdesc.name, name_suffix)
    else:
        alt_name = None
    return funcdesc.cachedgraph(key, alt_name=alt_name, builder=builder)

class AccessDirect(object):
    """marker for specialization: set when any arguments is a SomeInstance
    which has the 'access_directly' flag set."""

def getuniquenondirectgraph(desc):
    result = []
    for key, graph in desc._cache.items():
        if (type(key) is tuple and len(key) == 2 and
            key[0] is AccessDirect):
            continue
        result.append(graph)
    assert len(result) == 1
    return result[0]
        

# ____________________________________________________________________________
# specializations

class MemoTable:
    def __init__(self, funcdesc, args, value):
        self.funcdesc = funcdesc
        self.table = {args: value}
        self.graph = None
        self.do_not_process = False

    def register_finish(self):
        bookkeeper = self.funcdesc.bookkeeper
        bookkeeper.pending_specializations.append(self.finish)

    def absorb(self, other):
        self.table.update(other.table)
        self.graph = None   # just in case
        other.do_not_process = True

    fieldnamecounter = 0

    def getuniquefieldname(self):
        name = self.funcdesc.name
        fieldname = '$memofield_%s_%d' % (name, MemoTable.fieldnamecounter)
        MemoTable.fieldnamecounter += 1
        return fieldname

    def finish(self):
        if self.do_not_process:
            return
        from pypy.annotation.model import unionof
        assert self.graph is None, "MemoTable already finished"
        # list of which argument positions can take more than one value
        example_args, example_value = self.table.iteritems().next()
        nbargs = len(example_args)
        # list of sets of possible argument values -- one set per argument index
        sets = [{} for i in range(nbargs)]
        for args in self.table:
            for i in range(nbargs):
                sets[i][args[i]] = True

        bookkeeper = self.funcdesc.bookkeeper
        annotator = bookkeeper.annotator
        name = self.funcdesc.name
        argnames = ['a%d' % i for i in range(nbargs)]

        def make_helper(firstarg, stmt, miniglobals):
            header = "def f(%s):" % (', '.join(argnames[firstarg:],))
            source = py.code.Source(stmt)
            source = source.putaround(header)
            exec source.compile() in miniglobals
            f = miniglobals['f']
            return func_with_new_name(f, 'memo_%s_%d' % (name, firstarg))

        def make_constant_subhelper(firstarg, result):
            # make a function that just returns the constant answer 'result'
            f = make_helper(firstarg, 'return result', {'result': result})
            f.constant_result = result
            return f

        def make_subhelper(args_so_far=()):
            firstarg = len(args_so_far)
            if firstarg == nbargs:
                # no argument left, return the known result
                # (or a dummy value if none corresponds exactly)
                result = self.table.get(args_so_far, example_value)
                return make_constant_subhelper(firstarg, result)
            else:
                nextargvalues = list(sets[len(args_so_far)])
                if nextargvalues == [True, False]:
                    nextargvalues = [False, True]
                nextfns = [make_subhelper(args_so_far + (arg,))
                           for arg in nextargvalues]
                # do all graphs return a constant?
                try:
                    constants = [fn.constant_result for fn in nextfns]
                except AttributeError:
                    constants = None    # one of the 'fn' has no constant_result
                restargs = ', '.join(argnames[firstarg+1:])

                # is there actually only one possible value for the current arg?
                if len(nextargvalues) == 1:
                    if constants:   # is the result a constant?
                        result = constants[0]
                        return make_constant_subhelper(firstarg, result)
                    else:
                        # ignore the first argument and just call the subhelper
                        stmt = 'return subhelper(%s)' % restargs
                        return make_helper(firstarg, stmt,
                                           {'subhelper': nextfns[0]})

                # is the arg a bool?
                elif nextargvalues == [False, True]:
                    fieldname0 = self.getuniquefieldname()
                    fieldname1 = self.getuniquefieldname()
                    stmt = ['if %s:' % argnames[firstarg]]
                    if hasattr(nextfns[True], 'constant_result'):
                        # the True branch has a constant result
                        case1 = nextfns[True].constant_result
                        stmt.append('    return case1')
                    else:
                        # must call the subhelper
                        case1 = nextfns[True]
                        stmt.append('    return case1(%s)' % restargs)
                    stmt.append('else:')
                    if hasattr(nextfns[False], 'constant_result'):
                        # the False branch has a constant result
                        case0 = nextfns[False].constant_result
                        stmt.append('    return case0')
                    else:
                        # must call the subhelper
                        case0 = nextfns[False]
                        stmt.append('    return case0(%s)' % restargs)

                    return make_helper(firstarg, '\n'.join(stmt),
                                       {'case0': case0,
                                        'case1': case1})

                # the arg is a set of PBCs
                else:
                    descs = [bookkeeper.getdesc(pbc) for pbc in nextargvalues]
                    fieldname = self.getuniquefieldname()
                    stmt = 'return getattr(%s, %r)' % (argnames[firstarg],
                                                       fieldname)
                    if constants:
                        # instead of calling these subhelpers indirectly,
                        # we store what they would return directly in the
                        # pbc memo fields
                        store = constants
                    else:
                        store = nextfns
                        # call the result of the getattr()
                        stmt += '(%s)' % restargs

                    # store the memo field values
                    for desc, value_to_store in zip(descs, store):
                        desc.create_new_attribute(fieldname, value_to_store)

                    return make_helper(firstarg, stmt, {})

        entrypoint = make_subhelper(args_so_far = ())
        self.graph = annotator.translator.buildflowgraph(entrypoint)
        self.graph.defaults = self.funcdesc.defaults

        # schedule this new graph for being annotated
        args_s = []
        for set in sets:
            values_s = [bookkeeper.immutablevalue(x) for x in set]
            args_s.append(unionof(*values_s))
        annotator.addpendinggraph(self.graph, args_s)


def memo(funcdesc, arglist_s):
    from pypy.annotation.model import SomePBC, SomeImpossibleValue, SomeBool
    from pypy.annotation.model import unionof
    # call the function now, and collect possible results
    argvalues = []
    for s in arglist_s:
        if s.is_constant():
            values = [s.const]
        elif isinstance(s, SomePBC):
            values = []
            assert not s.can_be_None, "memo call: cannot mix None and PBCs"
            for desc in s.descriptions:
                if desc.pyobj is None:
                    raise Exception("memo call with a class or PBC that has no "
                                   "corresponding Python object (%r)" % (desc,))
                values.append(desc.pyobj)
        elif isinstance(s, SomeImpossibleValue):
            return s    # we will probably get more possible args later
        elif isinstance(s, SomeBool):
            values = [False, True]
        else:
            raise Exception("memo call: argument must be a class or a frozen "
                            "PBC, got %r" % (s,))
        argvalues.append(values)
    # the list of all possible tuples of arguments to give to the memo function
    possiblevalues = cartesian_product(argvalues)

    # a MemoTable factory -- one MemoTable per family of arguments that can
    # be called together, merged via a UnionFind.
    bookkeeper = funcdesc.bookkeeper
    try:
        memotables = bookkeeper.all_specializations[funcdesc]
    except KeyError:
        func = funcdesc.pyobj
        if func is None:
            raise Exception("memo call: no Python function object to call "
                            "(%r)" % (funcdesc,))

        def compute_one_result(args):
            value = func(*args)
            memotable = MemoTable(funcdesc, args, value)
            memotable.register_finish()
            return memotable

        memotables = UnionFind(compute_one_result)
        bookkeeper.all_specializations[funcdesc] = memotables

    # merge the MemoTables for the individual argument combinations
    firstvalues = possiblevalues.next()
    _, _, memotable = memotables.find(firstvalues)
    for values in possiblevalues:
        _, _, memotable = memotables.union(firstvalues, values)

    if memotable.graph is not None:
        return memotable.graph   # if already computed
    else:
        # otherwise, for now, return the union of each possible result
        return unionof(*[bookkeeper.immutablevalue(v)
                         for v in memotable.table.values()])

def cartesian_product(lstlst):
    if not lstlst:
        yield ()
        return
    for tuple_tail in cartesian_product(lstlst[1:]):
        for value in lstlst[0]:
            yield (value,) + tuple_tail

##    """NOT_RPYTHON"""
##    if len(arglist_s) != 1:
##        raise Exception("memo call: only 1 argument functions supported"
##                        " at the moment (%r)" % (funcdesc,))
##    s, = arglist_s
##    from pypy.annotation.model import SomeImpossibleValue
##    return memo1(funcdesc, func, s)

### XXX OBSCURE to support methodmemo()... needs to find something more 
###     reasonable :-(
##KEY_NUMBERS = {}

##def memo1(funcdesc, func, s, key='memo1'):
##    from pypy.annotation.model import SomeImpossibleValue
##    # compute the concrete results and store them directly on the descs,
##    # using a strange attribute name
##    num = KEY_NUMBERS.setdefault(key, len(KEY_NUMBERS))
##    attrname = '$memo%d_%d_%s' % (uid(funcdesc), num, funcdesc.name)
##    for desc in s.descriptions:
##        s_result = desc.s_read_attribute(attrname)
##        if isinstance(s_result, SomeImpossibleValue):
##            # first time we see this 'desc'
##            if desc.pyobj is None:
##                raise Exception("memo call with a class or PBC that has no "
##                                "corresponding Python object (%r)" % (desc,))
##            result = func(desc.pyobj)
##            desc.create_new_attribute(attrname, result)
##    # get or build the graph of the function that reads this strange attr
##    def memoized(x, y=None):
##        return getattr(x, attrname)
##    def builder(translator, func):
##        return translator.buildflowgraph(memoized)   # instead of 'func'
##    return funcdesc.cachedgraph(key, alt_name='memo_%s' % funcdesc.name, 
##                                     builder=builder)

##def methodmemo(funcdesc, arglist_s):
##    """NOT_RPYTHON"""
##    from pypy.annotation.model import SomePBC, SomeImpossibleValue
##    # call the function now, and collect possible results
##    for s in arglist_s:
##        if not isinstance(s, SomePBC):
##            if isinstance(s, SomeImpossibleValue):
##                return s    # we will probably get more possible args later
##            raise Exception("method-memo call: argument must be a class or"
##                            " a frozen PBC, got %r" % (s,))
##    if len(arglist_s) != 2:
##        raise Exception("method-memo call: expected  2 arguments function" 
##                        " at the moment (%r)" % (funcdesc,))
##    from pypy.annotation.model import SomeImpossibleValue
##    from pypy.annotation.description import FrozenDesc
##    func = funcdesc.pyobj
##    if func is None:
##        raise Exception("method-memo call: no Python function object to call"
##                        " (%r)" % (funcdesc,))
##    # compute the concrete results and store them directly on the descs,
##    # using a strange attribute name.  The goal is to store in the pbcs of
##    # 's1' under the common 'attrname' a reader function; each reader function
##    # will read a field 'attrname2' from the pbcs of 's2', where 'attrname2'
##    # differs for each pbc of 's1'. This is all specialized also
##    # considering the type of s1 to support return value 
##    # polymorphism.
##    s1, s2 = arglist_s
##    s1_type = s1.knowntype
##    if s2.is_constant():
##        return memo1(funcdesc, lambda val1: func(val1, s2.const),
##                    s1, ('memo1of2', s1_type, Constant(s2.const)))
##    memosig = "%d_%d_%s" % (uid(funcdesc), uid(s1_type), funcdesc.name)

##    attrname = '$memoreader%s' % memosig 
##    for desc1 in s1.descriptions:
##        attrname2 = '$memofield%d_%s' % (uid(desc1), memosig)
##        s_reader = desc1.s_read_attribute(attrname)
##        if isinstance(s_reader, SomeImpossibleValue):
##            # first time we see this 'desc1': sanity-check 'desc1' and
##            # create its reader function
##            assert isinstance(desc1, FrozenDesc), (
##                "XXX not implemented: memo call with a class as first arg")
##            if desc1.pyobj is None:
##                raise Exception("method-memo call with a class or PBC"
##                                " that has no "
##                                "corresponding Python object (%r)" % (desc1,))
##            def reader(y, attrname2=attrname2):
##                return getattr(y, attrname2)
##            desc1.create_new_attribute(attrname, reader)
##        for desc2 in s2.descriptions:
##            s_result = desc2.s_read_attribute(attrname2)
##            if isinstance(s_result, SomeImpossibleValue):
##                # first time we see this 'desc1+desc2' combination
##                if desc2.pyobj is None:
##                    raise Exception("method-memo call with a class or PBC"
##                                  " that has no "
##                                  "corresponding Python object (%r)" % (desc2,))
##                # concrete call, to get the concrete result
##                result = func(desc1.pyobj, desc2.pyobj)
##                #print 'func(%s, %s) -> %s' % (desc1.pyobj, desc2.pyobj, result)
##                #print 'goes into %s.%s'% (desc2,attrname2)
##                #print 'with reader %s.%s'% (desc1,attrname)
##                desc2.create_new_attribute(attrname2, result)
##    # get or build the graph of the function that reads this indirect
##    # settings of attributes
##    def memoized(x, y):
##        reader_fn = getattr(x, attrname)
##        return reader_fn(y)
##    def builder(translator, func):
##        return translator.buildflowgraph(memoized)   # instead of 'func'
##    return funcdesc.cachedgraph(s1_type, alt_name='memo_%s' % funcdesc.name, 
##                                         builder=builder)

def make_constgraphbuilder(n, v=None, factory=None, srcmodule=None):
    def constgraphbuilder(translator, ignore):
        args = ','.join(["arg%d" % i for i in range(n)])
        if factory is not None:
            computed_v = factory()
        else:
            computed_v = v
        miniglobals = {'v': computed_v, '__name__': srcmodule}
        exec "constf = lambda %s: v" % args in miniglobals
        return translator.buildflowgraph(miniglobals['constf'])
    return constgraphbuilder

def specialize_argvalue(funcdesc, args_s, *argindices):
    from pypy.annotation.model import SomePBC
    key = []
    for i in argindices:
        s = args_s[i]
        if s.is_constant():
            key.append(s.const)
        elif isinstance(s, SomePBC) and len(s.descriptions) == 1:
            # for test_specialize_arg_bound_method
            key.append(s.descriptions.keys()[0])
        else:
            raise Exception("specialize:arg(%d): argument not constant: %r"
                            % (i, s))
    key = tuple(key)
    return funcdesc.cachedgraph(key)

def specialize_argtype(funcdesc, args_s, *argindices):
    key = tuple([args_s[i].knowntype for i in argindices])
    return funcdesc.cachedgraph(key)

def specialize_arglistitemtype(funcdesc, args_s, i):
    s = args_s[i]
    if s.knowntype is not list:
        key = None
    else:
        key = s.listdef.listitem.s_value.knowntype
    return funcdesc.cachedgraph(key)        
