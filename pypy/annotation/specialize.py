# specialization support
import types
from pypy.tool.uid import uid
from pypy.objspace.flow.model import Block, Link, Variable, SpaceOperation
from pypy.objspace.flow.model import Constant, checkgraph

def default_specialize(funcdesc, args_s):
    argnames, vararg, kwarg = funcdesc.signature
    assert not kwarg, "functions with ** arguments are not supported"
    if vararg:
        from pypy.annotation import model as annmodel
        # calls to *arg functions: create one version per number of args
        assert len(args_s) == len(argnames) + 1
        s_tuple = args_s[-1]
        assert isinstance(s_tuple, annmodel.SomeTuple), (
            "calls f(..., *arg) require 'arg' to be a tuple")
        s_len = s_tuple.len()
        assert s_len.is_constant(), "calls require known number of args"
        nb_extra_args = s_len.const
        
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
        
        return funcdesc.cachedgraph(nb_extra_args,
                                    alt_name='%s_star%d' % (funcdesc.name,
                                                            nb_extra_args),
                                    builder=builder)
    else:
        return funcdesc.cachedgraph(None)

# ____________________________________________________________________________
# specializations

def memo(funcdesc, arglist_s):
    """NOT_RPYTHON"""
    from pypy.annotation.model import SomePBC, SomeImpossibleValue
    # call the function now, and collect possible results
    for s in arglist_s:
        if not isinstance(s, SomePBC):
            if isinstance(s, SomeImpossibleValue):
                return s    # we will probably get more possible args later
            raise Exception("memo call: argument must be a class or a frozen "
                            "PBC, got %r" % (s,))
    if len(arglist_s) != 1:
        raise Exception("memo call: only 1 argument functions supported"
                        " at the moment (%r)" % (funcdesc,))
    s, = arglist_s
    from pypy.annotation.model import SomeImpossibleValue
    func = funcdesc.pyobj
    if func is None:
        raise Exception("memo call: no Python function object to call (%r)" %
                        (funcdesc,))
    return memo1(funcdesc, func, s)

# XXX OBSCURE to support methodmemo()... needs to find something more 
#     reasonable :-(
KEY_NUMBERS = {}

def memo1(funcdesc, func, s, key='memo1'):
    from pypy.annotation.model import SomeImpossibleValue
    # compute the concrete results and store them directly on the descs,
    # using a strange attribute name
    num = KEY_NUMBERS.setdefault(key, len(KEY_NUMBERS))
    attrname = '$memo%d_%d_%s' % (uid(funcdesc), num, funcdesc.name)
    for desc in s.descriptions:
        s_result = desc.s_read_attribute(attrname)
        if isinstance(s_result, SomeImpossibleValue):
            # first time we see this 'desc'
            if desc.pyobj is None:
                raise Exception("memo call with a class or PBC that has no "
                                "corresponding Python object (%r)" % (desc,))
            result = func(desc.pyobj)
            desc.create_new_attribute(attrname, result)
    # get or build the graph of the function that reads this strange attr
    def memoized(x, y=None):
        return getattr(x, attrname)
    def builder(translator, func):
        return translator.buildflowgraph(memoized)   # instead of 'func'
    return funcdesc.cachedgraph(key, alt_name='memo_%s' % funcdesc.name, 
                                     builder=builder)

def methodmemo(funcdesc, arglist_s):
    """NOT_RPYTHON"""
    from pypy.annotation.model import SomePBC, SomeImpossibleValue
    # call the function now, and collect possible results
    for s in arglist_s:
        if not isinstance(s, SomePBC):
            if isinstance(s, SomeImpossibleValue):
                return s    # we will probably get more possible args later
            raise Exception("method-memo call: argument must be a class or"
                            " a frozen PBC, got %r" % (s,))
    if len(arglist_s) != 2:
        raise Exception("method-memo call: expected  2 arguments function" 
                        " at the moment (%r)" % (funcdesc,))
    from pypy.annotation.model import SomeImpossibleValue
    from pypy.annotation.description import FrozenDesc
    func = funcdesc.pyobj
    if func is None:
        raise Exception("method-memo call: no Python function object to call"
                        " (%r)" % (funcdesc,))
    # compute the concrete results and store them directly on the descs,
    # using a strange attribute name.  The goal is to store in the pbcs of
    # 's1' under the common 'attrname' a reader function; each reader function
    # will read a field 'attrname2' from the pbcs of 's2', where 'attrname2'
    # differs for each pbc of 's1'. This is all specialized also
    # considering the type of s1 to support return value 
    # polymorphism.
    s1, s2 = arglist_s
    s1_type = s1.knowntype
    if s2.is_constant():
        return memo1(funcdesc, lambda val1: func(val1, s2.const),
                    s1, ('memo1of2', s1_type, Constant(s2.const)))
    memosig = "%d_%d_%s" % (uid(funcdesc), uid(s1_type), funcdesc.name)

    attrname = '$memoreader%s' % memosig 
    for desc1 in s1.descriptions:
        attrname2 = '$memofield%d_%s' % (uid(desc1), memosig)
        s_reader = desc1.s_read_attribute(attrname)
        if isinstance(s_reader, SomeImpossibleValue):
            # first time we see this 'desc1': sanity-check 'desc1' and
            # create its reader function
            assert isinstance(desc1, FrozenDesc), (
                "XXX not implemented: memo call with a class as first arg")
            if desc1.pyobj is None:
                raise Exception("method-memo call with a class or PBC"
                                " that has no "
                                "corresponding Python object (%r)" % (desc1,))
            def reader(y, attrname2=attrname2):
                return getattr(y, attrname2)
            desc1.create_new_attribute(attrname, reader)
        for desc2 in s2.descriptions:
            s_result = desc2.s_read_attribute(attrname2)
            if isinstance(s_result, SomeImpossibleValue):
                # first time we see this 'desc1+desc2' combination
                if desc2.pyobj is None:
                    raise Exception("method-memo call with a class or PBC"
                                  " that has no "
                                  "corresponding Python object (%r)" % (desc2,))
                # concrete call, to get the concrete result
                result = func(desc1.pyobj, desc2.pyobj)
                #print 'func(%s, %s) -> %s' % (desc1.pyobj, desc2.pyobj, result)
                #print 'goes into %s.%s'% (desc2,attrname2)
                #print 'with reader %s.%s'% (desc1,attrname)
                desc2.create_new_attribute(attrname2, result)
    # get or build the graph of the function that reads this indirect
    # settings of attributes
    def memoized(x, y):
        reader_fn = getattr(x, attrname)
        return reader_fn(y)
    def builder(translator, func):
        return translator.buildflowgraph(memoized)   # instead of 'func'
    return funcdesc.cachedgraph(s1_type, alt_name='memo_%s' % funcdesc.name, 
                                         builder=builder)

def argvalue(i):
    def specialize_argvalue(funcdesc, args_s):
        key = args_s[i].const
        return funcdesc.cachedgraph(key)        
    return specialize_argvalue

def argtype(i):
    def specialize_argtype(funcdesc, args_s):
        key = args_s[i].knowntype
        return funcdesc.cachedgraph(key)        
    return specialize_argtype

def arglistitemtype(i):
    def specialize_arglistitemtype(funcdesc, args_s):
        s = args_s[i]
        if s.knowntype is not list:
            key = None
        else:
            key = s.listdef.listitem.s_value.knowntype
        return funcdesc.cachedgraph(key)        
    return specialize_arglistitemtype
