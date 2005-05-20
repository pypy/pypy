from pypy.interpreter.executioncontext import ExecutionContext
from pypy.interpreter.error import OperationError
from pypy.interpreter.argument import Arguments
from pypy.interpreter.miscutils import ThreadLocals
from pypy.tool.cache import Cache 
from pypy.rpython.rarithmetic import r_uint

__all__ = ['ObjSpace', 'OperationError', 'Wrappable', 'BaseWrappable',
           'W_Root']


class W_Root:
    """This is the abstract root class of all wrapped objects that live
    in a 'normal' object space like StdObjSpace."""
    def getdict(self):
        return None

    def getdictvalue(self, space, attr):
        w_dict = self.getdict()
        if w_dict is not None:
            try:
                return space.getitem(w_dict, space.wrap(attr))
            except OperationError, e:
                if not e.match(space, space.w_KeyError):
                    raise
        return None

    def setdict(self, space, w_dict):
        typename = space.type(self).getname(space, '?')
        raise OperationError(space.w_TypeError,
                             space.wrap("attribute '__dict__' of %s objects "
                                        "is not writable" % typename))

    def getclass(self, space):
        return space.gettypeobject(self.typedef)

    def setclass(self, space, w_subtype):
        raise OperationError(space.w_TypeError,
                             space.wrap("__class__ assignment: only for heap types"))

    def getname(self, space, default):
        try:
            return space.str_w(space.getattr(self, space.wrap('__name__')))
        except OperationError, e:
            if e.match(space, space.w_TypeError) or e.match(space, space.w_AttributeError):
                return default
            raise

    def getrepr(self, space, info):
        id = space.int_w(space.id(self)) # xxx ids could be long
        id = r_uint(id) # XXX what about sizeof(void*) > sizeof(long) !!
        return space.wrap("<%s at 0x%x>" % (info, id))

class BaseWrappable(W_Root):
    """A subclass of BaseWrappable is an internal, interpreter-level class
    that can nevertheless be exposed at application-level by space.wrap()."""
    def __spacebind__(self, space):
        return self

class Wrappable(BaseWrappable, object):
    """Same as BaseWrappable, just new-style instead."""


class InternalSpaceCache(Cache):
    """A generic cache for an object space.  Arbitrary information can
    be attached to the space by defining a function or class 'f' which
    can be called as 'f(space)'.  Its result is stored in this
    ObjSpaceCache.
    """
    def __init__(self, space):
        Cache.__init__(self)
        self.space = space
    def _build(self, callable):
        return callable(self.space)

class SpaceCache(Cache):
    """A base class for all our concrete caches."""
    def __init__(self, space):
        Cache.__init__(self)
        self.space = space
    def _build(self, key):
        val = self.space.enter_cache_building_mode()
        try:
            return self.build(key)
        finally:
            self.space.leave_cache_building_mode(val)


class ObjSpace(object):
    """Base class for the interpreter-level implementations of object spaces.
    http://codespeak.net/moin/pypy/moin.cgi/ObjectSpace"""
    
    full_exceptions = True  # full support for exceptions (normalization & more)

    def __init__(self):
        "NOT_RPYTHON: Basic initialization of objects."
        self.fromcache = InternalSpaceCache(self).getorbuild
        self.threadlocals = ThreadLocals()
        # set recursion limit
        # sets all the internal descriptors
        self.initialize()

    def __repr__(self):
        return self.__class__.__name__

    def setbuiltinmodule(self, name, importname=None): 
        """NOT_RPYTHON. load a lazy pypy/module and put it into sys.modules"""
        if importname is None: 
            importname = name 
        Module = __import__("pypy.module.%s" % importname, 
                            None, None, ["Module"]).Module
        w_name = self.wrap(name) 
        w_mod = self.wrap(Module(self, w_name)) 
        w_modules = self.sys.get('modules')
        self.setitem(w_modules, w_name, w_mod) 

    def make_builtins(self):
        "NOT_RPYTHON: only for initializing the space."

        from pypy.module.sys import Module 
        w_name = self.wrap('sys')
        self.sys = Module(self, w_name) 
        w_modules = self.sys.get('modules')
        self.setitem(w_modules, w_name, self.wrap(self.sys))

        from pypy.module.__builtin__ import Module 
        w_name = self.wrap('__builtin__')
        self.builtin = Module(self, w_name) 
        w_builtin = self.wrap(self.builtin)
        self.setitem(w_modules, w_name, w_builtin) 
        self.setitem(self.builtin.w_dict, self.wrap('__builtins__'), w_builtin) 

        # XXX we need to resolve unwrapping issues to 
        #     make this the default _sre module
        #self.setbuiltinmodule("_sre", "_sre_pypy") 

        # XXX disabled: self.setbuiltinmodule('parser')

        # initialize with "bootstrap types" from objspace  (e.g. w_None)
        for name, value in self.__dict__.items():
            if name.startswith('w_') and not name.endswith('Type'): 
                name = name[2:]
                #print "setitem: space instance %-20s into builtins" % name
                self.setitem(self.builtin.w_dict, self.wrap(name), value)

    def initialize(self):
        """NOT_RPYTHON: Abstract method that should put some minimal
        content into the w_builtins."""

    def enter_cache_building_mode(self):
        "hook for the flow object space"
    def leave_cache_building_mode(self, val):
        "hook for the flow object space"

    def get_ec_state_dict(self):
        "Return the 'state dict' from the active execution context."
        return self.getexecutioncontext().get_state_dict()
    
    def getexecutioncontext(self):
        "Return what we consider to be the active execution context."
        ec = self.threadlocals.executioncontext
        if ec is None:
            ec = self.createexecutioncontext()
            self.threadlocals.executioncontext = ec
        return ec

    def _freeze_(self):
        # Important: the annotator must not see a prebuilt ExecutionContext
        # for reasons related to the specialization of the framestack attribute
        # so we make sure there is no executioncontext at freeze-time
        self.threadlocals.executioncontext = None
        return True 

    def createexecutioncontext(self):
        "Factory function for execution contexts."
        return ExecutionContext(self)

    # Following is a friendly interface to common object space operations
    # that can be defined in term of more primitive ones.  Subclasses
    # may also override specific functions for performance.

    #def is_(self, w_x, w_y):   -- not really useful.  Must be subclassed
    #    "'x is y'."
    #    w_id_x = self.id(w_x)
    #    w_id_y = self.id(w_y)
    #    return self.eq(w_id_x, w_id_y)

    def not_(self, w_obj):
        return self.wrap(not self.is_true(w_obj))

    def eq_w(self, w_obj1, w_obj2):
        """shortcut for space.is_true(space.eq(w_obj1, w_obj2))"""
        return self.is_w(w_obj1, w_obj2) or self.is_true(self.eq(w_obj1, w_obj2))

    def is_w(self, w_obj1, w_obj2):
        """shortcut for space.is_true(space.is_(w_obj1, w_obj2))"""
        return self.is_true(self.is_(w_obj1, w_obj2))

    def newbool(self, b):
        if b:
            return self.w_True
        else:
            return self.w_False

    # support for the deprecated __getslice__, __setslice__, __delslice__
    def getslice(self, w_obj, w_start, w_stop):
        w_slice = self.newslice(w_start, w_stop, self.w_None)
        return self.getitem(w_obj, w_slice)
    def setslice(self, w_obj, w_start, w_stop, w_sequence):
        w_slice = self.newslice(w_start, w_stop, self.w_None)
        self.setitem(w_obj, w_slice, w_sequence)
    def delslice(self, w_obj, w_start, w_stop):
        w_slice = self.newslice(w_start, w_stop, self.w_None)
        self.delitem(w_obj, w_slice)

    def interpclass_w(space, w_obj):
        """
         If w_obj is a wrapped internal interpreter class instance unwrap to it,
         otherwise return None
        """
        if isinstance(w_obj, BaseWrappable):
            return w_obj
        return None

    def unpackiterable(self, w_iterable, expected_length=-1):
        """Unpack an iterable object into a real (interpreter-level) list.
        Raise a real ValueError if the length is wrong."""
        w_iterator = self.iter(w_iterable)
        items = []
        while True:
            try:
                w_item = self.next(w_iterator)
            except OperationError, e:
                if not e.match(self, self.w_StopIteration):
                    raise
                break  # done
            if expected_length != -1 and len(items) == expected_length:
                raise ValueError, "too many values to unpack"
            items.append(w_item)
        if expected_length != -1 and len(items) < expected_length:
            i = len(items)
            if i == 1:
                plural = ""
            else:
                plural = "s"
            raise ValueError, "need more than %d value%s to unpack" % (i, plural)
        return items

    def unpacktuple(self, w_tuple, expected_length=-1):
        """Same as unpackiterable(), but only for tuples.
        Only use for bootstrapping or performance reasons."""
        tuple_length = self.int_w(self.len(w_tuple))
        if expected_length != -1 and tuple_length != expected_length:
            raise ValueError, "got a tuple of length %d instead of %d" % (
                tuple_length, expected_length)
        items = [
            self.getitem(w_tuple, self.wrap(i)) for i in range(tuple_length)]
        return items

    def exception_match(self, w_exc_type, w_check_class):
        """Checks if the given exception type matches 'w_check_class'."""
        check_list = [w_check_class]
        while check_list:
            w_item = check_list.pop()
            # Match identical items.
            if self.is_true(self.is_(w_exc_type, w_item)):
                return True
            try:
                # Match subclasses.
                if self.is_true(self.abstract_issubclass(w_exc_type, w_item, failhard=True)):
                    return True
            except OperationError:
                # Assume that this is a TypeError: w_item not a type,
                # and assume that w_item is then actually a tuple.
                try:
                    exclst = self.unpackiterable(w_item)
                except OperationError:
                    # hum, maybe it is not a tuple after all, and w_exc_type
                    # was not a type at all (string exceptions).  Give up.
                    continue
                check_list.extend(exclst)
        return False

    def call(self, w_callable, w_args, w_kwds=None):
        args = Arguments.frompacked(self, w_args, w_kwds)
        return self.call_args(w_callable, args)

    def call_function(self, w_func, *args_w):
        args = Arguments(self, list(args_w))
        return self.call_args(w_func, args)

    def call_method(self, w_obj, methname, *arg_w):
        w_meth = self.getattr(w_obj, self.wrap(methname))
        return self.call_function(w_meth, *arg_w)

    def isinstance(self, w_obj, w_type):
        w_objtype = self.type(w_obj)
        return self.issubtype(w_objtype, w_type)

    def abstract_issubclass(self, w_obj, w_cls, failhard=False):
        try:
            return self.issubtype(w_obj, w_cls)
        except OperationError:
            try:
                self.getattr(w_cls, self.wrap('__bases__')) # type sanity check
                return self.recursive_issubclass(w_obj, w_cls)
            except OperationError:
                if failhard:
                    raise
                else:
                    return self.w_False

    def recursive_issubclass(self, w_obj, w_cls):
        if self.is_w(w_obj, w_cls):
            return self.w_True
        for w_base in self.unpackiterable(self.getattr(w_obj, 
                                                       self.wrap('__bases__'))):
            if self.is_true(self.recursive_issubclass(w_base, w_cls)):
                return self.w_True
        return self.w_False

    def abstract_isinstance(self, w_obj, w_cls):
        try:
            return self.isinstance(w_obj, w_cls)
        except OperationError:
            try:
                w_objcls = self.getattr(w_obj, self.wrap('__class__'))
                return self.abstract_issubclass(w_objcls, w_cls)
            except OperationError:
                return self.w_False

    def abstract_isclass(self, w_obj):
        if self.is_true(self.isinstance(w_obj, self.w_type)):
            return self.w_True
        try:
            self.getattr(w_obj, self.wrap('__bases__'))
        except OperationError:
            return self.w_False
        else:
            return self.w_True

    def abstract_getclass(self, w_obj):
        return self.getattr(w_obj, self.wrap('__class__'))

    def eval(self, expression, w_globals, w_locals):
        "NOT_RPYTHON: For internal debugging."
        import types
        from pypy.interpreter.pycode import PyCode
        if isinstance(expression, str):
            expression = compile(expression, '?', 'eval')
        if isinstance(expression, types.CodeType):
            expression = PyCode(self)._from_code(expression)
        if not isinstance(expression, PyCode):
            raise TypeError, 'space.eval(): expected a string, code or PyCode object'
        return expression.exec_code(self, w_globals, w_locals)

    def exec_(self, statement, w_globals, w_locals):
        "NOT_RPYTHON: For internal debugging."
        import types
        from pypy.interpreter.pycode import PyCode
        if isinstance(statement, str):
            statement = compile(statement, '?', 'exec')
        if isinstance(statement, types.CodeType):
            statement = PyCode(self)._from_code(statement)
        if not isinstance(statement, PyCode):
            raise TypeError, 'space.exec_(): expected a string, code or PyCode object'
        w_key = self.wrap('__builtins__')
        if not self.is_true(self.contains(w_globals, w_key)):
            self.setitem(w_globals, w_key, self.wrap(self.builtin))
        return statement.exec_code(self, w_globals, w_locals)

    def appexec(self, posargs_w, source): 
        """ return value from executing given source at applevel.
            EXPERIMENTAL. The source must look like
               '''(x, y):
                       do_stuff...
                       return result
               '''
        """
        w_func = self.fromcache(AppExecCache).getorbuild(source)
        args = Arguments(self, posargs_w)
        return self.call_args(w_func, args)

class AppExecCache(SpaceCache):
    def build(cache, source):
        """ NOT_RPYTHON """
        space = cache.space
        # XXX will change once we have our own compiler 
        from pypy.interpreter.pycode import PyCode
        import py
        source = source.lstrip()
        assert source.startswith('('), "incorrect header in:\n%s" % (source,)
        source = py.code.Source("def anonymous%s\n" % source)
        w_glob = space.newdict([])
        space.exec_(source.compile(), w_glob, w_glob)
        return space.getitem(w_glob, space.wrap('anonymous'))

## Table describing the regular part of the interface of object spaces,
## namely all methods which only take w_ arguments and return a w_ result
## (if any).  Note: keep in sync with pypy.objspace.flow.operation.Table.

ObjSpace.MethodTable = [
# method name # symbol # number of arguments # special method name(s)
    ('is_',             'is',        2, []),
    ('id',              'id',        1, []),
    ('type',            'type',      1, []),
    ('issubtype',       'issubtype', 2, []),  # not for old-style classes
    ('repr',            'repr',      1, ['__repr__']),
    ('str',             'str',       1, ['__str__']),
    ('len',             'len',       1, ['__len__']),
    ('hash',            'hash',      1, ['__hash__']),
    ('getattr',         'getattr',   2, ['__getattribute__']),
    ('setattr',         'setattr',   3, ['__setattr__']),
    ('delattr',         'delattr',   2, ['__delattr__']),
    ('getitem',         'getitem',   2, ['__getitem__']),
    ('setitem',         'setitem',   3, ['__setitem__']),
    ('delitem',         'delitem',   2, ['__delitem__']),
    ('pos',             'pos',       1, ['__pos__']),
    ('neg',             'neg',       1, ['__neg__']),
    ('nonzero',         'truth',     1, ['__nonzero__']),
    ('abs' ,            'abs',       1, ['__abs__']),
    ('hex',             'hex',       1, ['__hex__']),
    ('oct',             'oct',       1, ['__oct__']),
    ('ord',             'ord',       1, []),
    ('invert',          '~',         1, ['__invert__']),
    ('add',             '+',         2, ['__add__', '__radd__']),
    ('sub',             '-',         2, ['__sub__', '__rsub__']),
    ('mul',             '*',         2, ['__mul__', '__rmul__']),
    ('truediv',         '/',         2, ['__truediv__', '__rtruediv__']),
    ('floordiv',        '//',        2, ['__floordiv__', '__rfloordiv__']),
    ('div',             'div',       2, ['__div__', '__rdiv__']),
    ('mod',             '%',         2, ['__mod__', '__rmod__']),
    ('divmod',          'divmod',    2, ['__divmod__', '__rdivmod__']),
    ('pow',             '**',        3, ['__pow__', '__rpow__']),
    ('lshift',          '<<',        2, ['__lshift__', '__rlshift__']),
    ('rshift',          '>>',        2, ['__rshift__', '__rrshift__']),
    ('and_',            '&',         2, ['__and__', '__rand__']),
    ('or_',             '|',         2, ['__or__', '__ror__']),
    ('xor',             '^',         2, ['__xor__', '__rxor__']),
    ('int',             'int',       1, ['__int__']),
    ('float',           'float',     1, ['__float__']),
    ('long',            'long',      1, ['__long__']),
    ('inplace_add',     '+=',        2, ['__iadd__']),
    ('inplace_sub',     '-=',        2, ['__isub__']),
    ('inplace_mul',     '*=',        2, ['__imul__']),
    ('inplace_truediv', '/=',        2, ['__itruediv__']),
    ('inplace_floordiv','//=',       2, ['__ifloordiv__']),
    ('inplace_div',     'div=',      2, ['__idiv__']),
    ('inplace_mod',     '%=',        2, ['__imod__']),
    ('inplace_pow',     '**=',       2, ['__ipow__']),
    ('inplace_lshift',  '<<=',       2, ['__ilshift__']),
    ('inplace_rshift',  '>>=',       2, ['__irshift__']),
    ('inplace_and',     '&=',        2, ['__iand__']),
    ('inplace_or',      '|=',        2, ['__ior__']),
    ('inplace_xor',     '^=',        2, ['__ixor__']),
    ('lt',              '<',         2, ['__lt__', '__gt__']),
    ('le',              '<=',        2, ['__le__', '__ge__']),
    ('eq',              '==',        2, ['__eq__', '__eq__']),
    ('ne',              '!=',        2, ['__ne__', '__ne__']),
    ('gt',              '>',         2, ['__gt__', '__lt__']),
    ('ge',              '>=',        2, ['__ge__', '__le__']),
    ('cmp',             'cmp',       2, ['__cmp__']),   # rich cmps preferred
    ('coerce',          'coerce',    2, ['__coerce__', '__coerce__']),
    ('contains',        'contains',  2, ['__contains__']),
    ('iter',            'iter',      1, ['__iter__']),
    ('next',            'next',      1, ['next']),
#    ('call',            'call',      3, ['__call__']),
    ('get',             'get',       3, ['__get__']),
    ('set',             'set',       3, ['__set__']),
    ('delete',          'delete',    2, ['__delete__']),
    ('userdel',         'del',       2, ['__del__']),
    ]

ObjSpace.BuiltinModuleTable = [
    '__builtin__',
    'sys',
    ]

ObjSpace.ConstantTable = [
    'None',
    'False',
    'True',
    'Ellipsis',
    'NotImplemented',
    ]

ObjSpace.ExceptionTable = [
    'ArithmeticError',
    'AssertionError',
    'AttributeError',
    'EOFError',
    'EnvironmentError',
    'Exception',
    'FloatingPointError',
    'IOError',
    'ImportError',
    'IndentationError',
    'IndexError',
    'KeyError',
    'KeyboardInterrupt',
    'LookupError',
    'MemoryError',
    'NameError',
    'NotImplementedError',
    'OSError',
    'OverflowError',
    'ReferenceError',
    'RuntimeError',
    'StandardError',
    'StopIteration',
    'SyntaxError',
    'SystemError',
    'SystemExit',
    'TabError',
    'TypeError',
    'UnboundLocalError',
    'UnicodeError',
    'ValueError',
    'ZeroDivisionError',
    ]

## Irregular part of the interface:
#
#                                   wrap(x) -> w_x
#                              str_w(w_str) -> str
#              int_w(w_ival or w_long_ival) -> ival
#                       float_w(w_floatval) -> floatval
#             uint_w(w_ival or w_long_ival) -> r_uint_val (unsigned int value)
#interpclass_w(w_interpclass_inst or w_obj) -> interpclass_inst|w_obj
#                               unwrap(w_x) -> x
#                              is_true(w_x) -> True or False
#                  newtuple([w_1, w_2,...]) -> w_tuple
#                   newlist([w_1, w_2,...]) -> w_list
#                 newstring([w_1, w_2,...]) -> w_string from ascii numbers (bytes)
#            newdict([(w_key,w_value),...]) -> w_dict
#           newslice(w_start,w_stop,w_step) -> w_slice
#              call_args(w_obj,Arguments()) -> w_result

ObjSpace.IrregularOpTable = [
    'wrap',
    'str_w',
    'int_w',
    'float_w',
    'uint_w',
    'interpclass_w',
    'unwrap',
    'is_true',
    'is_w',
    'newtuple',
    'newlist',
    'newstring',
    'newdict',
    'newslice',
    'call_args'
    ]

