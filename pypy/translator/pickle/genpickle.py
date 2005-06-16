"""
Generate a Python source file from the flowmodel.
The purpose is to create something that allows
to restart code generation after flowing and maybe
annotation.

The generated source appeared to be way too large
for the CPython compiler. Therefore, we cut the
source into pieces and compile them seperately.
"""
from __future__ import generators, division, nested_scopes
import __future__
all_feature_names = __future__.all_feature_names
import os, sys, new, __builtin__

from pypy.translator.gensupp import uniquemodulename, NameManager
from pypy.translator.gensupp import builtin_base
from pypy.rpython.rarithmetic import r_int, r_uint
from pypy.objspace.flow.model import Variable, Constant, SpaceOperation
from pypy.objspace.flow.model import FunctionGraph, Block, Link
from pypy.objspace.flow.flowcontext import SpamBlock, EggBlock
from pypy.annotation.model import SomeInteger, SomeObject, SomeChar, SomeBool
from pypy.annotation.model import SomeList, SomeString, SomeTuple
from pypy.annotation.unaryop import SomeInstance
from pypy.interpreter.baseobjspace import ObjSpace
from pypy.translator.pickle import slotted

from pickle import whichmodule, PicklingError
from copy_reg import _reconstructor

import pickle

from types import *
import types

class AlreadyCreated(Exception): pass

# ____________________________________________________________


class GenPickle:

    def __init__(self, translator, writer = None):
        self.translator = translator
        self.writer = writer
        self.initcode = []
        self.produce = self._produce()
        self.produce(
            'from __future__ import %s\n' % ', '.join(all_feature_names) +
            'import new, types, sys',
            )
        self.picklenames = {}  # memoize objects
        self.memoize(float("1e10000000000000000000000000000000"),
                     'float("1e10000000000000000000000000000000")')
        for name in all_feature_names + "new types sys".split():
            self.memoize(globals()[name], name)
        self.namespace = NameManager()
        self.uniquename = self.namespace.uniquename
        self.namespace.make_reserved_names('None False True')
        self.namespace.make_reserved_names('new types sys')
        self.namespace.make_reserved_names(' '.join(all_feature_names))
        self.namespace.make_reserved_names('result') # result dict
        self.result = {}
        self.simple_const_types = {
            int: repr,
            long: repr,
            float: repr,
            str: repr,
            unicode: repr,
            type(None): repr,
            bool: repr,
            }
        self.typecache = {} # hold types vs. nameof methods
        # we distinguish between the "user program" and other stuff.
        # "user program" will never use save_global.
        self.domains = (
            'pypy.objspace.std.',
            'pypy.objspace.descroperation',
            'pypy._cache.',
            'pypy.interpreter.',
            'pypy.module.',
            '__main__',
            )
        self.shortnames = {
            Variable:       'V',
            Constant:       'C',
            Block:          'B',
            SpamBlock:      'SB',
            EggBlock:       'EB',
            Link:           'L',
            FunctionGraph:  'FG',
            SomeInteger:    'sI',
            SomeObject:     'sO',
            SomeChar:       'sC',
            SomeBool:       'sB',
            SomeList:       'sL',
            SomeString:     'sS',
            SomeTuple:      'sT',
            SomeInstance:   'sIn',
            }
        self.inline_instances = {
            SpaceOperation: True,
            }

    def pickle(self, **kwds):
        for obj in kwds.values():
            self.nameof(obj)
        self.result.update(kwds)

    def finish(self):
        self.nameof(self.result)
        self.pickle()
        self.produce('result = %s' % self.nameof(self.result))
        if self.writer:
            self.writer.close()

    def memoize(self, obj, name):
        self.picklenames[id(obj)] = name
        return name

    def memoize_unique(self, obj, basename):
        if id(obj) in self.picklenames:
            raise AlreadyCreated
        return self.memoize(obj, self.uniquename(basename))

    def _produce(self):
        writer = self.writer
        down = 1234
        cnt = [0, 0]  # text, calls
        self.last_progress = ''
        if writer:
            write = writer.write
        else:
            write = self.initcode.append
        def produce(text):
            write(text+'\n')
            cnt[0] += len(text) + 1
            cnt[1] += 1
            if cnt[1] == down:
                cnt[1] = 0
                self.progress("%d" % cnt[0])
        return produce

    def progress(self, txt):
        back = '\x08' * len(self.last_progress)
        self.last_progress = txt+' ' # soft space
        print back+txt,

    def spill(self):
        self.progress_count += len(self.initcode)
        writer = self.writer
        if writer:
            for line in self.initcode:
                writer.write(line+'\n')
            del self.initcode[:]
        if self.progress_count - self.progress_last >= 1234:
            print '%s%d' % (20*'\x08', self.progress_count),
            self.progress_last = self.progress_count

    def nameof(self, obj):
        try:
            try:
                return self.picklenames[id(obj)]
            except KeyError:
                typ = type(obj)
                return self.simple_const_types[typ](obj)
        except KeyError:
            try:
                try:
                    meth = self.typecache[typ]
                except KeyError:
                    obj_builtin_base = builtin_base(obj)
                    if (obj_builtin_base in (object,) + tuple(
                        self.simple_const_types.keys()) and
                        typ is not obj_builtin_base):
                        # assume it's a user defined thingy
                        meth = self.nameof_instance
                    else:
                        for cls in typ.__mro__:
                            meth = getattr(self, 'nameof_' + ''.join(
                                [ c for c in cls.__name__
                                  if c.isalpha() or c == '_'] ), None)
                            if meth:
                                break
                        else:
                            raise Exception, "nameof(%r)" % (obj,)
                    self.typecache[typ] = meth
                name = meth(obj)
            except AlreadyCreated:
                name = self.picklenames[id(obj)]
            return name

    def nameofargs(self, tup, plain_tuple = False):
        """ a string with the nameofs, concatenated """
        # see if we can build a compact representation
        ret = ', '.join([self.nameof(arg) for arg in tup])
        if plain_tuple and len(tup) == 1:
            ret += ','
        if len(ret) <= 90:
            return ret
        ret = '\n ' + ',\n '.join(
            [self.nameof(arg) for arg in tup]) + ',\n '
        return ret

    def nameof_object(self, value):
        if type(value) is not object:
            raise Exception, "nameof(%r): type %s not object" % (
                value, type(value).__name__)
        name = self.memoize_unique(value, 'g_object')
        self.produce('%s = object()' % name)
        return name

    def nameof_module(self, value):
        # all allowed here, we reproduce ourselves
        if self.is_app_domain(value.__name__):
            name = self.memoize_unique(value, 'gmod_%s' % value.__name__)
            self.produce('%s = new.module(%r)\n'
                         'sys.modules[%r] = %s'% (
                name, value.__name__, value.__name__, name) )
            def initmodule():
                names = value.__dict__.keys()
                names.sort()
                for k in names:
                    try:
                        v = value.__dict__[k]
                        nv = self.nameof(v)
                        yield '%s.%s = %s' % (name, k, nv)
                    except PicklingError:
                        pass
            for line in initmodule():
                self.produce(line)
        else:
            name = self.memoize_unique(value, value.__name__)
            self.produce('%s = __import__(%r)' % (name, value.__name__,))
        return name

    def skipped_function(self, func, reason=None, _dummydict={}):
        # Generates a placeholder for missing functions
        # that raises an exception when called.
        # The original code object is retained in an
        # attribute '_skipped_code'
        skipname = 'gskippedfunc_' + func.__name__
        funcname = func.__name__
        # need to handle this specially
        if id(func) in self.picklenames:
            raise AlreadyCreated
        # generate code object before the skipped func (reads better)
        func_code = getattr(func, 'func_code', None) # maybe builtin
        self.nameof(func_code)
        if reason:
            text = 'skipped: %r, see _skipped_code attr: %s' % (
                reason, funcname)
        else:
            text = 'skipped, see _skipped_code attr: %s' % funcname
        def dummy(*args, **kwds):
            raise NotImplementedError, text
        skippedfunc = new.function(dummy.func_code, _dummydict, skipname, (),
                                   dummy.func_closure)
        skippedfunc._skipped_code = func_code
        name = self.nameof(skippedfunc)
        return self.memoize(func, name)

    def nameof_staticmethod(self, sm):
        # XXX XXX XXXX
        func = sm.__get__(42.5)
        functionname = self.nameof(func)
        name = self.memoize_unique(sm, 'gsm_' + func.__name__)
        self.produce('%s = staticmethod(%s)' % (name, functionname))
        return name

    def nameof_instancemethod(self, meth):
        func = self.nameof(meth.im_func)
        typ = self.nameof(meth.im_class)
        if meth.im_self is None:
            # no error checking here
            name = self.memoize_unique(meth, 'gmeth_' + func)
            self.produce('%s = %s.%s' % (name, typ, meth.__name__))
        else:
            ob = self.nameof(meth.im_self)
            name = self.memoize_unique(meth, 'gumeth_'+ func)
            self.produce('%s = new.instancemethod(%s, %s, %s)' % (
                name, func, ob, typ))
        return name

    def should_translate_attr(self, pbc, attr):
        ann = self.translator.annotator
        if ann:
            classdef = ann.getuserclasses().get(pbc.__class__)
        else:
            classdef = None
        ignore = getattr(pbc.__class__, 'NOT_RPYTHON_ATTRIBUTES', [])
        if attr in ignore:
            return False
        if classdef:
            return classdef.about_attribute(attr) is not None
        # by default, render if we don't know anything
        return True

    def nameof_builtin_function_or_method(self, func):
        if func.__self__ is None:
            # builtin function
            # where does it come from? Python2.2 doesn't have func.__module__
            for modname, module in sys.modules.items():
                # here we don't ignore extension modules, but it must be
                # a builtin module
                if not module: continue
                if hasattr(module, '__file__'):
                    fname = module.__file__.lower()
                    pyendings = '.py', '.pyc', '.pyo'
                    if [fname.endswith(ending) for ending in pyendings]:
                        continue
                if func is getattr(module, func.__name__, None):
                    break
            else:
                #raise Exception, '%r not found in any built-in module' % (func,)
                return self.skipped_function(
                    func, 'not found in any built-in module')
            name = self.memoize_unique(func, 'gbltin_' + func.__name__)
            if modname == '__builtin__':
                self.produce('%s = %s' % (name, func.__name__))
            else:
                modname = self.nameof(module)
                self.produce('%s = %s.%s' % (name, modname, func.__name__))
        else:
            # builtin (bound) method
            selfname = self.nameof(func.__self__)
            name = self.memoize_unique(func, 'gbltinmethod_' + func.__name__)
            self.produce('%s = %s.%s' % (name, selfname, func.__name__))
        return name

    def nameof_classobj(self, cls):
        if cls.__doc__ and cls.__doc__.lstrip().startswith('NOT_RPYTHON'):
            raise PicklingError, "%r should never be reached" % (cls,)

        try:
            return self.save_global(cls)
        except PicklingError, e:
            pass
        
        metaclass = "type"
        if issubclass(cls, Exception):
            # if cls.__module__ == 'exceptions':
            # don't rely on this, py.magic redefines AssertionError
            if getattr(__builtin__, cls.__name__, None) is cls:
                name = self.memoize_unique(cls, 'gexc_' + cls.__name__)
                self.produce('%s = %s' % (name, cls.__name__))
                return name
        if not isinstance(cls, type):
            assert type(cls) is ClassType
            metaclass = "types.ClassType"

        basenames = [self.nameof(base) for base in cls.__bases__]
        def initclassobj():
            content = cls.__dict__.items()
            content.sort()
            ignore = getattr(cls, 'NOT_RPYTHON_ATTRIBUTES', [])
            isapp = self.is_app_domain(cls.__module__)
            for key, value in content:
                if key.startswith('__'):
                    if key in ['__module__', '__doc__', '__dict__', '__slots__',
                               '__weakref__', '__repr__', '__metaclass__']:
                        continue
                    # XXX some __NAMES__ are important... nicer solution sought
                    #raise Exception, "unexpected name %r in class %s"%(key, cls)
                if isapp:
                    if (isinstance(value, staticmethod) and value.__get__(1) not in
                        self.translator.flowgraphs and self.translator.frozen):
                        continue
                    if isinstance(value, classmethod):
                        doc = value.__get__(cls).__doc__
                        if doc and doc.lstrip().startswith("NOT_RPYTHON"):
                            continue
                    if (isinstance(value, FunctionType) and value not in
                        self.translator.flowgraphs and self.translator.frozen):
                        continue
                if key in ignore:
                    continue
                if type(value) in self.descriptor_filter:
                    continue # this gets computed

                yield '%s.%s = %s' % (name, key, self.nameof(value))

        baseargs = ", ".join(basenames)
        if baseargs:
            baseargs = '(%s)' % baseargs
        name = self.memoize_unique(cls, 'gcls_' + cls.__name__)
        ini = 'class %s%s:\n  __metaclass__ = %s' % (name, baseargs, metaclass)
        if '__slots__' in cls.__dict__:
            ini += '\n  __slots__ = %r' % cls.__slots__
        self.produce(ini)
        self.produce('%s.__name__ = %r' % (name, cls.__name__))
        self.produce('%s.__module__ = %r' % (name, cls.__module__))
        # squeeze it out, early # self.later(initclassobj())
        for line in initclassobj():
            self.produce(line)
        return name

    nameof_class = nameof_classobj   # for Python 2.2

    typename_mapping = {
        InstanceType: 'types.InstanceType',
        type(None):   'type(None)',
        CodeType:     'types.CodeType',
        type(sys):    'type(new)',

        r_int:        'r_int',
        r_uint:       'r_uint',

        # XXX more hacks
        # type 'builtin_function_or_method':
        type(len): 'type(len)',
        # type 'method_descriptor':
        type(type.__reduce__): 'type(type.__reduce__)',
        # type 'wrapper_descriptor':
        type(type(None).__repr__): 'type(type(None).__repr__)',
        # type 'getset_descriptor':
        type(type.__dict__['__dict__']): "type(type.__dict__['__dict__'])",
        # type 'member_descriptor':
        type(type.__dict__['__basicsize__']): "type(type.__dict__['__basicsize__'])",
        # type 'instancemethod':
        type(Exception().__init__): 'type(Exception().__init__)',
        # type 'listiterator':
        type(iter([])): 'type(iter([]))',
        }
    descriptor_filter = {}
    for _key in typename_mapping.keys():
        if _key.__name__.endswith('descriptor'):
            descriptor_filter[_key] = True
    del _key
    
    def nameof_type(self, cls):
        if cls.__module__ != '__builtin__':
            return self.nameof_classobj(cls)   # user-defined type
        name = self.memoize_unique(cls, 'gtype_%s' % cls.__name__)
        if getattr(__builtin__, cls.__name__, None) is cls:
            expr = cls.__name__    # type available from __builtin__
        elif cls in types.__dict__.values():
            for key, value in types.__dict__.items():
                if value is cls:
                    break
            self.produce('from types import %s as %s' % (
                key, name))
            return name
        else:
            expr = self.typename_mapping[cls]
        self.produce('%s = %s' % (name, expr))
        return name

    def nameof_tuple(self, tup):
        chunk = 20
        # first create all arguments
        for i in range(0, len(tup), chunk):
            self.nameofargs(tup[i:i+chunk], True)
        # see if someone else created us meanwhile
        name = self.memoize_unique(tup, 'T%d' % len(tup))
        argstr = self.nameofargs(tup[:chunk], True)
        self.produce('%s = (%s)' % (name, argstr))
        for i in range(chunk, len(tup), chunk):
            argstr = self.nameofargs(tup[i:i+chunk], True)
            self.produce('%s += (%s)' % (name, argstr) )
        return name

    def nameof_list(self, lis):
        chunk = 20
        def initlist():
            for i in range(0, len(lis), chunk):
                argstr = self.nameofargs(lis[i:i+chunk])
                yield '%s += [%s]' % (name, argstr)
        name = self.memoize_unique(lis, 'L%d' % len(lis))
        self.produce('%s = []' % name)
        for line in initlist():
            self.produce(line)
        return name

    def is_app_domain(self, modname):
        for domain in self.domains:
            if domain.endswith('.') and modname.startswith(domain):
                # handle subpaths
                return True
            if modname == domain:
                # handle exact module names
                return True
        return False

    def nameof_dict(self, dic):
        if '__name__' in dic:
            module = dic['__name__']
            try:
                if type(module) is str and self.is_app_domain(module):
                    raise ImportError
                __import__(module)
                mod = sys.modules[module]
            except (ImportError, KeyError, TypeError):
                pass
            else:
                if dic is mod.__dict__ and not self.is_app_domain(module):
                    dictname = module.split('.')[-1] + '__dict__'
                    dictname = self.memoize_unique(dic, dictname)
                    self.produce('from %s import __dict__ as %s' % (
                                 module, dictname) )
                    return dictname
        def initdict():
            keys = dic.keys()
            keys.sort()
            for k in keys:
                try:
                    nk, nv = self.nameof(k), self.nameof(dic[k])
                    yield '%s[%s] = %s' % (name, nk, nv)
                except PicklingError:
                    pass
        name = self.memoize_unique(dic, 'D%d' % len(dic))
        self.produce('%s = {}' % name)
        for line in initdict():
            self.produce(line)
        return name

    # strange prebuilt instances below, don't look too closely
    # XXX oh well.
    def nameof_member_descriptor(self, md):
        cls = self.nameof(md.__objclass__)
        name = self.memoize_unique(md, 'gdescriptor_%s_%s' % (
            md.__objclass__.__name__, md.__name__))
        self.produce('%s = %s.__dict__[%r]' % (name, cls, md.__name__))
        return name
    nameof_getset_descriptor  = nameof_member_descriptor
    nameof_method_descriptor  = nameof_member_descriptor
    nameof_wrapper_descriptor = nameof_member_descriptor

    def nameof_instance(self, instance):
        def initinstance():
            if hasattr(instance, '__setstate__'):
                # the instance knows what to do
                args = self.nameof(restorestate)
                yield '%s.__setstate__(%s)' % (name, args)
                return
            elif type(restorestate) is tuple:
                setstate = self.nameof(_set)
                argstr = self.nameofargs(restorestate)
                yield '%s(%s, %s)' % (setstate, name, argstr)
                return
            assert type(restorestate) is dict, (
                "%s has no dict and no __setstate__" % name)
            content = restorestate.items()
            content.sort()
            attrs = []
            for key, value in content:
                if self.should_translate_attr(instance, key):
                    if hasattr(value, '__doc__'):
                        doc = value.__doc__
                        if type(doc) is str and doc.lstrip().startswith('NOT_RPYTHON'):
                            continue
                    attrs.append( (key, self.nameof(value)) )
            for k, v in attrs:
                yield '%s.%s = %s' % (name, k, v)

        klass = instance.__class__
        cls = self.nameof(klass)
        if hasattr(klass, '__base__'):
            base_class = builtin_base(instance)
            base = self.nameof(base_class)
        else:
            base_class = None
            base = cls
        if klass in self.inline_instances:
            immediate = True
        else:
            if klass in self.shortnames:
                name = self.memoize_unique(instance, self.shortnames[klass])
            else:
                name = self.memoize_unique(instance, 'ginst_' + klass.__name__)
            immediate = False
        if hasattr(instance, '__reduce_ex__'):
            try:
                reduced = instance.__reduce_ex__()
            except TypeError:
                # oops! slots and no __getstate__?
                if not (hasattr(instance, '__slots__')
                        and not hasattr(instance, '__getstate__') ):
                    print "PROBLEM:", instance
                    raise
                assert not hasattr(instance, '__dict__'), ('wrong assumptions'
                    ' about __slots__ in %s instance without __setstate__,'
                    ' please update %s' % (cls.__name__, __name__) )
                restorestate = _get(instance)
                restorer = _rec
                restoreargs = klass,
            else:
                restorer = reduced[0]
                restoreargs = reduced[1]
                if restorer is _reconstructor:
                    restorer = _rec
                    if restoreargs[1:] == (object, None):
                        restoreargs = restoreargs[:1]
                if len(reduced) > 2:
                    restorestate = reduced[2]
                else:
                    restorestate = None
            restorename = self.nameof(restorer)
            # ignore possible dict, handled later by initinstance filtering
            # in other cases, we expect that the class knows what to pickle.
        else:
            restoreargs = (base, cls)
            restorename = '%s.__new__' % base
            if hasattr(instance, '__getstate__'):
                restorestate = instance.__getstate__()
            else:
                restorestate = instance.__dict__
        restoreargstr = self.nameofargs(restoreargs)
        if immediate:
            assert restorestate is None
            return '%s(%s)' % (restorename, restoreargstr)
        if isinstance(klass, type):
            self.produce('%s = %s(%s)' % (name, restorename, restoreargstr))
        else:
            self.produce('%s = new.instance(%s)' % (name, cls))
        if restorestate is not None:
            for line in initinstance():
                self.produce(line)
        return name

    def save_global(self, obj):
        # this is almost similar to pickle.py
        name = obj.__name__
        module = getattr(obj, "__module__", None)
        if module is None:
            module = whichmodule(obj, name)
        if self.is_app_domain(module):
            # not allowed to import this
            raise PicklingError('%s belongs to the user program' %
                                name)
        try:
            __import__(module)
            mod = sys.modules[module]
            klass = getattr(mod, name)
        except (ImportError, KeyError, AttributeError):
            raise PicklingError(
                "Can't pickle %r: it's not found as %s.%s" %
                (obj, module, name))
        else:
            if klass is not obj:
                raise PicklingError(
                    "Can't pickle %r: it's not the same object as %s.%s" %
                    (obj, module, name))
        # from here we do our own stuff
        restorename = self.memoize_unique(obj, obj.__name__)
        if restorename != obj.__name__:
            self.produce('from %s import %s as %s' % (
                         module, obj.__name__, restorename) )
        else:
            self.produce('from %s import %s' % (
                         module, obj.__name__) )
        return restorename

    def nameof_function(self, func):
        # look for skipped functions
        if self.translator.frozen:
            if func not in self.translator.flowgraphs:
                # see if this is in translator's domain
                module = whichmodule(func, func.__name__)
                if self.is_app_domain(module):
                    # see if this buddy has been skipped in another save, before
                    if not hasattr(func, '_skipped_code'):
                        return self.skipped_function(func,
                            'not found in translator\'s flowgraphs')
        else:
            if (func.func_doc and
                func.func_doc.lstrip().startswith('NOT_RPYTHON')):
                return self.skipped_function(func, 'tagged as NOT_RPYTHON')
        try:
            return self.save_global(func)
        except PicklingError:
            pass
        args = (func.func_code, func.func_globals, func.func_name,
                func.func_defaults, func.func_closure)
        argstr = self.nameofargs(args)
        if hasattr(func, '_skipped_code'):
            name = self.memoize_unique(func, func.__name__)
        else:
            name = self.memoize_unique(func, 'gfunc_' + func.__name__)
        self.produce('%s = new.function(%s)' % (name, argstr) )
        if func.__dict__:
            def initfunction():
                items = func.__dict__.items()
                items.sort()
                for k, v in items:
                    try:
                        yield '%s.%s = %s' % (name, k, self.nameof(v))
                    except PicklingError:
                        pass
            for line in initfunction():
                self.produce(line)
        return name

    def nameof_cell(self, cel):
        # no need to name cells. Their contents is what is shared.
        obj = break_cell(cel)
        return '%s(%s)' % (self.nameof(make_cell), self.nameof(obj))

    def nameof_property(self, prop):
        argstr = self.nameofargs((prop.fget, prop.fset, prop.fdel,
                                  prop.__doc__))
        name = self.memoize_unique(prop, 'gprop_')
        self.produce('%s = property(%s)' % (name, argstr) )
        return name

    def nameof_code(self, code):
        args = (code.co_argcount, code.co_nlocals, code.co_stacksize,
                code.co_flags, code.co_code, code.co_consts, code.co_names,
                code.co_varnames, code.co_filename, code.co_name,
                code.co_firstlineno, code.co_lnotab, code.co_freevars,
                code.co_cellvars)
        argstr = self.nameofargs(args)
        name = self.memoize_unique(code, 'gcode_' + code.co_name)
        self.produce('%s = new.code(%s)' % (name, argstr))
        return name

    def nameof_file(self, fil):
        if fil is sys.stdin:  return "sys.stdin"
        if fil is sys.stdout: return "sys.stdout"
        if fil is sys.stderr: return "sys.stderr"
        raise Exception, 'Cannot translate an already-open file: %r' % (fil,)

    def nameof_methodwrapper(self, wp):
        # this object should be enhanced in CPython!
        msg = '%r: method %s of unknown object cannot be reconstructed' % (
            wp, wp.__name__)
        return self.skipped_function(wp, msg)


def make_cell(obj):
    def func():
        return obj
    return func.func_closure[0]

def break_cell(cel):
    obj = None
    def func():
        return obj
    args = (func.func_code, func.func_globals, func.func_name,
            func.func_defaults, (cel,))
    func = new.function(*args)
    return func()

# some shortcuts, to make the pickle smaller

def _rec(klass, base=object, state=None):
    return _reconstructor(klass, base, state)

def _get(obj):
    return slotted.__getstate__(obj)

def _set(obj, *args):
    slotted.__setstate__(obj, args)

__all__ = ['GenPickle']
