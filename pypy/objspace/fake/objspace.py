from pypy.interpreter.baseobjspace import W_Root, ObjSpace
from pypy.interpreter.baseobjspace import Wrappable, SpaceCache
from pypy.interpreter import argument, gateway
from pypy.interpreter.typedef import TypeDef, GetSetProperty
from pypy.annotation.model import SomeInstance, s_None
from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.rpython.lltypesystem import lltype
from pypy.tool.sourcetools import compile2, func_with_new_name
from pypy.rlib.unroll import unrolling_iterable
from pypy.rlib.objectmodel import instantiate, we_are_translated
from pypy.rlib.nonconst import NonConstant
from pypy.rlib.rarithmetic import r_uint, r_singlefloat
from pypy.translator.translator import TranslationContext
from pypy.tool.option import make_config


class W_MyObject(Wrappable):
    typedef = None

    def getdict(self, space):
        return w_obj_or_none()

    def getdictvalue(self, space, attr):
        attr + "xx"   # check that it's a string
        return w_obj_or_none()

    def setdictvalue(self, space, attr, w_value):
        attr + "xx"   # check that it's a string
        is_root(w_value)
        return NonConstant(True)

    def deldictvalue(self, space, attr):
        attr + "xx"   # check that it's a string
        return NonConstant(True)

    def setdict(self, space, w_dict):
        is_root(w_dict)

    def setclass(self, space, w_subtype):
        is_root(w_subtype)

    def str_w(self, space):
        return NonConstant("foobar")

    def unicode_w(self, space):
        return NonConstant(u"foobar")

    def int_w(self, space):
        return NonConstant(-42)
    
    def uint_w(self, space):
        return r_uint(NonConstant(42))
    
    def bigint_w(self, space):
        from pypy.rlib.rbigint import rbigint
        return rbigint.fromint(NonConstant(42))


def w_some_obj():
    if NonConstant(False):
        return W_Root()
    return W_MyObject()

def w_obj_or_none():
    if NonConstant(False):
        return None
    return w_some_obj()

def is_root(w_obj):
    assert isinstance(w_obj, W_Root)
is_root.expecting = W_Root

def is_arguments(arg):
    assert isinstance(arg, argument.Arguments)
is_arguments.expecting = argument.Arguments


class Entry(ExtRegistryEntry):
    _about_ = is_root, is_arguments

    def compute_result_annotation(self, s_w_obj):
        cls = self.instance.expecting
        s_inst = SomeInstance(self.bookkeeper.getuniqueclassdef(cls),
                              can_be_None=True)
        assert s_inst.contains(s_w_obj)
        return s_None

    def specialize_call(self, hop):
        hop.exception_cannot_occur()
        return hop.inputconst(lltype.Void, None)

# ____________________________________________________________


class FakeObjSpace(ObjSpace):

    def __init__(self, config=None):
        self._seen_extras = []
        ObjSpace.__init__(self, config=config)

    def float_w(self, w_obj):
        is_root(w_obj)
        return NonConstant(42.5)

    def is_true(self, w_obj):
        is_root(w_obj)
        return NonConstant(False)

    def unwrap(self, w_obj):
        "NOT_RPYTHON"
        raise NotImplementedError

    def newdict(self, module=False, instance=False, kwargs=False,
                strdict=False):
        return w_some_obj()

    def newtuple(self, list_w):
        for w_x in list_w:
            is_root(w_x)
        return w_some_obj()

    def newlist(self, list_w):
        for w_x in list_w:
            is_root(w_x)
        return w_some_obj()

    def newslice(self, w_start, w_end, w_step):
        is_root(w_start)
        is_root(w_end)
        is_root(w_step)
        return w_some_obj()

    def newint(self, x):
        return w_some_obj()

    def newfloat(self, x):
        return w_some_obj()

    def newcomplex(self, x, y):
        return w_some_obj()

    def marshal_w(self, w_obj):
        "NOT_RPYTHON"
        raise NotImplementedError

    def wrap(self, x):
        if not we_are_translated():
            if isinstance(x, gateway.interp2app):
                self._see_interp2app(x)
            if isinstance(x, GetSetProperty):
                self._see_getsetproperty(x)
        if isinstance(x, r_singlefloat):
            self._wrap_not_rpython(x)
        if isinstance(x, list):
            self._wrap_not_rpython(x)
        return w_some_obj()
    wrap._annspecialcase_ = "specialize:argtype(1)"

    def _wrap_not_rpython(self, x):
        "NOT_RPYTHON"
        raise NotImplementedError

    def _see_interp2app(self, interp2app):
        "NOT_RPYTHON"
        activation = interp2app._code.activation
        def check():
            scope_w = [w_some_obj()] * NonConstant(42)
            w_result = activation._run(self, scope_w)
            is_root(w_result)
        check = func_with_new_name(check, 'check__' + interp2app.name)
        self._seen_extras.append(check)

    def _see_getsetproperty(self, getsetproperty):
        "NOT_RPYTHON"
        space = self
        def checkprop():
            getsetproperty.fget(getsetproperty, space, w_some_obj())
            if getsetproperty.fset is not None:
                getsetproperty.fset(getsetproperty, space, w_some_obj(),
                                    w_some_obj())
            if getsetproperty.fdel is not None:
                getsetproperty.fdel(getsetproperty, space, w_some_obj())
        if not getsetproperty.name.startswith('<'):
            checkprop = func_with_new_name(checkprop,
                                           'checkprop__' + getsetproperty.name)
        self._seen_extras.append(checkprop)

    def call_obj_args(self, w_callable, w_obj, args):
        is_root(w_callable)
        is_root(w_obj)
        is_arguments(args)
        return w_some_obj()

    def call(self, w_callable, w_args, w_kwds=None):
        is_root(w_callable)
        is_root(w_args)
        is_root(w_kwds)
        return w_some_obj()

    def call_function(self, w_func, *args_w):
        is_root(w_func)
        for w_arg in list(args_w):
            is_root(w_arg)
        return w_some_obj()

    def call_args(self, w_func, args):
        is_root(w_func)
        is_arguments(args)
        return w_some_obj()

    def get_and_call_function(space, w_descr, w_obj, *args_w):
        args = argument.Arguments(space, list(args_w))
        w_impl = space.get(w_descr, w_obj)
        return space.call_args(w_impl, args)

    def gettypefor(self, cls):
        return self.gettypeobject(cls.typedef)

    def gettypeobject(self, typedef):
        assert typedef is not None
        return self.fromcache(TypeCache).getorbuild(typedef)

    def unpackiterable(self, w_iterable, expected_length=-1):
        is_root(w_iterable)
        if expected_length < 0:
            expected_length = 3
        return [w_some_obj()] * expected_length

    def unpackcomplex(self, w_complex):
        is_root(w_complex)
        return 1.1, 2.2

    def allocate_instance(self, cls, w_subtype):
        is_root(w_subtype)
        return instantiate(cls)
    allocate_instance._annspecialcase_ = "specialize:arg(1)"

    def decode_index(self, w_index_or_slice, seqlength):
        is_root(w_index_or_slice)
        return (NonConstant(42), NonConstant(42), NonConstant(42))

    def decode_index4(self, w_index_or_slice, seqlength):
        is_root(w_index_or_slice)
        return (NonConstant(42), NonConstant(42),
                NonConstant(42), NonConstant(42))

    def exec_(self, *args, **kwds):
        pass

    def createexecutioncontext(self):
        ec = ObjSpace.createexecutioncontext(self)
        ec._py_repr = None
        return ec

    # ----------

    def translates(self, func=None, argtypes=None, **kwds):
        config = make_config(None, **kwds)
        if func is not None:
            if argtypes is None:
                nb_args = func.func_code.co_argcount
                argtypes = [W_Root] * nb_args
        #
        t = TranslationContext(config=config)
        self.t = t     # for debugging
        ann = t.buildannotator()
        ann.policy.allow_someobjects = False
        if func is not None:
            ann.build_types(func, argtypes, complete_now=False)
        #
        # annotate all _seen_extras, knowing that annotating some may
        # grow the list
        done = 0
        while done < len(self._seen_extras):
            #print self._seen_extras
            ann.build_types(self._seen_extras[done], [],
                            complete_now=False)
            done += 1
        ann.complete()
        #t.viewcg()
        t.buildrtyper().specialize()
        t.checkgraphs()


def setup():
    for name in (ObjSpace.ConstantTable +
                 ObjSpace.ExceptionTable +
                 ['int', 'str', 'float', 'long', 'tuple', 'list',
                  'dict', 'unicode', 'complex', 'slice', 'bool',
                  'type', 'basestring', 'object']):
        setattr(FakeObjSpace, 'w_' + name, w_some_obj())
    #
    for (name, _, arity, _) in ObjSpace.MethodTable:
        args = ['w_%d' % i for i in range(arity)]
        params = args[:]
        d = {'is_root': is_root,
             'w_some_obj': w_some_obj}
        if name in ('get',):
            params[-1] += '=None'
        exec compile2("""\
            def meth(self, %s):
                %s
                return w_some_obj()
        """ % (', '.join(params),
               '; '.join(['is_root(%s)' % arg for arg in args]))) in d
        meth = func_with_new_name(d['meth'], name)
        setattr(FakeObjSpace, name, meth)
    #
    for name in ObjSpace.IrregularOpTable:
        assert hasattr(FakeObjSpace, name)    # missing?

setup()

# ____________________________________________________________

class TypeCache(SpaceCache):
    def build(cache, typedef):
        assert isinstance(typedef, TypeDef)
        for value in typedef.rawdict.values():
            cache.space.wrap(value)
        return w_some_obj()

class FakeCompiler(object):
    pass
FakeObjSpace.default_compiler = FakeCompiler()

class FakeModule(Wrappable):
    def __init__(self):
        self.w_dict = w_some_obj()
    def get(self, name):
        name + "xx"   # check that it's a string
        return w_some_obj()
FakeObjSpace.sys = FakeModule()
FakeObjSpace.sys.filesystemencoding = 'foobar'
FakeObjSpace.sys.defaultencoding = 'ascii'
FakeObjSpace.builtin = FakeModule()
