"""
The Bookkeeper class.
"""

from __future__ import generators
import sys
from types import FunctionType, ClassType, MethodType
from types import BuiltinMethodType
from pypy.tool.ansi_print import ansi_print
from pypy.annotation.model import *
from pypy.annotation.classdef import ClassDef, isclassdef
from pypy.annotation.listdef import ListDef, MOST_GENERAL_LISTDEF
from pypy.annotation.dictdef import DictDef, MOST_GENERAL_DICTDEF
from pypy.interpreter.pycode import cpython_code_signature
from pypy.interpreter.argument import Arguments, ArgErr
from pypy.rpython.rarithmetic import r_uint
from pypy.tool.unionfind import UnionFind
from pypy.rpython import lltype

from pypy.annotation.specialize import decide_callable

class PBCAccessSet:
    def __init__(self, obj):
        self.objects = { obj: True }
        self.read_locations = {}
        self.attrs = {}

    def update(self, other):
        self.objects.update(other.objects)
        self.read_locations.update(other.read_locations)        
        self.attrs.update(other.attrs)

class PBCCallFamily:
    def __init__(self, obj):
        self.objects = { obj: True }
        self.patterns = {}

    def update(self, other):
        self.objects.update(other.objects)
        self.patterns.update(other.patterns)

class Stats:

    def __init__(self, bookkeeper):
        self.bookkeeper = bookkeeper
        self.classify = {}

    def count(self, category, *args):
        for_category = self.classify.setdefault(category, {})
        classifier = getattr(self, 'consider_%s' % category)
        outcome = classifier(*args)
        for_category[self.bookkeeper.position_key] = outcome

    def consider_newslice(self, s_start, s_stop, s_step):
        if ((s_start.is_constant() or (isinstance(s_start, SomeInteger) and s_start.nonneg)) and
            (s_stop.is_constant() or (isinstance(s_stop, SomeInteger) and s_stop.nonneg)) and
            (s_step.is_constant() and (s_step.const == 1 or s_step.const == None))):
            return 'proper'
        return 'improper'


class Bookkeeper:
    """The log of choices that have been made while analysing the operations.
    It ensures that the same 'choice objects' will be returned if we ask
    again during reflowing.  Like ExecutionContext, there is an implicit
    Bookkeeper that can be obtained from a thread-local variable.

    Currently used for factories and user-defined classes."""

    def __init__(self, annotator):
        self.annotator = annotator
        self.userclasses = {}    # map classes to ClassDefs
        self.userclasseslist = []# userclasses.keys() in creation order
        self.cachespecializations = {}
        self.pbccache = {}
        self.pbctypes = {}
        self.seen_mutable = {}
        self.listdefs = {}       # map position_keys to ListDefs
        self.dictdefs = {}       # map position_keys to DictDefs
        
        # mapping position -> key, prev_result for specializations
        self.spec_callsite_keys_results = {}

        self.pbc_maximal_access_sets = UnionFind(PBCAccessSet)
        # can be precisely computed only at fix-point, see
        # compute_at_fixpoint
        self.pbc_maximal_call_families = None
        self.pbc_callables = None
        
        self.pbc_call_sites = {}

        self.stats = Stats(self)

        # import ordering hack
        global BUILTIN_ANALYZERS
        from pypy.annotation.builtin import BUILTIN_ANALYZERS

    def count(self, category, *args):
        self.stats.count(category, *args)

    def enter(self, position_key):
        """Start of an operation.
        The operation is uniquely identified by the given key."""
        self.position_key = position_key
        TLS.bookkeeper = self

    def leave(self):
        """End of an operation."""
        del TLS.bookkeeper
        del self.position_key

    def compute_at_fixpoint(self):
        if self.pbc_maximal_call_families is None:
            self.pbc_maximal_call_families = UnionFind(PBCCallFamily)
        if self.pbc_callables is None:
            self.pbc_callables = {}

        for (fn, block, i), shape in self.pbc_call_sites.iteritems():
            spaceop = block.operations[i]
            assert spaceop.opname in ('call_args', 'simple_call')
            pbc = self.annotator.binding(spaceop.args[0], extquery=True)
            self.consider_pbc_call(pbc, shape, spaceop)
        self.pbc_call_sites = {}

    def getclassdef(self, cls):
        """Get the ClassDef associated with the given user cls."""
        if cls is object:
            return None
        try:
            return self.userclasses[cls]
        except KeyError:
            if cls in self.pbctypes:
                self.warning("%r gets a ClassDef, but is the type of some PBC"
                             % (cls,))
            cdef = ClassDef(cls, self)
            self.userclasses[cls] = cdef
            self.userclasseslist.append(cdef)
            return self.userclasses[cls]

    def getlistdef(self, **flags):
        """Get the ListDef associated with the current position."""
        try:
            listdef = self.listdefs[self.position_key]
        except KeyError:
            listdef = self.listdefs[self.position_key] = ListDef(self)
            listdef.listitem.__dict__.update(flags)
        return listdef

    def newlist(self, *s_values, **flags):
        """Make a SomeList associated with the current position, general
        enough to contain the s_values as items."""
        listdef = self.getlistdef(**flags)
        for s_value in s_values:
            listdef.generalize(s_value)
        return SomeList(listdef)

    def getdictdef(self):
        """Get the DictDef associated with the current position."""
        try:
            dictdef = self.dictdefs[self.position_key]
        except KeyError:
            dictdef = self.dictdefs[self.position_key] = DictDef(self)
        return dictdef

    def newdict(self, *items_s):
        """Make a SomeDict associated with the current position, general
        enough to contain the given (s_key, s_value) as items."""
        dictdef = self.getdictdef()
        for s_key, s_value in items_s:
            dictdef.generalize_key(s_key)
            dictdef.generalize_value(s_value)
        return SomeDict(dictdef)

    immutable_cache = {}

    def immutablevalue(self, x):
        """The most precise SomeValue instance that contains the
        immutable value x."""
        # convert unbound methods to the underlying function
        if hasattr(x, 'im_self') and x.im_self is None:
            x = x.im_func
            assert not hasattr(x, 'im_self')
        if x is sys: # special case constant sys to someobject
            return SomeObject()
        tp = type(x)
        if tp is bool:
            result = SomeBool()
        elif tp is int:
            result = SomeInteger(nonneg = x>=0)
        elif tp is r_uint:
            result = SomeInteger(nonneg = True, unsigned = True)
        elif issubclass(tp, str): # py.lib uses annotated str subclasses
            if len(x) == 1:
                result = SomeChar()
            else:
                result = SomeString()
        elif tp is unicode and len(x) == 1:
            result = SomeUnicodeCodePoint()
        elif tp is tuple:
            result = SomeTuple(items = [self.immutablevalue(e) for e in x])
        elif tp is float:
            result = SomeFloat()
        elif tp is list:
            try:
                return self.immutable_cache[id(x)]
            except KeyError:
                result = SomeList(ListDef(self, SomeImpossibleValue()))
                self.immutable_cache[id(x)] = result
                for e in x:
                    result.listdef.generalize(self.immutablevalue(e))
        elif tp is dict:   # exactly a dict
            try:
                return self.immutable_cache[id(x)]
            except KeyError:
                result = SomeDict(DictDef(self, 
                                          SomeImpossibleValue(),
                                          SomeImpossibleValue()))
                self.immutable_cache[id(x)] = result
                for ek, ev in x.iteritems():
                    result.dictdef.generalize_key(self.immutablevalue(ek))
                    result.dictdef.generalize_value(self.immutablevalue(ev))
        elif ishashable(x) and x in BUILTIN_ANALYZERS:
            result = SomeBuiltin(BUILTIN_ANALYZERS[x])
        elif isinstance(x, lltype._ptr):
            result = SomePtr(lltype.typeOf(x))
        elif callable(x) or isinstance(x, staticmethod): # XXX
            # maybe 'x' is a method bound to a not-yet-frozen cache?
            # fun fun fun.
            if hasattr(x, 'im_self') and hasattr(x.im_self, '_freeze_'):
                x.im_self._freeze_()
            if hasattr(x, '__self__') and x.__self__ is not None:
                s_self = self.immutablevalue(x.__self__)
                try:
                    result = s_self.find_method(x.__name__)
                except AttributeError:
                    result = SomeObject()
            else:
                return self.getpbc(x)
        elif hasattr(x, '__class__') \
                 and x.__class__.__module__ != '__builtin__':
            # user-defined classes can define a method _freeze_(), which
            # is called when a prebuilt instance is found.  If the method
            # returns True, the instance is considered immutable and becomes
            # a SomePBC().  Otherwise it's just SomeInstance().
            frozen = hasattr(x, '_freeze_') and x._freeze_()
            if frozen:
                return self.getpbc(x)
            else:
                clsdef = self.getclassdef(x.__class__)
                
                if x not in self.seen_mutable: # avoid circular reflowing, 
                                               # see for example test_circular_mutable_getattr
                    self.seen_mutable[x] = True
                    for attr in x.__dict__:
                        clsdef.add_source_for_attribute(attr, x) # can trigger reflowing
                result = SomeInstance(clsdef)
        elif x is None:
            return self.getpbc(None)
        else:
            result = SomeObject()
        result.const = x
        return result

    def getpbc(self, x):
        try:
            # this is not just an optimization, but needed to avoid
            # infinitely repeated calls to add_source_for_attribute()
            return self.pbccache[x]
        except KeyError:
            result = SomePBC({x: True}) # pre-built inst
            #clsdef = self.getclassdef(new_or_old_class(x))
            #for attr in getattr(x, '__dict__', {}):
            #    clsdef.add_source_for_attribute(attr, x)
            self.pbccache[x] = result
            cls = new_or_old_class(x)
            if cls not in self.pbctypes:
                self.pbctypes[cls] = True
                if cls in self.userclasses:
                    self.warning("making some PBC of type %r, which has "
                                 "already got a ClassDef" % (cls,))
            return result

    def valueoftype(self, t):
        """The most precise SomeValue instance that contains all
        objects of type t."""
        assert isinstance(t, (type, ClassType))
        if t is bool:
            return SomeBool()
        elif t is int:
            return SomeInteger()
        elif t is r_uint:
            return SomeInteger(nonneg = True, unsigned = True)
        elif issubclass(t, str): # py.lib uses annotated str subclasses
            return SomeString()
        elif t is float:
            return SomeFloat()
        elif t is list:
            return SomeList(MOST_GENERAL_LISTDEF)
        elif t is dict:
            return SomeDict(MOST_GENERAL_DICTDEF)
        # can't do tuple
        elif t.__module__ != '__builtin__' and t not in self.pbctypes:
            classdef = self.getclassdef(t)
            return SomeInstance(classdef)
        else:
            o = SomeObject()
            if t != object:
                o.knowntype = t
            return o

    def pbc_getattr(self, pbc, s_attr):
        assert s_attr.is_constant()
        attr = s_attr.const

        access_sets = self.pbc_maximal_access_sets
        objects = pbc.prebuiltinstances.keys()
        access = None
        first = None
        change = False
        
        for obj in objects:
            if obj is not None:
                first = obj
                break

        if first is not None:
            change, rep, access = access_sets.find(objects[0])
            for obj in objects:
                if obj is not None:
                    change1, rep, access = access_sets.union(rep, obj)
                    change = change or change1

            access.attrs[attr] = True
            position = self.position_key
            access.read_locations[position] = True

        actuals = []

        if access:
            for c in access.objects:
                if hasattr(c, attr):
                    actuals.append(self.immutablevalue(getattr(c, attr)))

        if change:
            for position in access.read_locations:
                self.annotator.reflowfromposition(position)
                
        return unionof(*actuals)        

    def consider_pbc_call(self, pbc, shape, spaceop=None, implicit_init=None): # computation done at fix-point
        if not isinstance(pbc, SomePBC):
            return
        
        if implicit_init:
            implicit_init = pbc, implicit_init
            shape = (shape[0]+1,) + shape[1:]
        else:
            implicit_init = None

        pbc, dontcaresc = self.query_spaceop_callable(spaceop,
                                                      implicit_init=implicit_init) 

        nonnullcallables = []
        for func, classdef in pbc.prebuiltinstances.items():
            if func is None:
                continue
            if not isclassdef(classdef): 
                classdef = None

            # if class => consider __init__ too
            if isinstance(func, (type, ClassType)) and \
                    func.__module__ != '__builtin__':
                assert classdef is None
                init_classdef, s_init = self.get_s_init(func)
                if s_init is not None:
                    self.consider_pbc_call(s_init, shape, spaceop, implicit_init=init_classdef) 

            callable = (classdef, func)
            assert not hasattr(func, 'im_func') or func.im_self is not None
            self.pbc_callables.setdefault(func,{})[callable] = True
            nonnullcallables.append(callable)

        if nonnullcallables:
            call_families = self.pbc_maximal_call_families

            dontcare, rep, callfamily = call_families.find(nonnullcallables[0])
            for obj in nonnullcallables:
                    dontcare, rep, callfamily = call_families.union(rep, obj)

            callfamily.patterns.update({shape: True})
 
    def pbc_call(self, pbc, args, implicit_init):
        if not implicit_init:
            fn, block, i = self.position_key
            assert block.operations[i].opname in ('call_args', 'simple_call')
            assert self.annotator.binding(block.operations[i].args[0], extquery=True) is pbc
            
            # extract shape from args
            shape = args.rawshape()
            if self.position_key in self.pbc_call_sites:
                assert self.pbc_call_sites[self.position_key] == shape
            else:
                self.pbc_call_sites[self.position_key] = shape

        results = []
        nonnullcallables = [(func, classdef) for func, classdef in pbc.prebuiltinstances.items()]
        mono = len(nonnullcallables) == 1

        for func, classdef in nonnullcallables:
            if isclassdef(classdef): 
                s_self = SomeInstance(classdef)
                args1 = args.prepend(s_self)
            else:
                args1 = args
            results.append(self.pycall(func, args1, mono))

        return unionof(*results) 

    # decide_callable(position, func, args, mono) -> callb, key
    # query_spaceop_callable(spaceop) -> pbc, isspecialcase
    # get_s_init(decided_cls) -> classdef, s_undecided_init

    def query_spaceop_callable(self, spaceop, implicit_init=None): # -> s_pbc, specialcase
        self.enter(None)
        try:
            if implicit_init is None:
                assert spaceop.opname in ("simple_call", "call_args")
                obj = spaceop.args[0]
                s_obj = self.annotator.binding(obj, extquery=True)
                init_classdef = None
            else:
                s_obj, init_classdef = implicit_init

            assert isinstance(s_obj, SomePBC)
            if len(s_obj.prebuiltinstances) > 1: # no specialization expected
                return s_obj, False

            argsvars = spaceop.args[1:]
            args_s = [self.annotator.binding(v) for v in argsvars]
            args = self.build_args(spaceop.opname, args_s)

            func, classdef = s_obj.prebuiltinstances.items()[0]

            if init_classdef:
                args = args.prepend(SomeInstance(init_classdef))
            elif isclassdef(classdef): 
                s_self = SomeInstance(classdef)
                args = args.prepend(s_self)
            
            func, key = decide_callable(self, spaceop, func, args, mono=True)

            if key is None:
                return s_obj, False

            if func is None: # specialisation computes annotation direclty
                return s_obj, True

            return SomePBC({func: classdef}), False
        finally:
            self.leave()

    def build_args(self, op, args_s):
        space = RPythonCallsSpace()
        if op == "simple_call":
            return Arguments(space, args_s)
        elif op == "call_args":
            return Arguments.fromshape(space, args_s[0].const, # shape
                                       args_s[1:])

    def get_s_init(self, cls):
        classdef = self.getclassdef(cls)
        init = getattr(cls, '__init__', None)
        if init is not None and init != object.__init__:
            # don't record the access of __init__ on the classdef
            # because it is not a dynamic attribute look-up, but
            # merely a static function call
            s_init = self.immutablevalue(init)
            return classdef, s_init
        else:
            return classdef, None
 
    def get_inputcells(self, func, args):
        # parse the arguments according to the function we are calling
        signature = cpython_code_signature(func.func_code)
        defs_s = []
        if func.func_defaults:
            for x in func.func_defaults:
                defs_s.append(self.immutablevalue(x))
        try:
            inputcells = args.match_signature(signature, defs_s)
        except ArgErr, e:
            raise TypeError, "signature mismatch: %s" % e.getmsg(args, func.__name__)

        return inputcells
 

    def pycall(self, func, args, mono):
        if func is None:   # consider None as a NULL function pointer
            return SomeImpossibleValue()

        # decide and pick if necessary a specialized version
        base_func = func
        func, key = decide_callable(self, self.position_key, func, args, mono, unpacked=True)
        
        if func is None:
            assert isinstance(key, SomeObject)
            return key

        func, args = func # method unpacking done by decide_callable
            
        if isinstance(func, (type, ClassType)) and \
            func.__module__ != '__builtin__':
            classdef, s_init = self.get_s_init(func)
            s_instance = SomeInstance(classdef)
            # flow into __init__() if the class has got one
            if s_init is not None:
                s_init.call(args.prepend(s_instance), implicit_init=True)
            else:
                try:
                    args.fixedunpack(0)
                except ValueError:
                    raise Exception, "no __init__ found in %r" % (cls,)
            return s_instance

        assert isinstance(func, FunctionType), "[%s] expected function, got %r" % (self.whereami(), func)

        inputcells = self.get_inputcells(func, args)

        r = self.annotator.recursivecall(func, self.position_key, inputcells)

        # if we got different specializations keys for a same site, mix previous results for stability
        if key is not None:
            occurence = (base_func, self.position_key)
            try:
                prev_key, prev_r = self.spec_callsite_keys_results[occurence]
            except KeyError:
                self.spec_callsite_keys_results[occurence] = key, r
            else:
                if prev_key != key:
                    r = unionof(r, prev_r)
                    prev_key = None
                self.spec_callsite_keys_results[occurence] = prev_key, r

        return r
        

    def whereami(self):
        return self.annotator.whereami(self.position_key)

    def warning(self, msg):
        try:
            pos = self.whereami()
        except AttributeError:
            pos = '?'
        ansi_print("*** WARNING: [%s] %s" % (pos, msg), esc="31") # RED


def ishashable(x):
    try:
        hash(x)
    except TypeError:
        return False
    else:
        return True

# for parsing call arguments
class RPythonCallsSpace:
    """Pseudo Object Space providing almost no real operation.
    For the Arguments class: if it really needs other operations, it means
    that the call pattern is too complex for R-Python.
    """
    def newtuple(self, items_s):
        return SomeTuple(items_s)

    def newdict(self, stuff):
        raise CallPatternTooComplex, "'**' argument"

    def unpackiterable(self, s_obj, expected_length=None):
        if isinstance(s_obj, SomeTuple):
            if (expected_length is not None and
                expected_length != len(s_obj.items)):
                raise ValueError
            return s_obj.items
        raise CallPatternTooComplex, "'*' argument must be SomeTuple"

class CallPatternTooComplex(Exception):
    pass

# get current bookkeeper

def getbookkeeper():
    """Get the current Bookkeeper.
    Only works during the analysis of an operation."""
    try:
        return TLS.bookkeeper
    except AttributeError:
        return None
