from pypy.objspace.std.register_all import register_all
from pypy.interpreter.baseobjspace import ObjSpace, Wrappable, UnpackValueError
from pypy.interpreter.error import OperationError, debug_print
from pypy.interpreter.typedef import get_unique_interplevel_subclass
from pypy.interpreter import argument
from pypy.interpreter import pyframe
from pypy.interpreter import function
from pypy.interpreter.pyopcode import unrolling_compare_dispatch_table, \
     BytecodeCorruption
from pypy.rlib.objectmodel import instantiate
from pypy.rlib.debug import make_sure_not_resized
from pypy.interpreter.gateway import PyPyCacheDir
from pypy.tool.cache import Cache 
from pypy.tool.sourcetools import func_with_new_name
from pypy.objspace.std.model import W_Object, UnwrapError
from pypy.objspace.std.model import W_ANY, StdObjSpaceMultiMethod, StdTypeModel
from pypy.objspace.std.multimethod import FailedToImplement
from pypy.objspace.descroperation import DescrOperation
from pypy.objspace.std import stdtypedef
from pypy.rlib.rarithmetic import base_int
from pypy.rlib.objectmodel import we_are_translated
from pypy.rlib.jit import hint, we_are_jitted
from pypy.rlib.unroll import unrolling_iterable
import sys
import os
import __builtin__

#check for sets
try:
    s = set()
    del s
except NameError:
    try:
        from sets import Set as set
        from sets import ImmutableSet as frozenset
    except ImportError:
        class DummySet(object):pass
        set = DummySet
        frozenset = DummySet

_registered_implementations = {}
def registerimplementation(implcls):
    # hint to objspace.std.model to register the implementation class
    assert issubclass(implcls, W_Object)
    _registered_implementations[implcls] = True


compare_table = [
    "lt",   # "<"
    "le",   # "<="
    "eq",   # "=="
    "ne",   # "!="
    "gt",   # ">"
    "ge",   # ">="
    ]

unrolling_compare_ops = unrolling_iterable(
    enumerate(compare_table))

##################################################################

class StdObjSpace(ObjSpace, DescrOperation):
    """The standard object space, implementing a general-purpose object
    library in Restricted Python."""

    PACKAGE_PATH = 'objspace.std'

    def initialize(self):
        "NOT_RPYTHON: only for initializing the space."
        self._typecache = Cache()

        # Import all the object types and implementations
        self.model = StdTypeModel(self.config)

        class StdObjSpaceFrame(pyframe.PyFrame):
            if self.config.objspace.std.optimized_int_add:
                if self.config.objspace.std.withsmallint:
                    def BINARY_ADD(f, oparg, *ignored):
                        from pypy.objspace.std.smallintobject import \
                             W_SmallIntObject, add__SmallInt_SmallInt
                        w_2 = f.popvalue()
                        w_1 = f.popvalue()
                        if type(w_1) is W_SmallIntObject and type(w_2) is W_SmallIntObject:
                            try:
                                w_result = add__SmallInt_SmallInt(f.space, w_1, w_2)
                            except FailedToImplement:
                                w_result = f.space.add(w_1, w_2)
                        else:
                            w_result = f.space.add(w_1, w_2)
                        f.pushvalue(w_result)
                else:
                    def BINARY_ADD(f, oparg, *ignored):
                        from pypy.objspace.std.intobject import \
                             W_IntObject, add__Int_Int
                        w_2 = f.popvalue()
                        w_1 = f.popvalue()
                        if type(w_1) is W_IntObject and type(w_2) is W_IntObject:
                            try:
                                w_result = add__Int_Int(f.space, w_1, w_2)
                            except FailedToImplement:
                                w_result = f.space.add(w_1, w_2)
                        else:
                            w_result = f.space.add(w_1, w_2)
                        f.pushvalue(w_result)

            if self.config.objspace.std.optimized_list_getitem:
                def BINARY_SUBSCR(f, *ignored):
                    w_2 = f.popvalue()
                    w_1 = f.popvalue()
                    if type(w_1) is W_ListObject and type(w_2) is W_IntObject:
                        try:
                            w_result = w_1.wrappeditems[w_2.intval]
                        except IndexError:
                            raise OperationError(f.space.w_IndexError,
                                f.space.wrap("list index out of range"))
                    else:
                        w_result = f.space.getitem(w_1, w_2)
                    f.pushvalue(w_result)

            def LIST_APPEND(f, *ignored):
                w = f.popvalue()
                v = f.popvalue()
                if type(v) is W_ListObject:
                    v.append(w)
                else:
                    f.space.call_method(v, 'append', w)

            if self.config.objspace.opcodes.CALL_LIKELY_BUILTIN:
                def CALL_LIKELY_BUILTIN(f, oparg, *ignored):
                    from pypy.module.__builtin__ import OPTIMIZED_BUILTINS, Module
                    from pypy.objspace.std.dictmultiobject import W_DictMultiObject
                    w_globals = f.w_globals
                    num = oparg >> 8
                    assert isinstance(w_globals, W_DictMultiObject)
                    w_value = w_globals.implementation.get_builtin_indexed(num)
                    if w_value is None:
                        builtins = f.get_builtin()
                        assert isinstance(builtins, Module)
                        w_builtin_dict = builtins.w_dict
                        assert isinstance(w_builtin_dict, W_DictMultiObject)
                        w_value = w_builtin_dict.implementation.get_builtin_indexed(num)
        ##                 if w_value is not None:
        ##                     print "CALL_LIKELY_BUILTIN fast"
                    if w_value is None:
                        varname = OPTIMIZED_BUILTINS[num]
                        message = "global name '%s' is not defined" % varname
                        raise OperationError(f.space.w_NameError,
                                             f.space.wrap(message))
                    nargs = oparg & 0xff
                    w_function = w_value
                    try:
                        w_result = f.call_likely_builtin(w_function, nargs)
                        # XXX XXX fix the problem of resume points!
                        #rstack.resume_point("CALL_FUNCTION", f, nargs, returns=w_result)
                    finally:
                        f.dropvalues(nargs)
                    f.pushvalue(w_result)

                def call_likely_builtin(f, w_function, nargs):
                    if isinstance(w_function, function.Function):
                        return w_function.funccall_valuestack(nargs, f)
                    args = f.make_arguments(nargs)
                    try:
                        return f.space.call_args(w_function, args)
                    finally:
                        if isinstance(args, argument.ArgumentsFromValuestack):
                            args.frame = None

            if self.config.objspace.opcodes.CALL_METHOD:
                # def LOOKUP_METHOD(...):
                from pypy.objspace.std.callmethod import LOOKUP_METHOD
                # def CALL_METHOD(...):
                from pypy.objspace.std.callmethod import CALL_METHOD

            if self.config.objspace.std.optimized_comparison_op:
                def COMPARE_OP(f, testnum, *ignored):
                    import operator
                    w_2 = f.popvalue()
                    w_1 = f.popvalue()
                    w_result = None
                    if (type(w_2) is W_IntObject and type(w_1) is W_IntObject
                        and testnum < len(compare_table)):
                        for i, attr in unrolling_compare_ops:
                            if i == testnum:
                                op = getattr(operator, attr)
                                w_result = f.space.newbool(op(w_1.intval,
                                                              w_2.intval))
                                break
                    else:
                        for i, attr in unrolling_compare_dispatch_table:
                            if i == testnum:
                                w_result = getattr(f, attr)(w_1, w_2)
                                break
                        else:
                            raise BytecodeCorruption, "bad COMPARE_OP oparg"
                    f.pushvalue(w_result)

            if self.config.objspace.std.logspaceoptypes:
                _space_op_types = []
                for name, func in pyframe.PyFrame.__dict__.iteritems():
                    if hasattr(func, 'binop'):
                        operationname = func.binop
                        def make_opimpl(operationname):
                            def opimpl(f, *ignored):
                                operation = getattr(f.space, operationname)
                                w_2 = f.popvalue()
                                w_1 = f.popvalue()
                                if we_are_translated():
                                    s = operationname + ' ' + str(w_1) + ' ' + str(w_2)
                                else:
                                    s = operationname + ' ' + w_1.__class__.__name__ + ' ' + w_2.__class__.__name__
                                f._space_op_types.append(s)
                                w_result = operation(w_1, w_2)
                                f.pushvalue(w_result)
                            return func_with_new_name(opimpl, "opcode_impl_for_%s" % operationname)
                        locals()[name] = make_opimpl(operationname)
                    elif hasattr(func, 'unaryop'):
                        operationname = func.unaryop
                        def make_opimpl(operationname):
                            def opimpl(f, *ignored):
                                operation = getattr(f.space, operationname)
                                w_1 = f.popvalue()
                                if we_are_translated():
                                    s = operationname + ' ' + str(w_1)
                                else:
                                    s = operationname + ' ' + w_1.__class__.__name__
                                f._space_op_types.append(s)
                                w_result = operation(w_1)
                                f.pushvalue(w_result)
                            return func_with_new_name(opimpl, "opcode_impl_for_%s" % operationname)
                        locals()[name] = make_opimpl(operationname)                    

        self.FrameClass = StdObjSpaceFrame

        # XXX store the dict class on the space to access it in various places
        if self.config.objspace.std.withmultidict:
            from pypy.objspace.std import dictmultiobject
            self.DictObjectCls = dictmultiobject.W_DictMultiObject
            self.emptydictimpl = dictmultiobject.EmptyDictImplementation(self)
            if self.config.objspace.std.withbucketdict:
                from pypy.objspace.std import dictbucket
                self.DefaultDictImpl = dictbucket.BucketDictImplementation
            else:
                self.DefaultDictImpl = dictmultiobject.RDictImplementation
        else:
            from pypy.objspace.std import dictobject
            self.DictObjectCls = dictobject.W_DictObject
        assert self.DictObjectCls in self.model.typeorder

        from pypy.objspace.std import tupleobject
        self.TupleObjectCls = tupleobject.W_TupleObject

        if not self.config.objspace.std.withrope:
            from pypy.objspace.std import stringobject
            self.StringObjectCls = stringobject.W_StringObject
        else:
            from pypy.objspace.std import ropeobject
            self.StringObjectCls = ropeobject.W_RopeObject
        assert self.StringObjectCls in self.model.typeorder

        # install all the MultiMethods into the space instance
        for name, mm in self.MM.__dict__.items():
            if not isinstance(mm, StdObjSpaceMultiMethod):
                continue
            if not hasattr(self, name):
                if name.endswith('_w'): # int_w, str_w...: these do not return a wrapped object
                    func = mm.install_not_sliced(self.model.typeorder, baked_perform_call=True)
                else:               
                    exprargs, expr, miniglobals, fallback = (
                        mm.install_not_sliced(self.model.typeorder, baked_perform_call=False))

                    func = stdtypedef.make_perform_trampoline('__mm_'+name,
                                                              exprargs, expr, miniglobals,
                                                              mm)
                
                                                  # e.g. add(space, w_x, w_y)
                def make_boundmethod(func=func):
                    def boundmethod(*args):
                        return func(self, *args)
                    return func_with_new_name(boundmethod, 'boundmethod_'+name)
                boundmethod = make_boundmethod()
                setattr(self, name, boundmethod)  # store into 'space' instance
            elif self.config.objspace.std.builtinshortcut:
                from pypy.objspace.std import builtinshortcut
                builtinshortcut.install(self, mm)

        if self.config.objspace.std.builtinshortcut:
            from pypy.objspace.std import builtinshortcut
            builtinshortcut.install_is_true(self, self.MM.nonzero, self.MM.len)

        # set up the method cache
        if self.config.objspace.std.withmethodcache:
            SIZE = 1 << self.config.objspace.std.methodcachesizeexp
            self.method_cache_versions = [None] * SIZE
            self.method_cache_names = [None] * SIZE
            self.method_cache_lookup_where = [(None, None)] * SIZE
            if self.config.objspace.std.withmethodcachecounter:
                self.method_cache_hits = {}
                self.method_cache_misses = {}

        # hack to avoid imports in the time-critical functions below
        for cls in self.model.typeorder:
            globals()[cls.__name__] = cls
        for cls in self.model.imported_but_not_registered:
            globals()[cls.__name__] = cls

        # singletons
        self.w_None  = W_NoneObject.w_None
        self.w_False = W_BoolObject.w_False
        self.w_True  = W_BoolObject.w_True
        from pypy.interpreter.special import NotImplemented, Ellipsis
        self.w_NotImplemented = self.wrap(NotImplemented(self))  
        self.w_Ellipsis = self.wrap(Ellipsis(self))  

        # types
        for typedef in self.model.pythontypes:
            w_type = self.gettypeobject(typedef)
            setattr(self, 'w_' + typedef.name, w_type)

        # exceptions & builtins
        w_mod = self.setup_exceptions()
        self.make_builtins()
        self.sys.setmodule(w_mod)

        # the type of old-style classes
        self.w_classobj = self.builtin.get('__metaclass__')

        # fix up a problem where multimethods apparently don't 
        # like to define this at interp-level 
        # HACK HACK HACK
        from pypy.objspace.std.typeobject import _HEAPTYPE
        old_flags = self.w_dict.__flags__
        self.w_dict.__flags__ |= _HEAPTYPE
        self.appexec([self.w_dict], """
            (dict): 
                def fromkeys(cls, seq, value=None):
                    r = cls()
                    for s in seq:
                        r[s] = value
                    return r
                dict.fromkeys = classmethod(fromkeys)
        """)
        self.w_dict.__flags__ = old_flags

        # final setup
        self.setup_builtin_modules()
        # Adding transparent proxy call
        if self.config.objspace.std.withtproxy:
            w___pypy__ = self.getbuiltinmodule("__pypy__")
            from pypy.objspace.std.transparent import app_proxy, app_proxy_controller
        
            self.setattr(w___pypy__, self.wrap('tproxy'),
                          self.wrap(app_proxy))
            self.setattr(w___pypy__, self.wrap('get_tproxy_controller'),
                          self.wrap(app_proxy_controller))

    def create_builtin_module(self, pyname, publicname):
        """NOT_RPYTHON
        helper function which returns the wrapped module and its dict.
        """
        # generate on-the-fly
        class Fake: pass
        fake = Fake()
        from pypy import lib
        fname = os.path.join(os.path.split(lib.__file__)[0], pyname)
        fake.filename = fname
        fake.code = compile(file(fname).read(), fname, "exec")
        fake.modname = publicname
        w_dic = PyPyCacheDir.build_applevelinterp_dict(fake, self)
        from pypy.interpreter.module import Module
        mod = Module(self, self.wrap(publicname), w_dic)
        w_mod = self.wrap(mod)
        return w_mod, w_dic

    def setup_exceptions(self):
        """NOT_RPYTHON"""
        ## hacking things in
        def call(w_type, w_args):
            space = self
            # too early for unpackiterable as well :-(
            name  = space.unwrap(space.getitem(w_args, space.wrap(0)))
            bases = space.viewiterable(space.getitem(w_args, space.wrap(1)))
            dic   = space.unwrap(space.getitem(w_args, space.wrap(2)))
            dic = dict([(key,space.wrap(value)) for (key, value) in dic.items()])
            bases = list(bases)
            if not bases:
                bases = [space.w_object]
            res = W_TypeObject(space, name, bases, dic)
            res.ready()
            return res
        try:
            # note that we hide the real call method by an instance variable!
            self.call = call
            mod, w_dic = self.create_builtin_module('_exceptions.py', 'exceptions')

            self.w_IndexError = self.getitem(w_dic, self.wrap("IndexError"))
            self.w_StopIteration = self.getitem(w_dic, self.wrap("StopIteration"))
        finally:
            del self.call # revert

        names_w = self.unpackiterable(self.call_function(self.getattr(w_dic, self.wrap("keys"))))

        for w_name in names_w:
            name = self.str_w(w_name)
            if not name.startswith('__'):
                excname = name
                w_exc = self.getitem(w_dic, w_name)
                setattr(self, "w_"+excname, w_exc)

        return mod

    def createexecutioncontext(self):
        # add space specific fields to execution context
        # note that this method must not call space methods that might need an
        # execution context themselves (e.g. nearly all space methods)
        ec = ObjSpace.createexecutioncontext(self)
        ec._py_repr = None
        return ec

    def createframe(self, code, w_globals, closure=None):
        from pypy.objspace.std.fake import CPythonFakeCode, CPythonFakeFrame
        if not we_are_translated() and isinstance(code, CPythonFakeCode):
            return CPythonFakeFrame(self, code, w_globals)
        else:
            return self.FrameClass(self, code, w_globals, closure)

    def gettypefor(self, cls):
        return self.gettypeobject(cls.typedef)

    def gettypeobject(self, typedef):
        # stdtypedef.TypeCache maps each StdTypeDef instance to its
        # unique-for-this-space W_TypeObject instance
        return self.fromcache(stdtypedef.TypeCache).getorbuild(typedef)

    def wrap(self, x):
        "Wraps the Python value 'x' into one of the wrapper classes."
        # You might notice that this function is rather conspicuously
        # not RPython.  We can get away with this because the function
        # is specialized (see after the function body).  Also worth
        # noting is that the isinstance's involving integer types
        # behave rather differently to how you might expect during
        # annotation (see pypy/annotation/builtin.py)
        if x is None:
            return self.w_None
        if isinstance(x, W_Object):
            raise TypeError, "attempt to wrap already wrapped object: %s"%(x,)
        if isinstance(x, OperationError):
            raise TypeError, ("attempt to wrap already wrapped exception: %s"%
                              (x,))
        if isinstance(x, int):
            if isinstance(x, bool):
                return self.newbool(x)
            else:
                return self.newint(x)
        if isinstance(x, str):
            from pypy.objspace.std.stringtype import wrapstr
            return wrapstr(self, x)
        if isinstance(x, unicode):
            from pypy.objspace.std.unicodetype import wrapunicode
            return wrapunicode(self, x)
        if isinstance(x, float):
            return W_FloatObject(x)
        if isinstance(x, Wrappable):
            w_result = x.__spacebind__(self)
            #print 'wrapping', x, '->', w_result
            return w_result
        if isinstance(x, base_int):
            return W_LongObject.fromrarith_int(x)

        # _____ below here is where the annotator should not get _____

        # wrap() of a container works on CPython, but the code is
        # not RPython.  Don't use -- it is kept around mostly for tests.
        # Use instead newdict(), newlist(), newtuple().
        if isinstance(x, dict):
            items_w = [(self.wrap(k), self.wrap(v)) for (k, v) in x.iteritems()]
            r = self.newdict()
            r.initialize_content(items_w)
            return r
        if isinstance(x, tuple):
            wrappeditems = [self.wrap(item) for item in list(x)]
            return self.newtuple(wrappeditems)
        if isinstance(x, list):
            wrappeditems = [self.wrap(item) for item in x]
            return self.newlist(wrappeditems)

        # The following cases are even stranger.
        # Really really only for tests.
        if type(x) is long:
            return W_LongObject.fromlong(x)
        if isinstance(x, slice):
            return W_SliceObject(self.wrap(x.start),
                                 self.wrap(x.stop),
                                 self.wrap(x.step))
        if isinstance(x, complex):
            return W_ComplexObject(x.real, x.imag)

        if isinstance(x, set):
            wrappeditems = [self.wrap(item) for item in x]
            return W_SetObject(self, wrappeditems)

        if isinstance(x, frozenset):
            wrappeditems = [self.wrap(item) for item in x]
            return W_FrozensetObject(self, wrappeditems)

        if x is __builtin__.Ellipsis:
            # '__builtin__.Ellipsis' avoids confusion with special.Ellipsis
            return self.w_Ellipsis

        if self.config.objspace.nofaking:
            # annotation should actually not get here.  If it does, you get
            # an error during rtyping because '%r' is not supported.  It tells
            # you that there was a space.wrap() on a strange object.
            raise OperationError(self.w_RuntimeError,
                                 self.wrap("nofaking enabled: refusing "
                                           "to wrap cpython value %r" %(x,)))
        if isinstance(x, type(Exception)) and issubclass(x, Exception):
            w_result = self.wrap_exception_cls(x)
            if w_result is not None:
                return w_result
        #print "fake-wrapping", x 
        from fake import fake_object
        return fake_object(self, x)

    wrap._annspecialcase_ = "specialize:wrap"

    def wrap_exception_cls(self, x):
        """NOT_RPYTHON"""
        if hasattr(self, 'w_' + x.__name__):
            w_result = getattr(self, 'w_' + x.__name__)            
            return w_result
        return None
    wrap_exception_cls._annspecialcase_ = "override:wrap_exception_cls"
        
    def unwrap(self, w_obj):
        if isinstance(w_obj, Wrappable):
            return w_obj
        if isinstance(w_obj, W_Object):
            return w_obj.unwrap(self)
        raise UnwrapError, "cannot unwrap: %r" % w_obj

    def newint(self, intval):
        # this time-critical and circular-imports-funny method was stored
        # on 'self' by initialize()
        # not sure how bad this is:
        from pypy.objspace.std.inttype import wrapint
        return wrapint(self, intval)

    def newfloat(self, floatval):
        return W_FloatObject(floatval)

    def newcomplex(self, realval, imagval):
        return W_ComplexObject(realval, imagval)

    def newset(self, rdict_w):
        return W_SetObject(self, rdict_w)

    def newfrozenset(self, rdict_w):
        return W_FrozensetObject(self, rdict_w)

    def newlong(self, val): # val is an int
        return W_LongObject.fromint(self, val)

    def newtuple(self, list_w):
        from pypy.objspace.std.tupletype import wraptuple
        assert isinstance(list_w, list)
        make_sure_not_resized(list_w)
        return wraptuple(self, list_w)

    def newlist(self, list_w):
        if self.config.objspace.std.withmultilist:
            from pypy.objspace.std.listmultiobject import convert_list_w
            return convert_list_w(self, list_w)
        else:
            from pypy.objspace.std.listobject import W_ListObject
            return W_ListObject(list_w)

    def newdict(self, track_builtin_shadowing=False):
        if self.config.objspace.opcodes.CALL_LIKELY_BUILTIN and track_builtin_shadowing:
            from pypy.objspace.std.dictmultiobject import W_DictMultiObject
            return W_DictMultiObject(self, wary=True)
        return self.DictObjectCls(self)

    def newslice(self, w_start, w_end, w_step):
        return W_SliceObject(w_start, w_end, w_step)

    def newseqiter(self, w_obj):
        return W_SeqIterObject(w_obj)

    def type(self, w_obj):
        hint(w_obj.__class__, promote=True)
        return w_obj.getclass(self)

    def lookup(self, w_obj, name):
        w_type = self.type(w_obj)
        return w_type.lookup(name)
    lookup._annspecialcase_ = 'specialize:lookup'

    def lookup_in_type_where(self, w_type, name):
        return w_type.lookup_where(name)
    lookup_in_type_where._annspecialcase_ = 'specialize:lookup_in_type_where'

    def lookup_in_type_starting_at(self, w_type, w_starttype, name):
        """ Only supposed to be used to implement super, w_starttype
        and w_type are the same as for super(starttype, type)
        """
        assert isinstance(w_type, W_TypeObject)
        assert isinstance(w_starttype, W_TypeObject)
        return w_type.lookup_starting_at(w_starttype, name)

    def allocate_instance(self, cls, w_subtype):
        """Allocate the memory needed for an instance of an internal or
        user-defined type, without actually __init__ializing the instance."""
        w_type = self.gettypeobject(cls.typedef)
        if self.is_w(w_type, w_subtype):
            instance =  instantiate(cls)
        elif cls.typedef.acceptable_as_base_class:
            # the purpose of the above check is to avoid the code below
            # to be annotated at all for 'cls' if it is not necessary
            w_subtype = w_type.check_user_subclass(w_subtype)
            subcls = get_unique_interplevel_subclass(cls, w_subtype.hasdict, w_subtype.nslots != 0, w_subtype.needsdel, w_subtype.weakrefable)
            instance = instantiate(subcls)
            instance.user_setup(self, w_subtype)
        else:
            raise OperationError(self.w_TypeError,
                self.wrap("%s.__new__(%s): only for the type %s" % (
                    w_type.name, w_subtype.getname(self, '?'), w_type.name)))
        assert isinstance(instance, cls)
        return instance
    allocate_instance._annspecialcase_ = "specialize:arg(1)"

    # two following functions are almost identical, but in fact they
    # have different return type. First one is a resizable list, second
    # one is not

    def unpackiterable(self, w_obj, expected_length=-1):
        if isinstance(w_obj, W_TupleObject):
            t = w_obj.wrappeditems[:]
        elif isinstance(w_obj, W_ListObject):
            t = w_obj.wrappeditems[:]
        else:
            return ObjSpace.unpackiterable(self, w_obj, expected_length)
        if expected_length != -1 and len(t) != expected_length:
            raise UnpackValueError("Expected length %d, got %d" % (expected_length, len(t)))
        return t

    def viewiterable(self, w_obj, expected_length=-1):
        """ Fast paths
        """
        if isinstance(w_obj, W_TupleObject):
            t = w_obj.wrappeditems
        elif isinstance(w_obj, W_ListObject):
            t = w_obj.wrappeditems[:]
        else:
            return ObjSpace.viewiterable(self, w_obj, expected_length)
        if expected_length != -1 and len(t) != expected_length:
            raise UnpackValueError("Expected length %d, got %d" % (expected_length, len(t)))
        return t

    def sliceindices(self, w_slice, w_length):
        if isinstance(w_slice, W_SliceObject):
            a, b, c = w_slice.indices3(self, self.int_w(w_length))
            return (a, b, c)
        w_indices = self.getattr(w_slice, self.wrap('indices'))
        w_tup = self.call_function(w_indices, w_length)
        l_w = self.unpackiterable(w_tup)
        if not len(l_w) == 3:
            raise OperationError(self.w_ValueError,
                                 self.wrap("Expected tuple of length 3"))
        return self.int_w(l_w[0]), self.int_w(l_w[1]), self.int_w(l_w[2])

    def is_(self, w_one, w_two):
        # XXX a bit of hacking to gain more speed 
        if w_one is w_two:
            return self.w_True
        return self.w_False

    # short-cut
    def is_w(self, w_one, w_two):
        return w_one is w_two

    def is_true(self, w_obj):
        # a shortcut for performance
        # NOTE! this method is typically overridden by builtinshortcut.py.
        if type(w_obj) is W_BoolObject:
            return w_obj.boolval
        return DescrOperation.is_true(self, w_obj)

    def getattr(self, w_obj, w_name):
        if not self.config.objspace.std.getattributeshortcut:
            return DescrOperation.getattr(self, w_obj, w_name)

        # an optional shortcut for performance
        from pypy.objspace.descroperation import raiseattrerror
        from pypy.objspace.descroperation import object_getattribute
        w_type = self.type(w_obj)
        if not w_type.uses_object_getattribute:
            # slow path: look for a custom __getattribute__ on the class
            w_descr = w_type.lookup('__getattribute__')
            # if it was not actually overriden in the class, we remember this
            # fact for the next time.
            if w_descr is object_getattribute(self):
                w_type.uses_object_getattribute = True
            return self._handle_getattribute(w_descr, w_obj, w_name)

        # fast path: XXX this is duplicating most of the logic
        # from the default __getattribute__ and the getattr() method...
        name = self.str_w(w_name)
        w_descr = w_type.lookup(name)
        e = None
        if w_descr is not None:
            if not self.is_data_descr(w_descr):
                w_value = w_obj.getdictvalue_attr_is_in_class(self, w_name)
                if w_value is not None:
                    return w_value
            try:
                return self.get(w_descr, w_obj)
            except OperationError, e:
                if not e.match(self, self.w_AttributeError):
                    raise
        else:
            w_value = w_obj.getdictvalue(self, w_name)
            if w_value is not None:
                return w_value

        w_descr = self.lookup(w_obj, '__getattr__')
        if w_descr is not None:
            return self.get_and_call_function(w_descr, w_obj, w_name)
        elif e is not None:
            raise e
        else:
            raiseattrerror(self, w_obj, name)

    def finditem(self, w_obj, w_key):
        # performance shortcut to avoid creating the OperationError(KeyError)
        if type(w_obj) is self.DictObjectCls:
            return w_obj.get(w_key, None)
        return ObjSpace.finditem(self, w_obj, w_key)

    def set_str_keyed_item(self, w_obj, w_key, w_value, shadows_type=True):
        # performance shortcut to avoid creating the OperationError(KeyError)
        if type(w_obj) is self.DictObjectCls:
            w_obj.set_str_keyed_item(w_key, w_value, shadows_type)
        else:
            self.setitem(w_obj, w_key, w_value)

    def getindex_w(self, w_obj, w_exception, objdescr=None):
        # Performance shortcut for the common case of w_obj being an int.
        # If withsmallint is disabled, we check for W_IntObject.
        # If withsmallint is enabled, we only check for W_SmallIntObject - it's
        # probably not useful to have a shortcut for W_IntObject at all then.
        if self.config.objspace.std.withsmallint:
            if type(w_obj) is W_SmallIntObject:
                return w_obj.intval
        else:
            if type(w_obj) is W_IntObject:
                return w_obj.intval
        return ObjSpace.getindex_w(self, w_obj, w_exception, objdescr)

    def call_method(self, w_obj, methname, *arg_w):
        if self.config.objspace.opcodes.CALL_METHOD:
            from pypy.objspace.std.callmethod import call_method_opt
            return call_method_opt(self, w_obj, methname, *arg_w)
        else:
            return ObjSpace.call_method(self, w_obj, methname, *arg_w)

    # support for the deprecated __getslice__, __setslice__, __delslice__

    def getslice(self, w_obj, w_start, w_stop):
        w_descr = self.lookup(w_obj, '__getslice__')
        if w_descr is not None:
            w_start, w_stop = old_slice_range(self, w_obj, w_start, w_stop)
            return self.get_and_call_function(w_descr, w_obj, w_start, w_stop)
        else:
            return ObjSpace.getslice(self, w_obj, w_start, w_stop)

    def setslice(self, w_obj, w_start, w_stop, w_sequence):
        w_descr = self.lookup(w_obj, '__setslice__')
        if w_descr is not None:
            w_start, w_stop = old_slice_range(self, w_obj, w_start, w_stop)
            self.get_and_call_function(w_descr, w_obj, w_start, w_stop,
                                       w_sequence)
        else:
            ObjSpace.setslice(self, w_obj, w_start, w_stop, w_sequence)

    def delslice(self, w_obj, w_start, w_stop):
        w_descr = self.lookup(w_obj, '__delslice__')
        if w_descr is not None:
            w_start, w_stop = old_slice_range(self, w_obj, w_start, w_stop)
            self.get_and_call_function(w_descr, w_obj, w_start, w_stop)
        else:
            ObjSpace.delslice(self, w_obj, w_start, w_stop)

    class MM:
        "Container for multimethods."
        call    = StdObjSpaceMultiMethod('call', 1, ['__call__'], general__args__=True)
        init    = StdObjSpaceMultiMethod('__init__', 1, general__args__=True)
        getnewargs = StdObjSpaceMultiMethod('__getnewargs__', 1)
        # special visible multimethods
        int_w   = StdObjSpaceMultiMethod('int_w', 1, [])     # returns an unwrapped int
        str_w   = StdObjSpaceMultiMethod('str_w', 1, [])     # returns an unwrapped string
        float_w = StdObjSpaceMultiMethod('float_w', 1, [])   # returns an unwrapped float
        uint_w  = StdObjSpaceMultiMethod('uint_w', 1, [])    # returns an unwrapped unsigned int (r_uint)
        unicode_w = StdObjSpaceMultiMethod('unicode_w', 1, [])    # returns an unwrapped list of unicode characters
        bigint_w = StdObjSpaceMultiMethod('bigint_w', 1, []) # returns an unwrapped rbigint
        # NOTE: when adding more sometype_w() methods, you need to write a
        # stub in default.py to raise a space.w_TypeError
        marshal_w = StdObjSpaceMultiMethod('marshal_w', 1, [], extra_args=['marshaller'])
        log     = StdObjSpaceMultiMethod('log', 1, [], extra_args=['base'])

        # add all regular multimethods here
        for _name, _symbol, _arity, _specialnames in ObjSpace.MethodTable:
            if _name not in locals():
                mm = StdObjSpaceMultiMethod(_symbol, _arity, _specialnames)
                locals()[_name] = mm
                del mm

        pow.extras['defaults'] = (None,)


# what is the maximum value slices can get on CPython?
# we need to stick to that value, because fake.py etc.
class Temp:
    def __getslice__(self, i, j):
        return j
slice_max = Temp()[:]
del Temp


def old_slice_range(space, w_obj, w_start, w_stop):
    """Only for backward compatibility for __getslice__()&co methods."""
    if space.is_w(w_start, space.w_None):
        w_start = space.wrap(0)
    else:
        w_start = space.wrap(space.getindex_w(w_start, None))
        if space.is_true(space.lt(w_start, space.wrap(0))):
            w_start = space.add(w_start, space.len(w_obj))
            # NB. the language ref is inconsistent with the new-style class
            # behavior when w_obj doesn't implement __len__(), so we just
            # ignore this case.
    if space.is_w(w_stop, space.w_None):
        w_stop = space.wrap(slice_max)
    else:
        w_stop = space.wrap(space.getindex_w(w_stop, None))
        if space.is_true(space.lt(w_stop, space.wrap(0))):
            w_stop = space.add(w_stop, space.len(w_obj))
    return w_start, w_stop
