"""
The Bookkeeper class.
"""
import sys, types, inspect, weakref

from pypy.objspace.flow.model import Constant
from pypy.annotation.model import SomeString, SomeChar, SomeFloat, \
     SomePtr, unionof, SomeInstance, SomeDict, SomeBuiltin, SomePBC, \
     SomeInteger, SomeOOInstance, SomeOOObject, TLS, SomeAddress, \
     SomeUnicodeCodePoint, SomeOOStaticMeth, s_None, s_ImpossibleValue, \
     SomeLLADTMeth, SomeBool, SomeTuple, SomeOOClass, SomeImpossibleValue, \
     SomeUnicodeString, SomeList, SomeObject, HarmlesslyBlocked, \
     SomeWeakRef, lltype_to_annotation
from pypy.annotation.classdef import InstanceSource, ClassDef
from pypy.annotation.listdef import ListDef, ListItem
from pypy.annotation.dictdef import DictDef
from pypy.annotation import description
from pypy.annotation.signature import annotationoftype
from pypy.interpreter.argument import ArgumentsForTranslation
from pypy.rlib.objectmodel import r_dict, Symbolic
from pypy.tool.algo.unionfind import UnionFind
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.ootypesystem import ootype
from pypy.rpython import extregistry
from pypy.tool.identity_dict import identity_dict

class Stats(object):

    def __init__(self, bookkeeper):
        self.bookkeeper = bookkeeper
        self.classify = {}

    def count(self, category, *args):
        for_category = self.classify.setdefault(category, {})
        classifier = getattr(self, 'consider_%s' % category, self.consider_generic)
        outcome = classifier(*args)
        for_category[self.bookkeeper.position_key] = outcome

    def indexrepr(self, idx):
        if idx.is_constant():
            if idx.const is None:
                return ''
            if isinstance(idx, SomeInteger):
                if idx.const >=0:
                    return 'pos-constant'
                else:
                    return 'Neg-constant'
            return idx.const
        else:
            if isinstance(idx, SomeInteger):
                if idx.nonneg:
                    return "non-neg"
                else:
                    return "MAYBE-NEG"
            else:
                return self.typerepr(idx)

    def steprepr(self, stp):
        if stp.is_constant():
            if stp.const in (1, None):
                return 'step=1'
            else:
                return 'step=%s?' % stp.const
        else:
            return 'non-const-step %s' % self.typerepr(stp)

    def consider_generic(self, *args):
        return tuple([self.typerepr(x) for x in args])

    def consider_list_list_eq(self, obj1, obj2):
        return obj1, obj2

    def consider_contains(self, seq):
        return seq

    def consider_non_int_eq(self, obj1, obj2):
        if obj1.knowntype == obj2.knowntype == list:
            self.count("list_list_eq", obj1, obj2)
        return self.typerepr(obj1), self.typerepr(obj2)

    def consider_non_int_comp(self, obj1, obj2):
        return self.typerepr(obj1), self.typerepr(obj2)

    def typerepr(self, obj):
        if isinstance(obj, SomeInstance):
            return obj.classdef.name
        else:
            return obj.knowntype.__name__

    def consider_tuple_random_getitem(self, tup):
        return tuple([self.typerepr(x) for x in tup.items])

    def consider_list_index(self):
        return '!'

    def consider_list_getitem(self, idx):
        return self.indexrepr(idx)

    def consider_list_setitem(self, idx):
        return self.indexrepr(idx)

    def consider_list_delitem(self, idx):
        return self.indexrepr(idx)
    
    def consider_str_join(self, s):
        if s.is_constant():
            return repr(s.const)
        else:
            return "NON-CONSTANT"

    def consider_str_getitem(self, idx):
        return self.indexrepr(idx)

    def consider_strformat(self, str, args):
        if str.is_constant():
            s = repr(str.const)
        else:
            s = "?!!!!!!"
        if isinstance(args, SomeTuple):
            return (s, tuple([self.typerepr(x) for x in args.items]))
        else:
            return (s, self.typerepr(args))

    def consider_dict_getitem(self, dic):
        return dic

    def consider_dict_setitem(self, dic):
        return dic

    def consider_dict_delitem(self, dic):
        return dic

class Bookkeeper(object):
    """The log of choices that have been made while analysing the operations.
    It ensures that the same 'choice objects' will be returned if we ask
    again during reflowing.  Like ExecutionContext, there is an implicit
    Bookkeeper that can be obtained from a thread-local variable.

    Currently used for factories and user-defined classes."""

    def __setstate__(self, dic):
        self.__dict__.update(dic) # normal action
        delayed_imports()

    def __init__(self, annotator):
        self.annotator = annotator
        self.policy = annotator.policy
        self.descs = {}          # map Python objects to their XxxDesc wrappers
        self.methoddescs = {}    # map (funcdesc, classdef) to the MethodDesc
        self.classdefs = []      # list of all ClassDefs
        self.pbctypes = {}
        self.seen_mutable = {}
        self.listdefs = {}       # map position_keys to ListDefs
        self.dictdefs = {}       # map position_keys to DictDefs
        self.immutable_cache = {}

        self.classpbc_attr_families = {} # {'attr': UnionFind(ClassAttrFamily)}
        self.frozenpbc_attr_families = UnionFind(description.FrozenAttrFamily)
        self.pbc_maximal_call_families = UnionFind(description.CallFamily)

        self.emulated_pbc_calls = {}
        self.all_specializations = {}       # {FuncDesc: specialization-info}
        self.pending_specializations = []   # list of callbacks
        self.external_class_cache = {}      # cache of ExternalType classes

        self.needs_generic_instantiate = {}

        self.stats = Stats(self)

        # used in SomeObject.__new__ for keeping debugging info
        self._isomeobject_coming_from = identity_dict()

        delayed_imports()

    def count(self, category, *args):
        self.stats.count(category, *args)

    def enter(self, position_key):
        """Start of an operation.
        The operation is uniquely identified by the given key."""
        assert not hasattr(self, 'position_key'), "don't call enter() nestedly"
        self.position_key = position_key
        TLS.bookkeeper = self

    def leave(self):
        """End of an operation."""
        del TLS.bookkeeper
        del self.position_key

    def compute_at_fixpoint(self):
        # getbookkeeper() needs to work during this function, so provide
        # one with a dummy position
        self.enter(None)
        try:
            def call_sites():
                newblocks = self.annotator.added_blocks
                if newblocks is None:
                    newblocks = self.annotator.annotated  # all of them
                binding = self.annotator.binding
                for block in newblocks:
                    for op in block.operations:
                        if op.opname in ('simple_call', 'call_args'):
                            yield op
                        # some blocks are partially annotated
                        if binding(op.result, None) is None:
                            break   # ignore the unannotated part

            for call_op in call_sites():
                self.consider_call_site(call_op)

            for pbc, args_s in self.emulated_pbc_calls.itervalues():
                self.consider_call_site_for_pbc(pbc, 'simple_call',
                                                args_s, s_ImpossibleValue, None)
            self.emulated_pbc_calls = {}
        finally:
            self.leave()

        # sanity check: no flags attached to heap stored instances

        seen = set()

        def check_no_flags(s_value_or_def):
            if isinstance(s_value_or_def, SomeInstance):
                assert not s_value_or_def.flags, "instance annotation with flags escaped to the heap"
                check_no_flags(s_value_or_def.classdef)
            elif isinstance(s_value_or_def, SomeList):
                check_no_flags(s_value_or_def.listdef.listitem)
            elif isinstance(s_value_or_def, SomeDict):
                check_no_flags(s_value_or_def.dictdef.dictkey)
                check_no_flags(s_value_or_def.dictdef.dictvalue)                
            elif isinstance(s_value_or_def, SomeTuple):
                for s_item in s_value_or_def.items:
                    check_no_flags(s_item)
            elif isinstance(s_value_or_def, ClassDef):
                if s_value_or_def in seen:
                    return
                seen.add(s_value_or_def)
                for attr in s_value_or_def.attrs.values():
                    s_attr = attr.s_value
                    check_no_flags(s_attr)
            elif isinstance(s_value_or_def, ListItem):
                if s_value_or_def in seen:
                    return
                seen.add(s_value_or_def)                
                check_no_flags(s_value_or_def.s_value)
            
        for clsdef in self.classdefs:
            check_no_flags(clsdef)

    def consider_call_site(self, call_op):
        binding = self.annotator.binding
        s_callable = binding(call_op.args[0])
        args_s = [binding(arg) for arg in call_op.args[1:]]
        if isinstance(s_callable, SomeLLADTMeth):
            adtmeth = s_callable
            s_callable = self.immutablevalue(adtmeth.func)
            args_s = [lltype_to_annotation(adtmeth.ll_ptrtype)] + args_s
        if isinstance(s_callable, SomePBC):
            s_result = binding(call_op.result, s_ImpossibleValue)
            self.consider_call_site_for_pbc(s_callable, call_op.opname, args_s,
                                            s_result, call_op)

    def consider_call_site_for_pbc(self, s_callable, opname, args_s, s_result,
                                   call_op):
        descs = list(s_callable.descriptions)
        if not descs:
            return
        family = descs[0].getcallfamily()
        args = self.build_args(opname, args_s)
        s_callable.getKind().consider_call_site(self, family, descs, args,
                                                s_result, call_op)

    def getuniqueclassdef(self, cls):
        """Get the ClassDef associated with the given user cls.
        Avoid using this!  It breaks for classes that must be specialized.
        """
        if cls is object:
            return None
        desc = self.getdesc(cls)
        return desc.getuniqueclassdef()

    def getlistdef(self, **flags_if_new):
        """Get the ListDef associated with the current position."""
        try:
            listdef = self.listdefs[self.position_key]
        except KeyError:
            listdef = self.listdefs[self.position_key] = ListDef(self)
            listdef.listitem.__dict__.update(flags_if_new)
        return listdef

    def newlist(self, *s_values, **flags):
        """Make a SomeList associated with the current position, general
        enough to contain the s_values as items."""
        listdef = self.getlistdef(**flags)
        for s_value in s_values:
            listdef.generalize(s_value)
        if flags:
            assert flags.keys() == ['range_step']
            listdef.generalize_range_step(flags['range_step'])
        return SomeList(listdef)

    def getdictdef(self, is_r_dict=False, force_non_null=False):
        """Get the DictDef associated with the current position."""
        try:
            dictdef = self.dictdefs[self.position_key]
        except KeyError:
            dictdef = DictDef(self, is_r_dict=is_r_dict,
                              force_non_null=force_non_null)
            self.dictdefs[self.position_key] = dictdef
        return dictdef

    def newdict(self):
        """Make a so-far empty SomeDict associated with the current
        position."""
        return SomeDict(self.getdictdef())

    def immutableconstant(self, const):
        return self.immutablevalue(const.value)

    def immutablevalue(self, x, need_const=True):
        """The most precise SomeValue instance that contains the
        immutable value x."""
        # convert unbound methods to the underlying function
        if hasattr(x, 'im_self') and x.im_self is None:
            x = x.im_func
            assert not hasattr(x, 'im_self')
        if x is sys: # special case constant sys to someobject
            return SomeObject()
        tp = type(x)
        if issubclass(tp, Symbolic): # symbolic constants support
            result = x.annotation()
            result.const_box = Constant(x)
            return result
        if tp is bool:
            result = SomeBool()
        elif tp is int:
            result = SomeInteger(nonneg = x>=0)
        elif tp is long:
            if -sys.maxint-1 <= x <= sys.maxint:
                x = int(x)
                result = SomeInteger(nonneg = x>=0)
            else:
                raise Exception("seeing a prebuilt long (value %s)" % hex(x))
        elif issubclass(tp, str): # py.lib uses annotated str subclasses
            if len(x) == 1:
                result = SomeChar()
            else:
                result = SomeString()
        elif tp is unicode:
            if len(x) == 1:
                result = SomeUnicodeCodePoint()
            else:
                result = SomeUnicodeString()
        elif tp is tuple:
            result = SomeTuple(items = [self.immutablevalue(e, need_const) for e in x])
        elif tp is float:
            result = SomeFloat()
        elif tp is list:
            if need_const:
                key = Constant(x)
                try:
                    return self.immutable_cache[key]
                except KeyError:
                    result = SomeList(ListDef(self, s_ImpossibleValue))
                    self.immutable_cache[key] = result
                    for e in x:
                        result.listdef.generalize(self.immutablevalue(e))
                    result.const_box = key
                    return result
            else:
                listdef = ListDef(self, s_ImpossibleValue)
                for e in x:
                    listdef.generalize(self.immutablevalue(e, False))
                result = SomeList(listdef)    
        elif tp is dict or tp is r_dict:
            if need_const:
                key = Constant(x)
                try:
                    return self.immutable_cache[key]
                except KeyError:
                    result = SomeDict(DictDef(self, 
                                              s_ImpossibleValue,
                                              s_ImpossibleValue,
                                              is_r_dict = tp is r_dict))
                    self.immutable_cache[key] = result
                    if tp is r_dict:
                        s_eqfn = self.immutablevalue(x.key_eq)
                        s_hashfn = self.immutablevalue(x.key_hash)
                        result.dictdef.dictkey.update_rdict_annotations(s_eqfn,
                                                                        s_hashfn)
                    seen_elements = 0
                    while seen_elements != len(x):
                        items = x.items()
                        for ek, ev in items:
                            result.dictdef.generalize_key(self.immutablevalue(ek))
                            result.dictdef.generalize_value(self.immutablevalue(ev))
                            result.dictdef.seen_prebuilt_key(ek)
                        seen_elements = len(items)
                        # if the dictionary grew during the iteration,
                        # start over again
                    result.const_box = key
                    return result
            else:
                dictdef = DictDef(self, 
                s_ImpossibleValue,
                s_ImpossibleValue,
                is_r_dict = tp is r_dict)
                if tp is r_dict:
                    s_eqfn = self.immutablevalue(x.key_eq)
                    s_hashfn = self.immutablevalue(x.key_hash)
                    dictdef.dictkey.update_rdict_annotations(s_eqfn,
                        s_hashfn)
                for ek, ev in x.iteritems():
                    dictdef.generalize_key(self.immutablevalue(ek, False))
                    dictdef.generalize_value(self.immutablevalue(ev, False))
                    dictdef.seen_prebuilt_key(ek)
                result = SomeDict(dictdef)
        elif tp is weakref.ReferenceType:
            x1 = x()
            if x1 is None:
                result = SomeWeakRef(None)    # dead weakref
            else:
                s1 = self.immutablevalue(x1)
                assert isinstance(s1, SomeInstance)
                result = SomeWeakRef(s1.classdef)
        elif ishashable(x) and x in BUILTIN_ANALYZERS:
            _module = getattr(x,"__module__","unknown")
            result = SomeBuiltin(BUILTIN_ANALYZERS[x], methodname="%s.%s" % (_module, x.__name__))
        elif extregistry.is_registered(x, self.policy):
            entry = extregistry.lookup(x, self.policy)
            result = entry.compute_annotation_bk(self)
        elif isinstance(x, lltype._ptr):
            result = SomePtr(lltype.typeOf(x))
        elif isinstance(x, llmemory.fakeaddress):
            result = SomeAddress()
        elif isinstance(x, ootype._static_meth):
            result = SomeOOStaticMeth(ootype.typeOf(x))
        elif isinstance(x, ootype._class):
            result = SomeOOClass(x._INSTANCE)   # NB. can be None
        elif isinstance(x, ootype.instance_impl): # XXX
            result = SomeOOInstance(ootype.typeOf(x))
        elif isinstance(x, (ootype._record, ootype._string)):
            result = SomeOOInstance(ootype.typeOf(x))
        elif isinstance(x, (ootype._object)):
            result = SomeOOObject()
        elif callable(x):
            if hasattr(x, 'im_self') and hasattr(x, 'im_func'):
                # on top of PyPy, for cases like 'l.append' where 'l' is a
                # global constant list, the find_method() returns non-None
                s_self = self.immutablevalue(x.im_self, need_const)
                result = s_self.find_method(x.im_func.__name__)
            elif hasattr(x, '__self__') and x.__self__ is not None:
                # for cases like 'l.append' where 'l' is a global constant list
                s_self = self.immutablevalue(x.__self__, need_const)
                result = s_self.find_method(x.__name__)
                if result is None:
                    result = SomeObject()
            else:
                result = None
            if result is None:
                if (self.annotator.policy.allow_someobjects
                    and getattr(x, '__module__', None) == '__builtin__'
                    # XXX note that the print support functions are __builtin__
                    and tp not in (types.FunctionType, types.MethodType)):
                    result = SomeObject()
                    result.knowntype = tp # at least for types this needs to be correct
                else:
                    result = SomePBC([self.getdesc(x)])
        elif hasattr(x, '_freeze_') and x._freeze_():
            # user-defined classes can define a method _freeze_(), which
            # is called when a prebuilt instance is found.  If the method
            # returns True, the instance is considered immutable and becomes
            # a SomePBC().  Otherwise it's just SomeInstance().
            result = SomePBC([self.getdesc(x)])
        elif hasattr(x, '__class__') \
                 and x.__class__.__module__ != '__builtin__':
            self.see_mutable(x)
            result = SomeInstance(self.getuniqueclassdef(x.__class__))
        elif x is None:
            return s_None
        else:
            result = SomeObject()
        if need_const:
            result.const = x
        return result
    
    def getdesc(self, pyobj):
        # get the XxxDesc wrapper for the given Python object, which must be
        # one of:
        #  * a user-defined Python function
        #  * a Python type or class (but not a built-in one like 'int')
        #  * a user-defined bound or unbound method object
        #  * a frozen pre-built constant (with _freeze_() == True)
        #  * a bound method of a frozen pre-built constant
        try:
            return self.descs[pyobj]
        except KeyError:
            if isinstance(pyobj, types.FunctionType):
                result = description.FunctionDesc(self, pyobj)
            elif isinstance(pyobj, (type, types.ClassType)):
                if pyobj is object:
                    raise Exception, "ClassDesc for object not supported"
                if pyobj.__module__ == '__builtin__': # avoid making classdefs for builtin types
                    result = self.getfrozen(pyobj)
                else:
                    result = description.ClassDesc(self, pyobj)
            elif isinstance(pyobj, types.MethodType):
                if pyobj.im_self is None:   # unbound
                    return self.getdesc(pyobj.im_func)
                elif (hasattr(pyobj.im_self, '_freeze_') and
                      pyobj.im_self._freeze_()):  # method of frozen
                    result = description.MethodOfFrozenDesc(self,
                        self.getdesc(pyobj.im_func),            # funcdesc
                        self.getdesc(pyobj.im_self))            # frozendesc
                else: # regular method
                    origincls, name = origin_of_meth(pyobj)
                    self.see_mutable(pyobj.im_self)
                    assert pyobj == getattr(pyobj.im_self, name), (
                        "%r is not %s.%s ??" % (pyobj, pyobj.im_self, name))
                    # emulate a getattr to make sure it's on the classdef
                    classdef = self.getuniqueclassdef(pyobj.im_class)
                    classdef.find_attribute(name)
                    result = self.getmethoddesc(
                        self.getdesc(pyobj.im_func),            # funcdesc
                        self.getuniqueclassdef(origincls),      # originclassdef
                        classdef,                               # selfclassdef
                        name)
            else:
                # must be a frozen pre-built constant, but let's check
                try:
                    assert pyobj._freeze_()
                except AttributeError:
                    raise Exception("unexpected prebuilt constant: %r" % (
                        pyobj,))
                result = self.getfrozen(pyobj)
            self.descs[pyobj] = result
            return result

    def have_seen(self, x):
        # this might need to expand some more.
        if x in self.descs:
            return True
        elif (x.__class__, x) in self.seen_mutable:
            return True
        else:
            return False
        
    def getfrozen(self, pyobj):
        result = description.FrozenDesc(self, pyobj)
        cls = result.knowntype
        if cls not in self.pbctypes:
            self.pbctypes[cls] = True
        return result

    def getmethoddesc(self, funcdesc, originclassdef, selfclassdef, name,
                      flags={}):
        flagskey = flags.items()
        flagskey.sort()
        key = funcdesc, originclassdef, selfclassdef, name, tuple(flagskey)
        try:
            return self.methoddescs[key]
        except KeyError:
            result = description.MethodDesc(self, funcdesc, originclassdef,
                                            selfclassdef, name, flags)
            self.methoddescs[key] = result
            return result

    def see_mutable(self, x):
        key = (x.__class__, x)
        if key in self.seen_mutable:
            return
        clsdef = self.getuniqueclassdef(x.__class__)        
        self.seen_mutable[key] = True
        self.event('mutable', x)
        source = InstanceSource(self, x)
        for attr in source.all_instance_attributes():
            clsdef.add_source_for_attribute(attr, source) # can trigger reflowing

    def valueoftype(self, t):
        return annotationoftype(t, self)

    def get_classpbc_attr_families(self, attrname):
        """Return the UnionFind for the ClassAttrFamilies corresponding to
        attributes of the given name.
        """
        map = self.classpbc_attr_families
        try:
            access_sets = map[attrname]
        except KeyError:
            access_sets = map[attrname] = UnionFind(description.ClassAttrFamily)
        return access_sets
    
    def pbc_getattr(self, pbc, s_attr):
        assert s_attr.is_constant()
        attr = s_attr.const

        descs = list(pbc.descriptions)
        if not descs:
            return s_ImpossibleValue

        first = descs[0]
        if len(descs) == 1:
            return first.s_read_attribute(attr)
        
        change = first.mergeattrfamilies(descs[1:], attr)
        attrfamily = first.getattrfamily(attr)

        position = self.position_key
        attrfamily.read_locations[position] = True

        actuals = []
        for desc in descs:
            actuals.append(desc.s_read_attribute(attr))
        s_result = unionof(*actuals)

        s_oldvalue = attrfamily.get_s_value(attr)
        attrfamily.set_s_value(attr, unionof(s_result, s_oldvalue))

        if change:
            for position in attrfamily.read_locations:
                self.annotator.reflowfromposition(position)

        if isinstance(s_result, SomeImpossibleValue):
            for desc in descs:
                try:
                    attrs = desc.read_attribute('_attrs_')
                except AttributeError:
                    continue
                if isinstance(attrs, Constant):
                    attrs = attrs.value
                if attr in attrs:
                    raise HarmlesslyBlocked("getattr on enforced attr")

        return s_result

    def pbc_call(self, pbc, args, emulated=None):
        """Analyse a call to a SomePBC() with the given args (list of
        annotations).
        """
        descs = list(pbc.descriptions)
        if not descs:
            return s_ImpossibleValue
        first = descs[0]
        first.mergecallfamilies(*descs[1:])

        if emulated is None:
            whence = self.position_key
            # fish the existing annotation for the result variable,
            # needed by some kinds of specialization.
            fn, block, i = self.position_key
            op = block.operations[i]
            s_previous_result = self.annotator.binding(op.result,
                                                       s_ImpossibleValue)
        else:
            if emulated is True:
                whence = None
            else:
                whence = emulated # callback case
            op = None
            s_previous_result = s_ImpossibleValue

        def schedule(graph, inputcells):
            return self.annotator.recursivecall(graph, whence, inputcells)

        results = []
        for desc in descs:
            results.append(desc.pycall(schedule, args, s_previous_result, op))
        s_result = unionof(*results)
        return s_result

    def emulate_pbc_call(self, unique_key, pbc, args_s, replace=[], callback=None):
        emulate_enter = not hasattr(self, 'position_key')
        if emulate_enter:
            self.enter(None)
        try:
            emulated_pbc_calls = self.emulated_pbc_calls
            prev = [unique_key]
            prev.extend(replace)
            for other_key in prev:
                if other_key in emulated_pbc_calls:
                    del emulated_pbc_calls[other_key]
            emulated_pbc_calls[unique_key] = pbc, args_s

            args = self.build_args("simple_call", args_s)
            if callback is None:
                emulated = True
            else:
                emulated = callback
            return self.pbc_call(pbc, args, emulated=emulated)
        finally:
            if emulate_enter:
                self.leave()

    def build_args(self, op, args_s):
        space = RPythonCallsSpace()
        if op == "simple_call":
            return ArgumentsForTranslation(space, list(args_s))
        elif op == "call_args":
            return ArgumentsForTranslation.fromshape(
                    space, args_s[0].const, # shape
                    list(args_s[1:]))

    def ondegenerated(self, what, s_value, where=None, called_from_graph=None):
        self.annotator.ondegenerated(what, s_value, where=where,
                                     called_from_graph=called_from_graph)
        
    def whereami(self):
        return self.annotator.whereami(self.position_key)

    def event(self, what, x):
        return self.annotator.policy.event(self, what, x)

    def warning(self, msg):
        return self.annotator.warning(msg)

def origin_of_meth(boundmeth):
    func = boundmeth.im_func
    candname = func.func_name
    for cls in inspect.getmro(boundmeth.im_class):
        dict = cls.__dict__
        if dict.get(candname) is func:
            return cls, candname
        for name, value in dict.iteritems():
            if value is func:
                return cls, name
    raise Exception, "could not match bound-method to attribute name: %r" % (boundmeth,)

def ishashable(x):
    try:
        hash(x)
    except TypeError:
        return False
    else:
        return True

# for parsing call arguments
class RPythonCallsSpace(object):
    """Pseudo Object Space providing almost no real operation.
    For the Arguments class: if it really needs other operations, it means
    that the call pattern is too complex for R-Python.
    """
    w_tuple = SomeTuple
    def newtuple(self, items_s):
        if len(items_s) == 1 and items_s[0] is Ellipsis:
            res = SomeObject()   # hack to get a SomeObject as the *arg
            res.from_ellipsis = True
            return res
        else:
            return SomeTuple(items_s)

    def newdict(self):
        raise CallPatternTooComplex, "'**' argument"

    def unpackiterable(self, s_obj, expected_length=None):
        if isinstance(s_obj, SomeTuple):
            if (expected_length is not None and
                expected_length != len(s_obj.items)):
                raise ValueError
            return list(s_obj.items)
        if (s_obj.__class__ is SomeObject and
            getattr(s_obj, 'from_ellipsis', False)):    # see newtuple()
            return [Ellipsis]
        raise CallPatternTooComplex, "'*' argument must be SomeTuple"
    fixedview = unpackiterable
    listview  = unpackiterable

    def is_w(self, one, other):
        return one is other

    def type(self, item):
        return type(item)

    def is_true(self, s_tup):
        assert isinstance(s_tup, SomeTuple)
        return bool(s_tup.items)

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


def delayed_imports():
    # import ordering hack
    global BUILTIN_ANALYZERS
    from pypy.annotation.builtin import BUILTIN_ANALYZERS

