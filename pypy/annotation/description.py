import types
from pypy.objspace.flow.model import Constant, FunctionGraph
from pypy.interpreter.pycode import cpython_code_signature
from pypy.interpreter.argument import rawshape
from pypy.interpreter.argument import ArgErr
from pypy.tool.sourcetools import valid_identifier


class CallFamily:
    """A family of Desc objects that could be called from common call sites.
    The call families are conceptually a partition of all (callable) Desc
    objects, where the equivalence relation is the transitive closure of
    'd1~d2 if d1 and d2 might be called at the same call site'.
    """
    overridden = False
    normalized = False
    
    def __init__(self, desc):
        self.descs = { desc: True }
        self.calltables = {}  # see calltable_lookup_row()
        self.total_calltable_size = 0

    def update(self, other):
        self.normalized = self.normalized or other.normalized
        self.descs.update(other.descs)
        for shape, table in other.calltables.items():
            for row in table:
                self.calltable_add_row(shape, row)

    def calltable_lookup_row(self, callshape, row):
        # this code looks up a table of which graph to
        # call at which call site.  Each call site gets a row of graphs,
        # sharable with other call sites.  Each column is a FunctionDesc.
        # There is one such table per "call shape".
        table = self.calltables.setdefault(callshape, [])
        for i, existing_row in enumerate(table):
            if existing_row == row:   # XXX maybe use a dict again here?
                return i
        raise LookupError

    def calltable_add_row(self, callshape, row):
        try:
            self.calltable_lookup_row(callshape, row)
        except LookupError:
            table = self.calltables.setdefault(callshape, [])
            table.append(row)
            self.total_calltable_size += 1


class AttrFamily:
    """A family of Desc objects that have common 'getattr' sites.
    The attr families are conceptually a partition of FrozenDesc and ClassDesc
    objects, where the equivalence relation is the transitive closure of
    'd1~d2 if d1 and d2 might have an attribute read on them by the same
    getattr operation.'
    """
    def __init__(self, desc):
        self.descs = { desc: True }
        self.read_locations = {}     # set of position_keys
        self.attrs = {}              # { attr: s_value }

    def update(self, other):
        self.descs.update(other.descs)
        self.read_locations.update(other.read_locations)
        self.attrs.update(other.attrs)

# ____________________________________________________________

class Desc(object):
    def __init__(self, bookkeeper, pyobj=None):
        self.bookkeeper = bookkeeper
        # 'pyobj' is non-None if there is an associated underlying Python obj
        self.pyobj = pyobj

    def __repr__(self):
        pyobj = self.pyobj
        if pyobj is None:
            return object.__repr__(self)
        return '<%s for %r>' % (self.__class__.__name__, pyobj)

    def querycallfamily(self):
        """Retrieve the CallFamily object if there is one, otherwise
           return None."""
        call_families = self.bookkeeper.pbc_maximal_call_families
        try:
            return call_families[self]
        except KeyError:
            return None

    def getcallfamily(self):
        """Get the CallFamily object. Possibly creates one."""
        call_families = self.bookkeeper.pbc_maximal_call_families
        _, _, callfamily = call_families.find(self.rowkey())
        return callfamily

    def mergecallfamilies(self, *others):
        """Merge the call families of the given Descs into one."""
        call_families = self.bookkeeper.pbc_maximal_call_families
        changed, rep, callfamily = call_families.find(self.rowkey())
        for desc in others:
            changed1, rep, callfamily = call_families.union(rep, desc.rowkey())
            changed = changed or changed1
        return changed

    def getattrfamily(self):
        """Get the AttrFamily object. Possibly creates one."""
        access_sets = self.bookkeeper.pbc_maximal_access_sets
        _, _, attrfamily = access_sets.find(self)
        return attrfamily

    def queryattrfamily(self):
        """Retrieve the AttrFamily object if there is one, otherwise
           return None."""
        access_sets = self.bookkeeper.pbc_maximal_access_sets
        try:
            return access_sets[self]
        except KeyError:
            return None

    def mergeattrfamilies(self, *others):
        """Merge the attr families of the given Descs into one."""
        access_sets = self.bookkeeper.pbc_maximal_access_sets
        changed, rep, attrfamily = access_sets.find(self)
        for desc in others:
            changed1, rep, attrfamily = access_sets.union(rep, desc)
            changed = changed or changed1
        return changed

    def bind_under(self, classdef, name):
        return self

    def simplify_desc_set(descs):
        pass
    simplify_desc_set = staticmethod(simplify_desc_set)


class FunctionDesc(Desc):
    knowntype = types.FunctionType
    overridden = False
    
    def __init__(self, bookkeeper, pyobj=None,
                 name=None, signature=None, defaults=None,
                 specializer=None):
        super(FunctionDesc, self).__init__(bookkeeper, pyobj)
        if name is None:
            name = pyobj.func_name
        if signature is None:
            signature = cpython_code_signature(pyobj.func_code)
        if defaults is None:
            defaults = pyobj.func_defaults
        self.name = name
        self.signature = signature
        self.defaults = defaults or ()
        # 'specializer' is a function with the following signature:
        #      specializer(funcdesc, args_s) => graph
        #                                 or => s_result (overridden/memo cases)
        self.specializer = specializer
        self._cache = {}     # convenience for the specializer

    def buildgraph(self, alt_name=None, builder=None):
        translator = self.bookkeeper.annotator.translator
        if builder:
            graph = builder(translator, self.pyobj)
        else:
            graph = translator.buildflowgraph(self.pyobj)
        if alt_name:
            graph.name = alt_name
        return graph

    def cachedgraph(self, key, alt_name=None, builder=None):
        try:
            return self._cache[key]
        except KeyError:
            def nameof(thing):
                if isinstance(thing, str):
                    return thing
                elif hasattr(thing, '__name__'): # mostly types and functions
                    return thing.__name__
                elif hasattr(thing, 'name'): # mostly ClassDescs
                    return thing.name
                elif isinstance(thing, tuple):
                    return '_'.join(map(nameof, thing))
                else:
                    return str(thing)[:30]
                
            if key is not None and alt_name is None:
                postfix = valid_identifier(nameof(key))
                alt_name = "%s__%s"%(self.name, postfix)
            graph = self.buildgraph(alt_name, builder)
            self._cache[key] = graph
            return graph

    def parse_arguments(self, args, graph=None):
        defs_s = []
        if graph is None:
            signature = self.signature
            defaults  = self.defaults
        else:
            signature = graph.signature
            defaults  = graph.defaults
        if defaults:
            for x in defaults:
                defs_s.append(self.bookkeeper.immutablevalue(x))
        try:
            inputcells = args.match_signature(signature, defs_s)
        except ArgErr, e:
            raise TypeError, "signature mismatch: %s" % e.getmsg(self.name)
        return inputcells

    def specialize(self, inputcells):
        if self.specializer is None:
            # get the specializer based on the tag of the 'pyobj'
            # (if any), according to the current policy
            tag = getattr(self.pyobj, '_annspecialcase_', None)
            policy = self.bookkeeper.annotator.policy
            self.specializer = policy.get_specializer(tag)
        return self.specializer(self, inputcells)

    def pycall(self, schedule, args, s_previous_result):
        inputcells = self.parse_arguments(args)
        result = self.specialize(inputcells)
        if isinstance(result, FunctionGraph):
            graph = result         # common case
            # if that graph has a different signature, we need to re-parse
            # the arguments.
            # recreate the args object because inputcells may have been changed
            new_args = args.unmatch_signature(self.signature, inputcells)
            inputcells = self.parse_arguments(new_args, graph)
            result = schedule(graph, inputcells)
        # Some specializations may break the invariant of returning
        # annotations that are always more general than the previous time.
        # We restore it here:
        from pypy.annotation.model import unionof
        result = unionof(result, s_previous_result)
        return result

    def bind_under(self, classdef, name):
        # XXX static methods
        return self.bookkeeper.getmethoddesc(self, 
                                             classdef,   # originclassdef,
                                             None,       # selfclassdef
                                             name)

    def consider_call_site(bookkeeper, family, descs, args, s_result):
        shape = rawshape(args)
        row = FunctionDesc.row_to_consider(descs, args)
        family.calltable_add_row(shape, row)
    consider_call_site = staticmethod(consider_call_site)

    def variant_for_call_site(bookkeeper, family, descs, args):
        shape = rawshape(args)
        bookkeeper.enter(None)
        try:
            row = FunctionDesc.row_to_consider(descs, args)
        finally:
            bookkeeper.leave()
        index = family.calltable_lookup_row(shape, row)
        return shape, index
    variant_for_call_site = staticmethod(variant_for_call_site)

    def rowkey(self):
        return self

    def row_to_consider(descs, args):
        # see comments in CallFamily
        from pypy.annotation.model import s_ImpossibleValue
        row = {}
        for desc in descs:
            def enlist(graph, ignore):
                row[desc.rowkey()] = graph
                return s_ImpossibleValue   # meaningless
            desc.pycall(enlist, args, s_ImpossibleValue)
        return row
    row_to_consider = staticmethod(row_to_consider)

    def get_s_signatures(self, shape):
        family = self.getcallfamily()
        table = family.calltables.get(shape)
        if table is None:
            return []
        else:
            graph_seen = {}
            s_sigs = []

            binding = self.bookkeeper.annotator.binding

            def enlist(graph):
                if graph in graph_seen:
                    return
                graph_seen[graph] = True
                s_sig = ([binding(v) for v in graph.getargs()],
                         binding(graph.getreturnvar()))
                if s_sig in s_sigs:
                    return
                s_sigs.append(s_sig)

            for row in table:
                for graph in row.itervalues():
                    enlist(graph)

            return s_sigs

NODEFAULT = object()

class ClassDesc(Desc):
    knowntype = type
    instance_level = False

    def __init__(self, bookkeeper, pyobj=None,
                 name=None, basedesc=None, classdict=None,
                 specialize=None):
        super(ClassDesc, self).__init__(bookkeeper, pyobj)

        if name is None:
            name = pyobj.__module__ + '.' + pyobj.__name__
        self.name = name
        self.basedesc = basedesc
        if classdict is None:
            classdict = {}    # populated below
        self.classdict = classdict     # {attr: Constant-or-Desc}
        if specialize is None:
            specialize = pyobj.__dict__.get('_annspecialcase_', '')
        self.specialize = specialize
        self._classdefs = {}

        if pyobj is not None:
            assert pyobj.__module__ != '__builtin__'
            cls = pyobj
            base = object
            baselist = list(cls.__bases__)
            baselist.reverse()

            for b1 in baselist:
                if b1 is object:
                    continue
                if b1.__dict__.get('_mixin_', False):
                    assert b1.__bases__ == () or b1.__bases__ == (object,), (
                        "mixin class %r should have no base" % (b1,))
                    self.add_sources_for_class(b1, mixin=True)
                else:
                    assert base is object, ("multiple inheritance only supported "
                                            "with _mixin_: %r" % (cls,))
                    base = b1

            self.add_sources_for_class(cls)
            if base is not object:
                self.basedesc = bookkeeper.getdesc(base)

    def add_sources_for_class(self, cls, mixin=False):
        for name, value in cls.__dict__.items():
            ## -- useless? -- ignore some special attributes
            ##if name.startswith('_') and not isinstance(value, types.FunctionType):
            ##    continue
            if isinstance(value, types.FunctionType):
                # for debugging
                if not hasattr(value, 'class_'):
                    value.class_ = self.pyobj # remember that this is really a method
                if self.specialize:
                    # make a custom funcdesc that specializes on its first
                    # argument (i.e. 'self').
                    from pypy.annotation.specialize import specialize_argtype
                    def argtype0(funcdesc, args_s):
                        return specialize_argtype(funcdesc, args_s, 0)
                    funcdesc = FunctionDesc(self.bookkeeper, value,
                                            specializer=argtype0)
                    self.classdict[name] = funcdesc
                    continue
                if mixin:
                    # make a new copy of the FunctionDesc for this class,
                    # but don't specialize further for all subclasses
                    funcdesc = FunctionDesc(self.bookkeeper, value)
                    self.classdict[name] = funcdesc
                    continue
                # NB. if value is, say, AssertionError.__init__, then we
                # should not use getdesc() on it.  Never.  The problem is
                # that the py lib has its own AssertionError.__init__ which
                # is of type FunctionType.  But bookkeeper.immutablevalue()
                # will do the right thing in s_get_value().
            self.classdict[name] = Constant(value)

    def getclassdef(self, key):
        try:
            return self._classdefs[key]
        except KeyError:
            from pypy.annotation.classdef import ClassDef, FORCE_ATTRIBUTES_INTO_CLASSES
            classdef = ClassDef(self.bookkeeper, self)
            self.bookkeeper.classdefs.append(classdef)
            self._classdefs[key] = classdef

            # forced attributes
            if self.pyobj is not None:
                cls = self.pyobj
                if cls in FORCE_ATTRIBUTES_INTO_CLASSES:
                    for name, s_value in FORCE_ATTRIBUTES_INTO_CLASSES[cls].items():
                        classdef.generalize_attr(name, s_value)
                        classdef.find_attribute(name).readonly = False

            # register all class attributes as coming from this ClassDesc
            # (as opposed to prebuilt instances)
            classsources = {}
            for attr in self.classdict:
                classsources[attr] = self    # comes from this ClassDesc
            classdef.setup(classsources)
            # look for a __del__ method and annotate it if it's there
            if '__del__' in self.classdict:
                from pypy.annotation.model import s_None, SomeInstance
                s_func = self.s_read_attribute('__del__')
                args_s = [SomeInstance(classdef)]
                s = self.bookkeeper.emulate_pbc_call(classdef, s_func, args_s)
                assert s_None.contains(s)
            return classdef

    def getuniqueclassdef(self):
        if self.specialize:
            raise Exception("not supported on class %r because it needs "
                            "specialization" % (self.name,))
        return self.getclassdef(None)

    def pycall(self, schedule, args, s_previous_result):
        from pypy.annotation.model import SomeInstance, SomeImpossibleValue
        if self.specialize:
            if self.specialize == 'specialize:ctr_location':
                # We use the SomeInstance annotation returned the last time
                # to make sure we use the same ClassDef this time.
                if isinstance(s_previous_result, SomeInstance):
                    classdef = s_previous_result.classdef
                else:
                    classdef = self.getclassdef(object())
            else:
                raise Exception("unsupported specialization tag: %r" % (
                    self.specialize,))
        else:
            classdef = self.getuniqueclassdef()
        s_instance = SomeInstance(classdef)
        # look up __init__ directly on the class, bypassing the normal
        # lookup mechanisms ClassDef (to avoid influencing Attribute placement)
        s_init = self.s_read_attribute('__init__')
        if isinstance(s_init, SomeImpossibleValue):
            # no __init__: check that there are no constructor args
            try:
                args.fixedunpack(0)
            except ValueError:
                raise Exception("default __init__ takes no argument"
                                " (class %s)" % (self.name,))
        else:
            # call the constructor
            args = args.prepend(s_instance)
            s_init.call(args)
        return s_instance

    def lookup(self, name):
        cdesc = self
        while name not in cdesc.classdict:
            cdesc = cdesc.basedesc
            if cdesc is None:
                return None 
        else:
            return cdesc

    def read_attribute(self, name, default=NODEFAULT):
        cdesc = self.lookup(name)
        if cdesc is None:
            if default is NODEFAULT:
                raise AttributeError
            else:
                return default
        else:
            return cdesc.classdict[name]

    def s_read_attribute(self, name):
        # look up an attribute in the class
        cdesc = self.lookup(name)
        if cdesc is None:
            from pypy.annotation.model import s_ImpossibleValue
            return s_ImpossibleValue
        else:
            # delegate to s_get_value to turn it into an annotation
            return cdesc.s_get_value(None, name)

    def s_get_value(self, classdef, name):
        obj = self.classdict[name]
        if isinstance(obj, Constant):
            value = obj.value
            if isinstance(value, staticmethod):   # special case
                value = value.__get__(42)
                classdef = None   # don't bind
            s_value = self.bookkeeper.immutablevalue(value)
            if classdef is not None:
                s_value = s_value.bind_callables_under(classdef, name)
        elif isinstance(obj, Desc):
            from pypy.annotation.model import SomePBC
            if classdef is not None:
                obj = obj.bind_under(classdef, name)
            s_value = SomePBC([obj])
        else:
            raise TypeError("classdict should not contain %r" % (obj,))
        return s_value

    def create_new_attribute(self, name, value):
        assert name not in self.classdict, "name clash: %r" % (name,)
        self.classdict[name] = Constant(value)

    def find_source_for(self, name):
        if name in self.classdict:
            return self
        if self.pyobj is not None:
            # check whether in the case the classdesc corresponds to a real class
            # there is a new attribute
            cls = self.pyobj
            if name in cls.__dict__:
                self.classdict[name] = Constant(cls.__dict__[name])
                return self
        return None

    def consider_call_site(bookkeeper, family, descs, args, s_result):
        from pypy.annotation.model import SomeInstance, SomePBC, s_None
        if len(descs) == 1:
            # call to a single class, look at the result annotation
            # in case it was specialized
            if not isinstance(s_result, SomeInstance):
                raise Exception("calling a class didn't return an instance??")
            classdefs = [s_result.classdef]
        else:
            # call to multiple classes: specialization not supported
            classdefs = [desc.getuniqueclassdef() for desc in descs]
        # make a PBC of MethodDescs, one for the __init__ of each class
        initdescs = []
        for desc, classdef in zip(descs, classdefs):
            s_init = desc.s_read_attribute('__init__')
            if isinstance(s_init, SomePBC):
                assert len(s_init.descriptions) == 1, (
                    "unexpected dynamic __init__?")
                initfuncdesc = s_init.descriptions.keys()[0]
                if isinstance(initfuncdesc, FunctionDesc):
                    initmethdesc = bookkeeper.getmethoddesc(initfuncdesc,
                                                            classdef,
                                                            classdef,
                                                            '__init__')
                    initdescs.append(initmethdesc)
        # register a call to exactly these __init__ methods
        if initdescs:
            initdescs[0].mergecallfamilies(*initdescs[1:])
            initfamily = initdescs[0].getcallfamily()
            MethodDesc.consider_call_site(bookkeeper, initfamily, initdescs,
                                          args, s_None)
    consider_call_site = staticmethod(consider_call_site)

    def rowkey(self):
        return self


class MethodDesc(Desc):
    knowntype = types.MethodType

    def __init__(self, bookkeeper, funcdesc, originclassdef, 
                 selfclassdef, name):
        super(MethodDesc, self).__init__(bookkeeper)
        self.funcdesc = funcdesc
        self.originclassdef = originclassdef
        self.selfclassdef = selfclassdef
        self.name = name

    def __repr__(self):
        if self.selfclassdef is None:
            return '<unbound MethodDesc %r of %r>' % (self.name,
                                                      self.originclassdef)
        else:
            return '<MethodDesc %r of %r bound to %r>' % (self.name,
                                                          self.originclassdef,
                                                          self.selfclassdef)

    def pycall(self, schedule, args, s_previous_result):
        from pypy.annotation.model import SomeInstance
        if self.selfclassdef is None:
            raise Exception("calling %r" % (self,))
        s_instance = SomeInstance(self.selfclassdef)
        args = args.prepend(s_instance)
        return self.funcdesc.pycall(schedule, args, s_previous_result)

    def bind_under(self, classdef, name):
        self.bookkeeper.warning("rebinding an already bound %r" % (self,))
        return self.funcdesc.bind_under(classdef, name)

    def bind_self(self, newselfclassdef):
        return self.bookkeeper.getmethoddesc(self.funcdesc,
                                             self.originclassdef,
                                             newselfclassdef,
                                             self.name)
    
    def consider_call_site(bookkeeper, family, descs, args, s_result):
        shape = rawshape(args, nextra=1)     # account for the extra 'self'
        funcdescs = [methoddesc.funcdesc for methoddesc in descs]
        row = FunctionDesc.row_to_consider(descs, args)
        family.calltable_add_row(shape, row)
    consider_call_site = staticmethod(consider_call_site)

    def rowkey(self):
        # we are computing call families and call tables that always contain
        # FunctionDescs, not MethodDescs.  The present method returns the
        # FunctionDesc to use as a key in that family.
        return self.funcdesc
    
    def simplify_desc_set(descs):
        # if two MethodDescs in the set differ only in their selfclassdefs,
        # and if one of the selfclassdefs is a subclass of the other, then
        # we can remove the former.  This is not just an optimization but
        # needed to make contains() happy on SomePBC.
        groups = {}
        for desc in descs:
            if desc.selfclassdef is not None:
                key = desc.funcdesc, desc.originclassdef, desc.name
                groups.setdefault(key, []).append(desc)
        for group in groups.values():
            if len(group) > 1:
                for desc1 in group:
                    cdef1 = desc1.selfclassdef
                    for desc2 in group:
                        cdef2 = desc2.selfclassdef
                        if cdef1 is not cdef2 and cdef1.issubclass(cdef2):
                            del descs[desc1]
                            break
    simplify_desc_set = staticmethod(simplify_desc_set)


def new_or_old_class(c):
    if hasattr(c, '__class__'):
        return c.__class__
    else:
        return type(c)

class FrozenDesc(Desc):

    def __init__(self, bookkeeper, pyobj, read_attribute=None):
        super(FrozenDesc, self).__init__(bookkeeper, pyobj)
        if read_attribute is None:
            read_attribute = lambda attr: getattr(pyobj, attr)
        self._read_attribute = read_attribute
        self.attrcache = {}
        self.knowntype = new_or_old_class(pyobj)
        assert bool(pyobj), "__nonzero__ unsupported on frozen PBC %r" %(pyobj,)

    def read_attribute(self, attr):
        try:
            return self.attrcache[attr]
        except KeyError:
            result = self.attrcache[attr] = self._read_attribute(attr)
            return result

    def s_read_attribute(self, attr):
        try:
            value = self.read_attribute(attr)
        except AttributeError:
            from pypy.annotation.model import s_ImpossibleValue
            return s_ImpossibleValue
        else:
            return self.bookkeeper.immutablevalue(value)
    
    def create_new_attribute(self, name, value):
        try:
            self.read_attribute(name)
        except AttributeError:
            pass
        else:
            raise AssertionError("name clash: %r" % (name,))
        self.attrcache[name] = value


class MethodOfFrozenDesc(Desc):
    knowntype = types.MethodType

    def __init__(self, bookkeeper, funcdesc, frozendesc):
        super(MethodOfFrozenDesc, self).__init__(bookkeeper)
        self.funcdesc = funcdesc
        self.frozendesc = frozendesc

    def __repr__(self):
        return '<MethodOfFrozenDesc %r of %r>' % (self.funcdesc,
                                                  self.frozendesc)

    def pycall(self, schedule, args, s_previous_result):
        from pypy.annotation.model import SomePBC
        s_self = SomePBC([self.frozendesc])
        args = args.prepend(s_self)
        return self.funcdesc.pycall(schedule, args, s_previous_result)
    
    def consider_call_site(bookkeeper, family, descs, args, s_result):
        shape = rawshape(args, nextra=1)    # account for the extra 'self'
        funcdescs = [mofdesc.funcdesc for mofdesc in descs]
        row = FunctionDesc.row_to_consider(descs, args)
        family.calltable_add_row(shape, row)
    consider_call_site = staticmethod(consider_call_site)

    def rowkey(self):
        return self.funcdesc
