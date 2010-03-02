from pypy.objspace.std.register_all import register_all
from pypy.interpreter.baseobjspace import ObjSpace, Wrappable, UnpackValueError
from pypy.interpreter.error import OperationError, operationerrfmt, debug_print
from pypy.interpreter.typedef import get_unique_interplevel_subclass
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
from pypy.objspace.std.multimethod import FailedToImplement, FailedToImplementArgs
from pypy.objspace.descroperation import DescrOperation, raiseattrerror
from pypy.objspace.std import stdtypedef
from pypy.rlib.rarithmetic import base_int
from pypy.rlib.objectmodel import we_are_translated
from pypy.rlib.jit import hint
from pypy.rlib.unroll import unrolling_iterable
import sys
import os
import __builtin__

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
                    w_value = w_globals.get_builtin_indexed(num)
                    if w_value is None:
                        builtins = f.get_builtin()
                        assert isinstance(builtins, Module)
                        w_builtin_dict = builtins.w_dict
                        assert isinstance(w_builtin_dict, W_DictMultiObject)
                        w_value = w_builtin_dict.get_builtin_indexed(num)
        ##                 if w_value is not None:
        ##                     print "CALL_LIKELY_BUILTIN fast"
                    if w_value is None:
                        varname = OPTIMIZED_BUILTINS[num]
                        message = "global name '%s' is not defined"
                        raise operationerrfmt(f.space.w_NameError,
                                              message, varname)
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
                        executioncontext = self.getexecutioncontext()
                        executioncontext.c_call_trace(f, w_function)
                        res = w_function.funccall_valuestack(nargs, f)
                        executioncontext.c_return_trace(f, w_function)
                        return res
                    args = f.make_arguments(nargs)
                    return f.space.call_args(w_function, args)

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

        # store the dict class on the space to access it in various places
        from pypy.objspace.std import dictmultiobject
        self.DictObjectCls = dictmultiobject.W_DictMultiObject

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
                if name.startswith('inplace_'):
                    fallback_name = name[len('inplace_'):]
                    if fallback_name in ('or', 'and'):
                        fallback_name += '_'
                    fallback_mm = self.MM.__dict__[fallback_name]
                else:
                    fallback_mm = None
                builtinshortcut.install(self, mm, fallback_mm)

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
        self.make_builtins()

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
        assert typedef is not None
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

    def newlong(self, val): # val is an int
        return W_LongObject.fromint(self, val)

    def newtuple(self, list_w):
        from pypy.objspace.std.tupletype import wraptuple
        assert isinstance(list_w, list)
        make_sure_not_resized(list_w)
        return wraptuple(self, list_w)

    def newlist(self, list_w):
        from pypy.objspace.std.listobject import W_ListObject
        return W_ListObject(list_w)

    def newdict(self, module=False, instance=False, classofinstance=None,
                from_strdict_shared=None, strdict=False):
        from pypy.objspace.std.dictmultiobject import W_DictMultiObject
        return W_DictMultiObject.allocate_and_init_instance(
                self, module=module, instance=instance,
                classofinstance=classofinstance,
                from_strdict_shared=from_strdict_shared,
                strdict=strdict)

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
            instance = instantiate(cls)
        elif cls.typedef.acceptable_as_base_class:
            # the purpose of the above check is to avoid the code below
            # to be annotated at all for 'cls' if it is not necessary
            w_subtype = w_type.check_user_subclass(w_subtype)
            if cls.typedef.applevel_subclasses_base is not None:
                cls = cls.typedef.applevel_subclasses_base
            subcls = get_unique_interplevel_subclass(
                    self.config, cls, w_subtype.hasdict, w_subtype.nslots != 0,
                    w_subtype.needsdel, w_subtype.weakrefable)
            instance = instantiate(subcls)
            assert isinstance(instance, cls)
            instance.user_setup(self, w_subtype)
        else:
            raise operationerrfmt(self.w_TypeError,
                "%s.__new__(%s): only for the type %s",
                w_type.name, w_subtype.getname(self, '?'), w_type.name)
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

    def fixedview(self, w_obj, expected_length=-1):
        """ Fast paths
        """
        if isinstance(w_obj, W_TupleObject):
            t = w_obj.wrappeditems
        elif isinstance(w_obj, W_ListObject):
            t = w_obj.wrappeditems[:]
        else:
            return ObjSpace.fixedview(self, w_obj, expected_length)
        if expected_length != -1 and len(t) != expected_length:
            raise UnpackValueError("Expected length %d, got %d" % (expected_length, len(t)))
        return t

    def listview(self, w_obj, expected_length=-1):
        if isinstance(w_obj, W_ListObject):
            t = w_obj.wrappeditems
        elif isinstance(w_obj, W_TupleObject):
            t = w_obj.wrappeditems[:]
        else:
            return ObjSpace.listview(self, w_obj, expected_length)
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
        w_type = self.type(w_obj)
        w_descr = w_type.getattribute_if_not_from_object()
        if w_descr is not None:
            return self._handle_getattribute(w_descr, w_obj, w_name)

        # fast path: XXX this is duplicating most of the logic
        # from the default __getattribute__ and the getattr() method...
        name = self.str_w(w_name)
        w_descr = w_type.lookup(name)
        e = None
        if w_descr is not None:
            w_get = None
            is_data = self.is_data_descr(w_descr)
            if is_data:
                w_get = self.lookup(w_descr, "__get__")
            if w_get is None:
                w_value = w_obj.getdictvalue_attr_is_in_class(self, name)
                if w_value is not None:
                    return w_value
                if not is_data:
                    w_get = self.lookup(w_descr, "__get__")
            if w_get is not None:
                # __get__ is allowed to raise an AttributeError to trigger
                # use of __getattr__.
                try:
                    return self.get_and_call_function(w_get, w_descr, w_obj,
                                                      w_type)
                except OperationError, e:
                    if not e.match(self, self.w_AttributeError):
                        raise
            else:
                return w_descr
        else:
            w_value = w_obj.getdictvalue(self, name)
            if w_value is not None:
                return w_value

        w_descr = self.lookup(w_obj, '__getattr__')
        if w_descr is not None:
            return self.get_and_call_function(w_descr, w_obj, w_name)
        elif e is not None:
            raise e
        else:
            raiseattrerror(self, w_obj, name)

    def finditem_str(self, w_obj, key):
        # performance shortcut to avoid creating the OperationError(KeyError)
        if (isinstance(w_obj, self.DictObjectCls) and
                not w_obj.user_overridden_class):
            return w_obj.getitem_str(key)
        return ObjSpace.finditem_str(self, w_obj, key)

    def finditem(self, w_obj, w_key):
        # performance shortcut to avoid creating the OperationError(KeyError)
        if (isinstance(w_obj, self.DictObjectCls) and
                not w_obj.user_overridden_class):
            return w_obj.getitem(w_key)
        return ObjSpace.finditem(self, w_obj, w_key)

    def set_str_keyed_item(self, w_obj, key, w_value, shadows_type=True):
        # performance shortcut to avoid creating the OperationError(KeyError)
        if (isinstance(w_obj, self.DictObjectCls) and
                not w_obj.user_overridden_class):
            w_obj.set_str_keyed_item(key, w_value, shadows_type)
        else:
            self.setitem(w_obj, self.wrap(key), w_value)

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

    def raise_key_error(self, w_key):
        e = self.call_function(self.w_KeyError, w_key)
        raise OperationError(self.w_KeyError, e)

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
