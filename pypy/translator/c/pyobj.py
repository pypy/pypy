from __future__ import generators
import autopath, os, sys, __builtin__, marshal, zlib
from types import FunctionType, CodeType, InstanceType, ClassType

from pypy.objspace.flow.model import Variable, Constant
from pypy.translator.gensupp import builtin_base, builtin_type_base
from pypy.translator.c.support import log
from pypy.translator.c.wrapper import gen_wrapper

from pypy.rpython.rarithmetic import r_int, r_uint
from pypy.rpython.lltypesystem.lltype import pyobjectptr, LowLevelType

# XXX maybe this can be done more elegantly:
# needed to convince should_translate_attr
# to fill the space instance.
# Should this be registered with the annotator?
from pypy.interpreter.baseobjspace import ObjSpace

class PyObjMaker:
    """Handles 'PyObject*'; factored out from LowLevelDatabase.
    This class contains all the nameof_xxx() methods that allow a wild variety
    of Python objects to be 'pickled' as Python source code that will
    reconstruct them.
    """

    def __init__(self, namespace, getvalue, translator=None):
        self.namespace = namespace
        self.getvalue = getvalue
        self.translator = translator
        self.initcode = [      # list of lines for the module's initxxx()
            'import new, types, sys',
            ]

        self.latercode = []    # list of generators generating extra lines
                               #   for later in initxxx() -- for recursive
                               #   objects
        self.debugstack = ()  # linked list of nested nameof()
        self.wrappers = {}    # {'pycfunctionvariable': ('name', 'wrapperfn')}
        self.import_hints = {} # I don't seem to need it any longer.
        # leaving the import support intact, doesn't hurt.

    def nameof(self, obj, debug=None):
        if debug:
            stackentry = debug, obj
        else:
            stackentry = obj
        self.debugstack = (self.debugstack, stackentry)
        try:
            return self.getvalue(pyobjectptr(obj))
        finally:
            self.debugstack, x = self.debugstack
            assert x is stackentry

    def computenameof(self, obj):
        obj_builtin_base = builtin_base(obj)
        if obj_builtin_base in (object, int, long) and type(obj) is not obj_builtin_base:
            # assume it's a user defined thingy
            return self.nameof_instance(obj)
        else:
            for cls in type(obj).__mro__:
                meth = getattr(self,
                               'nameof_' + cls.__name__.replace(' ', ''),
                               None)
                if meth:
                    break
            else:
                raise Exception, "nameof(%r)" % (obj,)
            return meth(obj)

    def uniquename(self, basename):
        return self.namespace.uniquename(basename)

    def initcode_python(self, name, pyexpr):
        # generate init code that will evaluate the given Python expression
        #self.initcode.append("print 'setting up', %r" % name)
        self.initcode.append("%s = %s" % (name, pyexpr))

    def nameof_object(self, value):
        if type(value) is not object:
            raise Exception, "nameof(%r)" % (value,)
        name = self.uniquename('g_object')
        self.initcode_python(name, "object()")
        return name

    def nameof_NoneType(self, value):
        assert value is None
        name = self.uniquename('g_None')
        self.initcode_python(name, "None")
        return name

    def nameof_bool(self, value):
        assert value is False or value is True
        if value:
            name = 'True'
        else:
            name = 'False'
        name = self.uniquename('g_' + name)
        self.initcode_python(name, repr(value))
        return name

    def nameof_module(self, value):
        easy = value is os or not hasattr(value, "__file__") or \
               not (value.__file__.endswith('.pyc') or
                    value.__file__.endswith('.py') or
                    value.__file__.endswith('.pyo'))
        name = self.uniquename('mod%s'%value.__name__)
        if not easy:
            self.initcode.append('######## warning ########')
            self.initcode.append('## %r is not a builtin module (probably :)' %value)
        access = "__import__(%r)" % value.__name__
        # this is an inlined version of my_import, see sect. 2.1 of the python docs
        for submodule in value.__name__.split('.')[1:]:
            access += '.' + submodule
        self.initcode_python(name, access)
        return name

    def _import_module(self, modname):
        mod = __import__(modname)
        for submodule in modname.split('.')[1:]:
            mod = getattr(mod, submodule)
        return mod

    def _find_in_module(self, obj, mod):
        if hasattr(obj, '__name__') and obj.__name__ in mod.__dict__:
            return obj.__name__
        for key, value in mod.__dict__.iteritems():
            if value is obj:
                return key
        raise ImportError, 'object %r cannot be found in %r' % (obj, mod)

    def nameof_int(self, value):
        if value >= 0:
            name = 'gint_%d' % value
        else:
            name = 'gint_minus%d' % abs(value)
        name = self.uniquename(name)
        self.initcode_python(name, repr(value))
        return name

    def nameof_long(self, value):
        if value >= 0:
            name = 'glong%d' % value
        else:
            name = 'glong_minus%d' % abs(value)
        name = self.uniquename(name)
        self.initcode_python(name, repr(value))
        return name

    def nameof_float(self, value):
        name = 'gfloat_%s' % value
        name = (name.replace('-', 'minus')
                    .replace('.', 'dot'))
        name = self.uniquename(name)
        self.initcode_python(name, repr(value))
        return name

    def nameof_str(self, value):
        name = self.uniquename('gstr_' + value[:32])
        self.initcode_python(name, repr(value))
        return name

    def nameof_unicode(self, value):
        name = self.uniquename('guni_' + str(value[:32]))
        self.initcode_python(name, repr(value))
        return name

    def skipped_function(self, func):
        # debugging only!  Generates a placeholder for missing functions
        # that raises an exception when called.
        if self.translator.annotator.frozen:
            warning = 'NOT GENERATING'
        else:
            warning = 'skipped'
        printable_name = '(%s:%d) %s' % (
            func.func_globals.get('__name__', '?'),
            func.func_code.co_firstlineno,
            func.__name__)
        log.WARNING("%s %s" % (warning, printable_name))
        name = self.uniquename('gskippedfunc_' + func.__name__)
        self.initcode.append('def %s(*a,**k):' % name)
        self.initcode.append('  raise NotImplementedError')
        return name

    def shouldskipfunc(self, func):
        if isinstance(func, (staticmethod, classmethod)):
            func = func.__get__(42)
        try: func = func.im_func
        except AttributeError: pass
        if isinstance(func, FunctionType):
            ann = self.translator.annotator
            if ann is None:
                if (func.func_doc and
                    func.func_doc.lstrip().startswith('NOT_RPYTHON')):
                    return "NOT_RPYTHON"   # True
            else:
                if not ann.bookkeeper.getdesc(func).querycallfamily():
                    return True
        return False

    def nameof_function(self, func):
        assert self.translator is not None, (
            "the Translator must be specified to build a PyObject "
            "wrapper for %r" % (func,))
        # shortcut imports
        if func in self.import_hints:
            return self.import_function(func)
        # look for skipped functions
        if self.shouldskipfunc(func):
            return self.skipped_function(func)

        fwrapper = gen_wrapper(func, self.translator)
        pycfunctionobj = self.uniquename('gfunc_' + func.__name__)
        self.wrappers[pycfunctionobj] = func.__name__, self.getvalue(fwrapper)
        return pycfunctionobj

    def import_function(self, func):
        name = self.uniquename('impfunc_' + func.__name__)
        modulestr = self.import_hints[func] or func.__module__
        module = self._import_module(modulestr)
        modname = self.nameof(module)
        obname = self._find_in_module(func, module)
        self.initcode_python(name, '%s.%s' % (modname, obname))
        return name

    def nameof_staticmethod(self, sm):
        # XXX XXX XXXX
        func = sm.__get__(42.5)
        name = self.uniquename('gsm_' + func.__name__)
        functionname = self.nameof(func)
        self.initcode_python(name, 'staticmethod(%s)' % functionname)
        return name

    def nameof_instancemethod(self, meth):
        if meth.im_self is None:
            # no error checking here
            return self.nameof(meth.im_func)
        else:
            ob = self.nameof(meth.im_self)
            func = self.nameof(meth.im_func)
            typ = self.nameof(meth.im_class)
            name = self.uniquename('gmeth_'+meth.im_func.__name__)
            self.initcode_python(name, 'new.instancemethod(%s, %s, %s)' % (
                func, ob, typ))
            return name

    nameof_method = nameof_instancemethod   # when run on top of PyPy

    def should_translate_attr(self, pbc, attr):
        ann = self.translator.annotator
        if ann is None or isinstance(pbc, ObjSpace):
            ignore = getattr(pbc.__class__, 'NOT_RPYTHON_ATTRIBUTES', [])
            if attr in ignore:
                return False
            else:
                return "probably"   # True
        classdef = ann.bookkeeper.immutablevalue(pbc).classdef
        if classdef and classdef.about_attribute(attr) is not None:
            return True
        return False

    def nameof_instance(self, instance):
        if instance in self.import_hints:
            return self.import_instance(instance)
        klass = instance.__class__
        if issubclass(klass, LowLevelType):
            raise Exception, 'nameof_LowLevelType(%r)' % (instance,)
        name = self.uniquename('ginst_' + klass.__name__)
        cls = self.nameof(klass)
        if hasattr(klass, '__base__'):
            base_class = builtin_base(instance)
            base = self.nameof(base_class)
        else:
            base_class = None
            base = cls
        def initinstance():
            content = instance.__dict__.items()
            content.sort()
            for key, value in content:
                if self.should_translate_attr(instance, key):
                    line = '%s.%s = %s' % (name, key, self.nameof(value))
                    yield line
        if hasattr(instance,'__reduce_ex__'):
            import copy_reg
            reduced = instance.__reduce_ex__()
            assert reduced[0] is copy_reg._reconstructor,"not clever enough"
            assert reduced[1][1] is base_class, "not clever enough for %r vs. %r" % (base_class, reduced)
            state = reduced[1][2]
        else:
            state = None
        self.initcode.append('if isinstance(%s, type):' % cls)
        if state is not None:
            self.initcode.append('    %s = %s.__new__(%s, %r)' % (name, base, cls, state))
        else:
            self.initcode.append('    %s = %s.__new__(%s)' % (name, base, cls))
        self.initcode.append('else:')
        self.initcode.append('    %s = new.instance(%s)' % (name, cls))
        self.later(initinstance())
        return name

    def import_instance(self, inst):
        klass = inst.__class__
        name = self.uniquename('impinst_' + klass.__name__)
        modulestr = self.import_hints[inst] or klass.__module__
        module = self._import_module(modulestr)
        modname = self.nameof(module)
        obname = self._find_in_module(func, module)
        self.initcode_python(name, '%s.%s' % (modname, obname))
        return name

    def nameof_builtin_function_or_method(self, func):
        if func.__self__ is None:
            # builtin function
            # where does it come from? Python2.2 doesn't have func.__module__
            for modname, module in sys.modules.items():
                if hasattr(module, '__file__'):
                    if (module.__file__.endswith('.py') or
                        module.__file__.endswith('.pyc') or
                        module.__file__.endswith('.pyo')):
                        continue    # skip non-builtin modules
                if func is getattr(module, func.__name__, None):
                    break
            else:
                raise Exception, '%r not found in any built-in module' % (func,)
            name = self.uniquename('gbltin_' + func.__name__)
            if modname == '__builtin__':
                self.initcode_python(name, func.__name__)
            else:
                modname = self.nameof(module)
                self.initcode_python(name, '%s.%s' % (modname, func.__name__))
        else:
            # builtin (bound) method
            name = self.uniquename('gbltinmethod_' + func.__name__)
            selfname = self.nameof(func.__self__)
            self.initcode_python(name, '%s.%s' % (selfname, func.__name__))
        return name

    def nameof_classobj(self, cls):
        if isinstance(cls, ClassType) or builtin_type_base(cls) is object:
            clsdef = self.translator.annotator.bookkeeper.getuniqueclassdef(cls)
            if self.translator.rtyper.needs_wrapper(clsdef):
                return self.wrap_exported_class(cls)

        if cls.__doc__ and cls.__doc__.lstrip().startswith('NOT_RPYTHON'):
            raise Exception, "%r should never be reached" % (cls,)

        if cls in self.import_hints:
            return self.import_classobj(cls)
        metaclass = "type"
        if issubclass(cls, Exception):
            # if cls.__module__ == 'exceptions':
            # don't rely on this, py.magic redefines AssertionError
            if getattr(__builtin__, cls.__name__, None) is cls:
                name = self.uniquename('gexc_' + cls.__name__)
                self.initcode_python(name, cls.__name__)
                return name
            #else:
            #    # exceptions must be old-style classes (grr!)
            #    metaclass = "&PyClass_Type"
        # For the moment, use old-style classes exactly when the
        # pypy source uses old-style classes, to avoid strange problems.
        if not isinstance(cls, type):
            assert type(cls) is ClassType
            metaclass = "types.ClassType"

        name = self.uniquename('gcls_' + cls.__name__)
        basenames = [self.nameof(base) for base in cls.__bases__]
        def initclassobj():
            content = cls.__dict__.items()
            content.sort()
            ignore = getattr(cls, 'NOT_RPYTHON_ATTRIBUTES', [])
            for key, value in content:
                if key.startswith('__'):
                    if key in ['__module__', '__doc__', '__dict__',
                               '__weakref__', '__repr__', '__metaclass__']:
                        continue
                    # XXX some __NAMES__ are important... nicer solution sought
                    #raise Exception, "unexpected name %r in class %s"%(key, cls)
                if key in ignore:
                    continue
                skip = self.shouldskipfunc(value)
                if skip:
                    if skip != 'NOT_RPYTHON':
                        log.WARNING("skipped class function: %r" % value)
                    continue
                yield '%s.%s = %s' % (name, key, self.nameof(value))

        baseargs = ", ".join(basenames)
        if baseargs:
            baseargs = '(%s)' % baseargs
        self.initcode.append('class %s%s:' % (name, baseargs))
        self.initcode.append('  __metaclass__ = %s' % metaclass)
        self.later(initclassobj())
        return name

    nameof_class = nameof_classobj   # for Python 2.2

    def import_classobj(self, cls):
        name = self.uniquename('impcls_' + cls.__name__)
        modulestr = self.import_hints[cls] or cls.__module__
        module = self._import_module(modulestr)
        modname = self.nameof(module)
        obname = self._find_in_module(cls, module)
        self.initcode_python(name, '%s.%s' % (modname, obname))
        return name

    typename_mapping = {
        InstanceType: 'types.InstanceType',
        type(None):   'type(None)',
        CodeType:     'types.CodeType',
        type(sys):    'type(new)',

        r_int:        'int',   # XXX
        r_uint:       'int',   # XXX

        # XXX more hacks
        # type 'builtin_function_or_method':
        type(len): 'type(len)',
        # type 'method_descriptor':
        type(list.append): 'type(list.append)',
        # type 'wrapper_descriptor':
        type(type(None).__repr__): 'type(type(None).__repr__)',
        # type 'getset_descriptor':
        type(type.__dict__['__dict__']): "type(type.__dict__['__dict__'])",
        # type 'member_descriptor':
        type(type.__dict__['__basicsize__']): "type(type.__dict__['__basicsize__'])",
        }

    def nameof_type(self, cls):
        if cls.__module__ != '__builtin__':
            return self.nameof_classobj(cls)   # user-defined type
        name = self.uniquename('gtype_%s' % cls.__name__)
        if getattr(__builtin__, cls.__name__, None) is cls:
            expr = cls.__name__    # type available from __builtin__
        else:
            expr = self.typename_mapping[cls]
        self.initcode_python(name, expr)
        return name

    def nameof_tuple(self, tup):
        name = self.uniquename('g%dtuple' % len(tup))
        args = [self.nameof(x) for x in tup]
        args = ', '.join(args)
        if args:
            args += ','
        self.initcode_python(name, '(%s)' % args)
        return name

    def nameof_list(self, lis):
        name = self.uniquename('g%dlist' % len(lis))
        def initlist():
            for i in range(len(lis)):
                item = self.nameof(lis[i])
                yield '%s.append(%s)' % (name, item)
        self.initcode_python(name, '[]')
        self.later(initlist())
        return name

    def nameof_dict(self, dic):
        assert dic is not __builtins__
        assert '__builtins__' not in dic, 'Seems to be the globals of %s' % (
            dic.get('__name__', '?'),)
        name = self.uniquename('g%ddict' % len(dic))
        def initdict():
            for k in dic:
                if type(k) is str:
                    yield '%s[%r] = %s' % (name, k, self.nameof(dic[k]))
                else:
                    yield '%s[%s] = %s' % (name, self.nameof(k),
                                           self.nameof(dic[k]))
        self.initcode_python(name, '{}')
        self.later(initdict())
        return name

    # strange prebuilt instances below, don't look too closely
    # XXX oh well.
    def nameof_member_descriptor(self, md):
        name = self.uniquename('gdescriptor_%s_%s' % (
            md.__objclass__.__name__, md.__name__))
        cls = self.nameof(md.__objclass__)
        self.initcode_python(name, '%s.__dict__[%r]' % (cls, md.__name__))
        return name
    nameof_getset_descriptor  = nameof_member_descriptor
    nameof_method_descriptor  = nameof_member_descriptor
    nameof_wrapper_descriptor = nameof_member_descriptor

    def nameof_file(self, fil):
        if fil is sys.stdin:
            name = self.uniquename("gsys_stdin")
            self.initcode_python(name, "sys.stdin")
            return name
        if fil is sys.stdout:
            name = self.uniquename("gsys_stdout")
            self.initcode_python(name, "sys.stdout")
            return name
        if fil is sys.stderr:
            name = self.uniquename("gsys_stderr")
            self.initcode_python(name, "sys.stderr")
            return name
        raise Exception, 'Cannot translate an already-open file: %r' % (fil,)


    def later(self, gen):
        self.latercode.append((gen, self.debugstack))

    def collect_initcode(self):
        while self.latercode:
            gen, self.debugstack = self.latercode.pop()
            #self.initcode.extend(gen) -- eats TypeError! bad CPython!
            for line in gen:
                self.initcode.append(line)
            self.debugstack = ()

    def getfrozenbytecode(self):
        self.initcode.append('')
        source = '\n'.join(self.initcode)
        del self.initcode[:]
        co = compile(source, '<initcode>', 'exec')
        originalsource = source
        small = zlib.compress(marshal.dumps(co))
        source = """if 1:
            import zlib, marshal
            exec marshal.loads(zlib.decompress(%r))""" % small
        # Python 2.2 SyntaxError without newline: Bug #501622
        source += '\n'
        co = compile(source, '<initcode>', 'exec')
        del source
        return marshal.dumps(co), originalsource

    # ____________________________________________________________-
    # addition for true extension module building

    def wrap_exported_class(self, cls):
        metaclass = "type"
        name = self.uniquename('gwcls_' + cls.__name__)
        basenames = [self.nameof(base) for base in cls.__bases__]
        def initclassobj():
            content = cls.__dict__.items()
            content.sort()
            for key, value in content:
                if key.startswith('__'):
                    if key in ['__module__', '__doc__', '__dict__',
                               '__weakref__', '__repr__', '__metaclass__']:
                        continue
                if self.shouldskipfunc(value):
                    log.WARNING("skipped class function: %r" % value)
                    continue
#                yield '%s.%s = property(lambda self:%s.__get__(self.__self__))' % (
#                    name, key, self.nameof(value))
                yield '%s.%s = %s' % (name, key, self.nameof(value))

        baseargs = ", ".join(basenames)
        if baseargs:
            baseargs = '(%s)' % baseargs
            
        a = self.initcode.append
        a('class %s%s:'                     % (name, baseargs) )
        a('    __metaclass__ = type')
        a('    __slots__ = ["__self__"] # for PyCObject')
        self.later(initclassobj())
        return name
