"""
Generate a Python source file from the flowmodel.
The purpose is to create something that allows
to restart code generation after flowing and maybe
annotation.
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
from pypy.interpreter.baseobjspace import ObjSpace
from pypy.translator.pickle import slotted

from pickle import whichmodule, PicklingError
from copy_reg import _reduce_ex, _reconstructor

import pickle

from types import *
import types

# ____________________________________________________________


class GenPickle:

    def __init__(self, translator, outfile = None):
        self.translator = translator
        self.initcode = [
            'from __future__ import %s\n' % ', '.join(all_feature_names) +
            'import new, types, sys',
            ]

        self.latercode = []    # list of generators generating extra lines
        self.debugstack = ()   # linked list of nested nameof()

        self.picklenames = {Constant(None):  'None',
                            Constant(False): 'False',
                            Constant(True):  'True',
                            # hack: overflowed float
                            Constant(float("1e10000000000000000000000000000000")):
                                'float("1e10000000000000000000000000000000")',
                            }
        for name in all_feature_names + "new types sys".split():
            self.picklenames[Constant(globals()[name])] = name
        self.namespace = NameManager()
        self.namespace.make_reserved_names('None False True')
        self.namespace.make_reserved_names('new types sys')
        self.namespace.make_reserved_names(' '.join(all_feature_names))
        self.inline_consts = True # save lots of space
        self._nesting = 0 # for formatting nested tuples etc.
        # we distinguish between the "user program" and other stuff.
        # "user program" will never use save_global.
        self.domains = (
            'pypy.objspace.std.',
            'pypy._cache.',
            'pypy.interpreter.',
            'pypy.module.',
            '__main__',
            )
        self.shortnames = {
            SpaceOperation: 'S',
            Variable:       'V',
            Constant:       'C',
            Block:          'B',
            SpamBlock:      'SB',
            EggBlock:       'EB',
            Link:           'L',
            FunctionGraph:  'F',
            SomeInteger:    'SI',
            SomeObject:     'SO',
            SomeChar:       'SC',
            SomeBool:       'SB',
            SomeList:       'SL',
            SomeString:     'SS',
            SomeTuple:      'ST',
            }
        self.outfile = outfile
        self._partition = 1234

    def nameof(self, obj, debug=None, namehint=None):
        key = Constant(obj)
        try:
            return self.picklenames[key]
        except KeyError:
            if debug:
                stackentry = debug, obj
            else:
                stackentry = obj
            self.debugstack = (self.debugstack, stackentry)
            obj_builtin_base = builtin_base(obj)
            if obj_builtin_base in (object, int, long) and type(obj) is not obj_builtin_base:
                # assume it's a user defined thingy
                name = self.nameof_instance(obj)
            else:
                for cls in type(obj).__mro__:
                    meth = getattr(self,
                                   'nameof_' + ''.join( [
                                       c for c in cls.__name__
                                       if c.isalpha() or c == '_'] ),
                                   None)
                    if meth:
                        break
                else:
                    raise Exception, "nameof(%r)" % (obj,)

                code = meth.im_func.func_code
                if namehint and 'namehint' in code.co_varnames[:code.co_argcount]:
                    name = meth(obj, namehint=namehint)
                else:
                    name = meth(obj)
            self.debugstack, x = self.debugstack
            assert x is stackentry
            if name[0].isalpha():
                # avoid to store things which are used just once
                self.picklenames[key] = name
            return name

    def nameofargs(self, tup):
        """ a string with the nameofs, concatenated """
        if len(tup) < 5:
            # see if there is nesting to be expected
            for each in tup:
                if type(each) is tuple:
                    break
            else:
                return ', '.join([self.nameof(arg) for arg in tup])
        # we always wrap into multi-lines, this is simple and readable
        self._nesting += 1
        space = '  ' * self._nesting
        ret = '\n' + space + (',\n' + space).join(
            [self.nameof(arg) for arg in tup]) + ',\n' + space
        self._nesting -= 1
        return ret

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

    def nameof_module(self, value):
        # all allowed here, we reproduce ourselves
        if self.is_app_domain(value.__name__):
            name = self.uniquename('gmod_%s' % value.__name__)
            self.initcode.append('%s = new.module(%r)\n'
                                 'sys.modules[%r] = %s'% (
                name, value.__name__, value.__name__, name) )
            def initmodule():
                for k, v in value.__dict__.items():
                    try:
                        nv = self.nameof(v)
                        yield '%s.%s = %s' % (name, k, nv)
                    except PicklingError:
                        pass
            self.later(initmodule())
        else:
            name = self.uniquename(value.__name__)
            self.initcode_python(name, "__import__(%r)" % (value.__name__,))
        return name

    def nameof_int(self, value):
        return repr(value)

    # we don't need to name the following const types.
    # the compiler folds the consts the same way as we do.
    # note that true pickling is more exact, here.
    nameof_long = nameof_float = nameof_bool = nameof_NoneType = nameof_int

    def nameof_str(self, value):
        if self.inline_consts:
            return repr(value)
        name = self.uniquename('gstr_' + value[:32])
        self.initcode_python(name, repr(value))
        return name

    def nameof_unicode(self, value):
        if self.inline_consts:
            return repr(value)
        name = self.uniquename('guni_' + str(value[:32]))
        self.initcode_python(name, repr(value))
        return name

    def skipped_function(self, func):
        # debugging only!  Generates a placeholder for missing functions
        # that raises an exception when called.
        name = self.uniquename('gskippedfunc_' + func.__name__)
        self.initcode.append('def %s(*a,**k):\n' 
                             '  raise NotImplementedError' % name)
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

    # new version: save if we don't know
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
                # here we don't ignore extension modules
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
        if cls.__doc__ and cls.__doc__.lstrip().startswith('NOT_RPYTHON'):
            raise PicklingError, "%r should never be reached" % (cls,)

        try:
            return self.save_global(cls)
        except PicklingError:
            pass
        
        metaclass = "type"
        if issubclass(cls, Exception):
            # if cls.__module__ == 'exceptions':
            # don't rely on this, py.magic redefines AssertionError
            if getattr(__builtin__,cls.__name__,None) is cls:
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
                        print value
                        continue
                    if isinstance(value, classmethod):
                        doc = value.__get__(cls).__doc__
                        if doc and doc.lstrip().startswith("NOT_RPYTHON"):
                            continue
                    if (isinstance(value, FunctionType) and value not in
                        self.translator.flowgraphs and self.translator.frozen):
                        print value
                        continue
                if key in ignore:
                    continue
                if type(value) in self.descriptor_filter:
                    continue # this gets computed

                yield '%s.%s = %s' % (name, key, self.nameof(value))

        baseargs = ", ".join(basenames)
        if baseargs:
            baseargs = '(%s)' % baseargs
        ini = 'class %s%s:\n  __metaclass__ = %s' % (name, baseargs, metaclass)
        if '__slots__' in cls.__dict__:
            ini += '\n  __slots__ = %r' % cls.__slots__
        self.initcode.append(ini)
        self.initcode.append('%s.name = %r' % (name, cls.__name__))
        # squeeze it out, now# self.later(initclassobj())
        self.picklenames[Constant(cls)] = name
        for line in initclassobj():
            self.initcode.append(line)
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
        }
    descriptor_filter = {}
    for _key in typename_mapping.keys():
        if _key.__name__.endswith('descriptor'):
            descriptor_filter[_key] = True
    del _key
    
    def nameof_type(self, cls):
        if cls.__module__ != '__builtin__':
            return self.nameof_classobj(cls)   # user-defined type
        name = self.uniquename('gtype_%s' % cls.__name__)
        if getattr(__builtin__, cls.__name__, None) is cls:
            expr = cls.__name__    # type available from __builtin__
        elif cls in types.__dict__.values():
            for key, value in types.__dict__.items():
                if value is cls:
                    break
            self.initcode.append('from types import %s as %s' % (
                key, name))
            return name
        else:
            expr = self.typename_mapping[cls]
        self.initcode_python(name, expr)
        return name

    def nameof_tuple(self, tup):
        # instead of defining myriads of tuples, it seems to
        # be cheaper to create them inline, although they don't
        # get constant folded like strings and numbers.
        if self.inline_consts:
            argstr = self.nameofargs(tup)
            if len(tup) == 1 and not argstr.rstrip().endswith(','):
                argstr += ','
            return '(%s)' % argstr
        name = self.uniquename('g%dtuple' % len(tup))
        args = [self.nameof(x) for x in tup]
        args = ', '.join(args)
        if args:
            args += ','
        self.initcode_python(name, '(%s)' % args)
        return name

    def nameof_list(self, lis):
        name = self.uniquename('L%d' % len(lis))
        extend = self.nameof(_ex)
        def initlist():
            chunk = 20
            for i in range(0, len(lis), chunk):
                items = lis[i:i+chunk]
                itemstr = self.nameofargs(items)
                yield '%s(%s, %s)' % (extend, name, itemstr)
        self.initcode_python(name, '[]')
        self.later(initlist())
        return name

    def is_app_domain(self, modname):
        for domain in self.domains:
            if modname.startswith(domain):
                return True
        return False

    def nameof_dict(self, dic):
        if '__name__' in dic:
            module = dic['__name__']
            try:
                __import__(module)
                mod = sys.modules[module]
            except (ImportError, KeyError, TypeError):
                pass
            else:
                if dic is mod.__dict__ and not self.is_app_domain(module):
                    dictname = module.split('.')[-1] + '__dict__'
                    dictname = self.uniquename(dictname)
                    self.initcode.append('from %s import __dict__ as %s' % (
                            module, dictname) )
                    self.picklenames[Constant(dic)] = dictname
                    return dictname
        name = self.uniquename('D%d' % len(dic))
        def initdict():
            for k in dic:
                try:
                    if type(k) is str:
                        yield '%s[%r] = %s' % (name, k, self.nameof(dic[k]))
                    else:
                        yield '%s[%s] = %s' % (name, self.nameof(k),
                                               self.nameof(dic[k]))
                except PicklingError:
                    pass
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

    def nameof_instance(self, instance):
        klass = instance.__class__
        if klass in self.shortnames:
            name = self.uniquename(self.shortnames[klass])
        else:
            name = self.uniquename('ginst_' + klass.__name__)
        cls = self.nameof(klass)
        if hasattr(klass, '__base__'):
            base_class = builtin_base(instance)
            base = self.nameof(base_class)
        else:
            base_class = None
            base = cls
        def initinstance():
            if hasattr(instance, '__setstate__'):
                # the instance knows what to do
                args = self.nameof(restorestate)
                yield '%s.__setstate__(%s)' % (name, args)
                return
            elif type(restorestate) is tuple:
                setstate = self.nameof(slotted.__setstate__)
                args = self.nameof(restorestate)
                yield '%s(%s, %s)' % (setstate, name, args)
                return
            assert type(restorestate) is dict, (
                "%s has no dict and no __setstate__" % name)
            content = restorestate.items()
            content.sort()
            for key, value in content:
                if self.should_translate_attr(instance, key):
                    if hasattr(value, '__doc__'):
                        doc = value.__doc__
                        if type(doc) is str and doc.lstrip().startswith('NOT_RPYTHON'):
                            continue
                    line = '%s.%s = %s' % (name, key, self.nameof(value))
                    yield line
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
                restorestate = slotted.__getstate__(instance)
                restorer = _rec
                restoreargs = klass, object, None
            else:
                restorer = reduced[0]
                if restorer is _reconstructor:
                    restorer = _rec
                restoreargs = reduced[1]
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
        if isinstance(klass, type):
            self.initcode.append('%s = %s(%s)' % (name, restorename,
                                                   restoreargstr))
        else:
            self.initcode.append('%s = new.instance(%s)' % (name, cls))
        if restorestate is not None:
            self.later(initinstance())
        return name

    def save_global(self, obj):
        # this is almost similar to pickle.py
        name = obj.__name__
        key = Constant(obj)
        if key not in self.picklenames:
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
            restorename = self.uniquename(obj.__name__)
            if restorename != obj.__name__:
                self.initcode.append('from %s import %s as %s' % (
                    module, obj.__name__, restorename) )
            else:
                self.initcode.append('from %s import %s' % (
                    module, obj.__name__) )
            self.picklenames[key] = restorename
        return self.picklenames[key]

    def nameof_function(self, func):
        # look for skipped functions
        if self.translator.frozen:
            if func not in self.translator.flowgraphs:
                # see if this is in translator's domain
                module = whichmodule(func, func.__name__)
                if self.is_app_domain(module):
                    return self.skipped_function(func)
        else:
            if (func.func_doc and
                func.func_doc.lstrip().startswith('NOT_RPYTHON')):
                return self.skipped_function(func)
        try:
            return self.save_global(func)
        except PicklingError:
            pass
        args = (func.func_code, func.func_globals, func.func_name,
                func.func_defaults, func.func_closure)
        pyfuncobj = self.uniquename('gfunc_' + func.__name__)
        # touch code,to avoid extra indentation
        self.nameof(func.func_code)
        self.initcode.append('%s = new.function(%s)' % (pyfuncobj,
                             self.nameofargs(args)) )
        if func.__dict__:
            for k, v in func.__dict__.items():
                try:
                    self.initcode.append('%s.%s = %s' % (
                        pyfuncobj, k, self.nameof(v)) )
                except PicklingError:
                    pass
        return pyfuncobj

    def nameof_cell(self, cel):
        obj = break_cell(cel)
        pycell = self.uniquename('gcell_' + self.nameof(obj))
        self.initcode.append('%s = %s(%s)' % (pycell, self.nameof(make_cell),
                                              self.nameof(obj)) )
        return pycell

    def nameof_property(self, prop):
        pyprop = self.uniquename('gprop_')
        self.initcode.append('%s = property(%s)' % (pyprop, self.nameofargs(
            (prop.fget, prop.fset, prop.fdel, prop.__doc__))) )
        return pyprop

    def nameof_code(self, code):
        args = (code.co_argcount, code.co_nlocals, code.co_stacksize,
                code.co_flags, code.co_code, code.co_consts, code.co_names,
                code.co_varnames, code.co_filename, code.co_name,
                code.co_firstlineno, code.co_lnotab, code.co_freevars,
                code.co_cellvars)
        if not self.inline_consts:
            # make the code, filename and lnotab strings nicer
            codestr = code.co_code
            codestrname = self.uniquename('gcodestr_' + code.co_name)
            self.picklenames[Constant(codestr)] = codestrname
            self.initcode.append('%s = %r' % (codestrname, codestr))
            fnstr = code.co_filename
            fnstrname = self.uniquename('gfname_' + code.co_name)
            self.picklenames[Constant(fnstr)] = fnstrname
            self.initcode.append('%s = %r' % (fnstrname, fnstr))
            lnostr = code.co_lnotab
            lnostrname = self.uniquename('glnotab_' + code.co_name)
            self.picklenames[Constant(lnostr)] = lnostrname
            self.initcode.append('%s = %r' % (lnostrname, lnostr))
        argstr = self.nameofargs(args)
        codeobj = self.uniquename('gcode_' + code.co_name)
        self.initcode.append('%s = new.code(%s)' % (codeobj, argstr))
        return codeobj

    def nameof_file(self, fil):
        if fil is sys.stdin:  return "sys.stdin"
        if fil is sys.stdout: return "sys.stdout"
        if fil is sys.stderr: return "sys.stderr"
        raise Exception, 'Cannot translate an already-open file: %r' % (fil,)

    def nameof_methodwrapper(self, wp):
        # this object should be enhanced in CPython!
        reprwp = repr(wp)
        name = wp.__name__
        def dummy_methodwrapper():
            return reprwp + (': method %s of unknown object '
                'cannot be reconstructed, sorry!' % name )
        return self.nameof(dummy_methodwrapper)

    def later(self, gen):
        self.latercode.append((gen, self.debugstack))

    def spill_source(self, final):
        def write_block(lines):
            if not lines:
                return
            txt = '\n'.join(lines)
            print >> self.outfile, txt
            print >> self.outfile, '## SECTION ##'

        if not self.outfile:
            return
        chunk = self._partition
        while len(self.initcode) >= chunk:
            write_block(self.initcode[:chunk])
            del self.initcode[:chunk]
        if final and self.initcode:
            write_block(self.initcode)
            del self.initcode[:]

    def collect_initcode(self):
        while self.latercode:
            gen, self.debugstack = self.latercode.pop()
            #self.initcode.extend(gen) -- eats TypeError! bad CPython!
            for line in gen:
                self.initcode.append(line)
            self.debugstack = ()
            if len(self.initcode) >= self._partition:
                self.spill_source(False)
        self.spill_source(True)

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

def _ex(lis, *args):
    lis.extend(args)

def _rec(*args):
    return _reconstructor(*args)
