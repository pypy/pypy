"""
Implementation of a translator from application Python to
interpreter level RPython.

The idea is that we can automatically transform application level
implementations of methods into some equivalent representation at
interpreter level. Then, the RPython to C translation might
hopefully spit out some more efficient code than always interpreting
these methods.

Note that the application level functions are treated as rpythonic,
in a sense that globals are constants, for instance. This definition
is not exact and might change.

The interface for this module is

    (initfunc, newsrc) = translate_as_module(
                                sourcetext,
                                filename=None,
                                modname="app2interpexec",
                                tmpname=None)

If filename is given, it is used as a reference where
this sourcetext can be literally found, to produce
real line numbers. It cannot be just any name but
must exist and contain the source code somewhere.

modname is optional and will be put into the dictionary
to be created.

tmpname is optional. If given, a temporary file will
be created for debugging purposes.

The returned newsrc is the generated source text.
It is used in gateway.py's caching mechanism.
The initfunc result is a function named "init"+modname
It must be called with a space instance and returns
a wrapped dict which is suitable to use as a module dict,
containing all trnaslatedobjects with their originalname.

Integration of this module is finished.
There are no longer hand-generated source
pieces in pypy svn.
"""

from __future__ import generators
import autopath, os, sys, types
import inspect
import cPickle as pickle, __builtin__
from copy_reg import _HEAPTYPE
from pypy.objspace.flow.model import Variable, Constant, SpaceOperation
from pypy.objspace.flow.model import c_last_exception, checkgraph
from pypy.interpreter.pycode import CO_VARARGS, CO_VARKEYWORDS
from types import FunctionType, CodeType, ModuleType, MethodType
from pypy.interpreter.error import OperationError
from pypy.interpreter.argument import Arguments
from pypy.translator.backendopt.ssa import SSI_to_SSA

from pypy.translator.translator import TranslationContext
from pypy.objspace.flow.objspace import FlowObjSpace

from pypy.tool.sourcetools import render_docstr, NiceCompile

from pypy.translator.gensupp import ordered_blocks, UniqueList, builtin_base, \
     uniquemodulename, C_IDENTIFIER, NameManager


import pypy # __path__
import py.path
from pypy.tool.ansi_print import ansi_log

log = py.log.Producer("geninterp")
py.log.setconsumer("geninterp", ansi_log)

GI_VERSION = '1.1.23'  # bump this for substantial changes
# ____________________________________________________________

try:
    set
except NameError:
    class fake_set(object):
        pass
    class fake_frozenset(object):
        pass
    builtin_set = fake_set
    builtin_frozenset = fake_frozenset
    faked_set = True
else:
    builtin_set = set
    builtin_frozenset = frozenset
    faked_set = False

def eval_helper(self, typename, expr):
    name = self.uniquename("gtype_%s" % typename)
    unique = self.uniquenameofprebuilt("eval_helper", eval_helper)
    self.initcode.append1(
        'def %s(expr):\n'
        '    dic = space.newdict()\n'
        '    if "types." in expr:\n'
        '        space.exec_("import types", dic, dic)\n'
        '    else:\n'
        '        space.exec_("", dic, dic)\n'
        '    return space.eval(expr, dic, dic)' % (unique, ))
    self.initcode.append1('%s = %s(%r)' % (name, unique, expr))
    return name

def unpickle_helper(self, name, value):
    unique = self.uniquenameofprebuilt("unpickle_helper", unpickle_helper)
    self.initcode.append1(
        'def %s(value):\n'
        '    dic = space.newdict()\n'
        '    space.exec_("import cPickle as pickle", dic, dic)\n'
        '    return space.eval("pickle.loads(%%r)" %% value, dic, dic)' % unique)
    self.initcode.append1('%s = %s(%r)' % (
        name, unique, pickle.dumps(value, 2)) )

# hey, for longs we can do even easier:
def long_helper(self, name, value):
    unique = self.uniquenameofprebuilt("long_helper", long_helper)
    self.initcode.append1(
        'def %s(value):\n'
        '    dic = space.newdict()\n'
        '    space.exec_("", dic, dic) # init __builtins__\n'
        '    return space.eval(value, dic, dic)' % unique)
    self.initcode.append1('%s = %s(%r)' % (
        name, unique, repr(value) ) )

def bltinmod_helper(self, mod):    
    name = self.uniquename("mod_%s" % mod.__name__)
    unique = self.uniquenameofprebuilt("bltinmod_helper", bltinmod_helper)
    self.initcode.append1(
        'def %s(name):\n'
        '    dic = space.newdict()\n'
        '    space.exec_("import %%s" %% name, dic, dic)\n'
        '    return space.eval("%%s" %% name, dic, dic)' % (unique, ))
    self.initcode.append1('%s = %s(%r)' % (name, unique, mod.__name__))
    return name

class GenRpy:
    def __init__(self, translator, entrypoint=None, modname=None, moddict=None):
        self.translator = translator
        if entrypoint is None:
            entrypoint = translator.entrypoint
        self.entrypoint = entrypoint
        self.modname = self.trans_funcname(modname or
                        uniquemodulename(entrypoint))
        self.moddict = moddict # the dict if we translate a module
        
        def late_OperationError():
            self.initcode.append1(
                'from pypy.interpreter.error import OperationError as gOperationError')
            return 'gOperationError'
        def late_Arguments():
            self.initcode.append1('from pypy.interpreter import gateway')
            return 'gateway.Arguments'

        self.rpynames = {Constant(None).key:  'space.w_None',
                         Constant(False).key: 'space.w_False',
                         Constant(True).key:  'space.w_True',
                         Constant(Ellipsis).key: 'space.w_Ellipsis',
                         Constant(NotImplemented).key: 'space.w_NotImplemented',
                         Constant(OperationError).key: late_OperationError,
                         Constant(Arguments).key: late_Arguments,
                       }
        u = UniqueList
        self.initcode = u()    # list of lines for the module's initxxx()
        self.latercode = u()   # list of generators generating extra lines
                               #   for later in initxxx() -- for recursive
                               #   objects
        self.namespace = NameManager()
        self.namespace.make_reserved_names('__doc__ __args__ space goto')
        self.globaldecl = []
        self.globalobjects = []
        self.pendingfunctions = []
        self.currentfunc = None
        self.debugstack = ()  # linked list of nested nameof()

        # special constructors:
        self.has_listarg = {}
        for name in "newtuple newlist".split():
            self.has_listarg[name] = name

        # catching all builtins in advance, to avoid problems
        # with modified builtins

        # add a dummy _issubtype() to builtins
        if not hasattr(__builtin__, '_issubtype'):
            def _issubtype(cls1, cls2):
                raise TypeError, "this dummy should *not* be reached"
            __builtin__._issubtype = _issubtype
        
        class bltinstub:
            def __init__(self, name):
                self.__name__ = name
            def __repr__(self):
                return '<%s>' % self.__name__
            
        self.builtin_ids = dict( [
            (id(value), bltinstub(key))
            for key, value in __builtin__.__dict__.items()
            if callable(value) and type(value) not in [types.ClassType, type] ] )
        
        self.space = FlowObjSpace() # for introspection

        self.use_fast_call = True
        self.specialize_goto = False
        self._labeltable = {} # unique label names, reused per func

        self._space_arities = None
        
    def expr(self, v, localscope, wrapped = True):
        if isinstance(v, Variable):
            return localscope.localname(v.name, wrapped)
        elif isinstance(v, Constant):
            return self.nameof(v.value,
                               debug=('Constant in the graph of', self.currentfunc))
        else:
            raise TypeError, "expr(%r)" % (v,)

    def arglist(self, args, localscope):
        res = [self.expr(arg, localscope) for arg in args]
        return ", ".join(res)

    def oper(self, op, localscope):
        if op.opname == 'issubtype':
            arg = op.args[1]
            if (not isinstance(arg, Constant)
                or not isinstance(arg.value, (type, types.ClassType))):
                  op = SpaceOperation("simple_call",
                                      [Constant(issubclass)]+op.args,
                                      op.result)
        if op.opname == "simple_call":
            v = op.args[0]
            space_shortcut = self.try_space_shortcut_for_builtin(v, len(op.args)-1,
                                                                 op.args[1:])
            if space_shortcut is not None:
                # space method call
                exv = space_shortcut
                fmt = "%(res)s = %(func)s(%(args)s)"
            else:
                # import sys|__builtin__|_codecs avoid going through __import__
                if isinstance(v, Constant) and v.value is __builtin__.__import__:
                    name, glb, loc, frm_lst = op.args[1:]
                    if (isinstance(name, Constant) and name.value in ('sys', '__builtin__', '_codecs') and
                        isinstance(loc, Constant) and loc.value is None and
                        isinstance(frm_lst, Constant) and frm_lst.value is None):
                        return "%s = space.getbuiltinmodule(%r)" % (self.expr(op.result, localscope),
                                                                    name.value)
                exv = self.expr(v, localscope)                
                # default for a spacecall:
                fmt = "%(res)s = space.call_function(%(func)s, %(args)s)"
                # see if we can optimize for a fast call.
                # we just do the very simple ones.
                if self.use_fast_call and (isinstance(v, Constant)
                                           and exv.startswith('gfunc_')):
                    func = v.value
                    if (not func.func_code.co_flags & CO_VARARGS) and (
                        func.func_defaults is None):
                        fmt = "%(res)s = fastf_%(func)s(space, %(args)s)"
                        exv = exv[6:]
            return fmt % {"res" : self.expr(op.result, localscope),
                          "func": exv,
                          "args": self.arglist(op.args[1:], localscope) }
        if op.opname == "call_args":
            v = op.args[0]
            exv = self.expr(v, localscope)
            fmt = (
                "_args = %(Arg)s.fromshape(space, %(shape)s, [%(data_w)s])\n"
                "%(res)s = space.call_args(%(func)s, _args)")
            assert isinstance(op.args[1], Constant)
            shape = op.args[1].value
            # make a list out of the second shape elt.
            shape = shape[0], list(shape[1]), shape[2], shape[3]
            return fmt % {"res": self.expr(op.result, localscope),
                          "func": exv,
                          "shape": repr(shape),
                          "data_w": self.arglist(op.args[2:], localscope),
                          'Arg': self.nameof(Arguments) }
        if op.opname == "hint":
            return "%s = %s" % (self.expr(op.result, localscope),
                                self.expr(op.args[0], localscope))
        if op.opname in self.has_listarg:
            fmt = "%s = %s([%s])"
        else:
            fmt = "%s = %s(%s)"
        # special case is_true
        opname = op.opname
        if opname.startswith('getitem_'):
            opname = 'getitem'
        wrapped = opname != "is_true"
        oper = "space.%s" % opname
        return fmt % (self.expr(op.result, localscope, wrapped), oper,
                      self.arglist(op.args, localscope))

    def large_assignment(self, left, right, margin=65):
        expr = "(%s) = (%s)" % (", ".join(left), ", ".join(right))
        pieces = expr.split(",")
        res = [pieces.pop(0)]
        for piece in pieces:
            if len(res[-1])+len(piece)+1 > margin:
                res[-1] += ","
                res.append(piece)
            else:
                res[-1] += (","+piece)
        return res

    def large_initialize(self, vars, margin=65):
        res = []
        nonestr = "None"
        margin -= len(nonestr)
        for var in vars:
            ass = var+"="
            if not res or len(res[-1]) >= margin:
                res.append(ass)
            else:
                res[-1] += ass
        res = [line + nonestr for line in res]
        return res

    def mklabel(self, blocknum):
        if self.specialize_goto:
            lbname = self._labeltable.get(blocknum)
            if not lbname:
                self.initcode.append1(
                    'from pypy.objspace.flow.framestate import SpecTag')
                lbname = self.uniquename("glabel_%d" % blocknum)
                self._labeltable[blocknum] = lbname
                self.initcode.append1('%s = SpecTag()' % lbname)
            return lbname
        else:
            return repr(blocknum)

    def gen_link(self, link, localscope, blocknum, block, linklocalvars=None):
        "Generate the code to jump across the given Link."
        linklocalvars = linklocalvars or {}
        left, right = [], []
        for a1, a2 in zip(link.args, link.target.inputargs):
            if a1 in linklocalvars:
                src = linklocalvars[a1]
            else:
                src = self.expr(a1, localscope)
            dest = self.expr(a2, localscope)
            if src != dest:
                left.append(dest)
                right.append(src)
        if left: # anything at all?
            txt = "%s = %s" % (", ".join(left), ", ".join(right))
            if len(txt) <= 65: # arbitrary
                yield txt
            else:
                for line in self.large_assignment(left, right):
                    yield line
        goto = blocknum[link.target]
        yield 'goto = %s' % self.mklabel(goto)
        if goto <= blocknum[block]:
            yield 'continue'

    def register_early(self, obj, name):
        # this was needed for recursive lists.
        # note that self.latercode led to too late initialization.
        key = Constant(obj).key
        self.rpynames[key] = name

    def nameof(self, obj, debug=None, namehint=None):
        key = Constant(obj).key
        try:
            txt = self.rpynames[key]
            if type(txt) is not str:
                # this is a predefined constant, initialized on first use
                func = txt
                txt = func()
                self.rpynames[key] = txt
            return txt
            
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
                # shortcutting references to __builtin__
                if id(obj) in self.builtin_ids:
                    func = self.builtin_ids[id(obj)]
                    #name = self.get_nameof_builtin_func(func)
                    # the above is quicker in principle, but pulls more
                    # stuff in, so it is slower right now.
                    name = "(space.builtin.get(space.str_w(%s)))" % self.nameof(func.__name__)
                else:
                    for cls in type(obj).__mro__:
                        meth = getattr(self,
                                       'nameof_' + cls.__name__.replace(' ', ''),
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
            self.rpynames[key] = name
            return name

    def get_nameof_builtin_func(self, func):
        # this is a hack!
        # in some cases, like exceptions, we don't have space.builtin available,
        #so we crate a fall-back...
        name = self.uniquename('gbltin_' + func.__name__)
        self.initcode.append1('''\
try:
    # see if we have space.builtin in this context
    space.builtin
except AttributeError:
    print "didn't get", %(bltin)r
    def %(name)s(space, __args__):
        w_func = space.builtin.get(%(bltin)r)
        return space.call_args(w_func, __args__)
    %(name)s = space.wrap(gateway.interp2app(%(name)s, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
else:
        print "got it:", %(bltin)r
        %(name)s = space.builtin.get(%(bltin)r)'''
        % {'name': name, 'bltin': func.__name__} )
        return name

    def uniquename(self, basename):
        name = self.namespace.uniquename(basename)
        self.globalobjects.append(name)
        self.globaldecl.append('# global object %s' % (name,))
        return name

    def uniquenameofprebuilt(self, basename, obj):
        # identifying an object and giving it a name,
        # without the attempt to render it.
        key = Constant(obj).key
        try:
            txt = self.rpynames[key]
        except KeyError:
            self.rpynames[key] = txt = self.uniquename(basename)
        return txt
            
    def nameof_object(self, value):
        if type(value) is not object:
            # try to just wrap it?
            name = self.uniquename('g_%sinst_%r' % (type(value).__name__, value))
            self.initcode.append1('%s = space.wrap(%r)' % (name, value))
            return name
        name = self.uniquename('g_object')
        self.initcode.append('_tup = space.newtuple([])\n'
                                '%s = space.call(space.w_object, _tup)'
                                % name)
        return name

    def is_module_builtin(self, mod):
        if not hasattr(mod, "__file__") or mod.__file__ is None:
            return True
        if not (mod.__file__.endswith('.pyc') or
                mod.__file__.endswith('.py') or
                mod.__file__.endswith('.pyo')):
            return True
        if mod.__file__.endswith('*.py'):  # on top of PyPy, a mixed module
            return True
        return False

    def nameof_module(self, value):
        if value is os or self.is_module_builtin(value):
            return bltinmod_helper(self, value)

        # we might have createda reference to a module
        # that is non-standard.

        # SKIPPING
        return "space.w_None"

        # check whether we can import
        try:
            import value
            need_extra_path = False
        except ImportError:
            need_extra_path = True
        name = self.uniquename('mod_%s' % value.__name__)
        if need_extra_path:
            self.initcode.append1('import pypy')
            self.initcode.append1('import sys')
            self.initcode.append1('import os')
            self.initcode.append1('for pkgdir in pypy.__path__:\n'
                                  '    libdir = os.path.join(pkgdir, "lib")\n'
                                  '    if os.path.isdir(libdir):\n'
                                  '        break\n'
                                  'else:\n'
                                  '    raise Exception, "cannot find pypy/lib directory"\n'
                                  'sys.path.insert(0, libdir)\n')
            self.initcode.append1('try:\n'
                                  '    import %s as _tmp\n'
                                  'finally:\n'
                                  '    if libdir in sys.path:\n'
                                  '        sys.path.remove(libdir)\n' % value.__name__)
        else:
            self.initcode.append1('import %s as _tmp' % value.__name__)
        self.initcode.append1('%s = space.wrap(_tmp)' % (name))
        return name
        

    def nameof_int(self, value):
        if value >= 0:
            name = 'gi_%d' % value
        else:
            # make sure that the type ident is completely described by
            # the prefixbefore the initial '_' for easy postprocessing
            name = 'gi_minus_%d' % abs(value)
        name = self.uniquename(name)
        self.initcode.append1('%s = space.wrap(%d)' % (name, value))
        return name

    def nameof_long(self, value):
        # assume we want them in hex most of the time
        if value < 256L:
            s = "%dL" % value
        else:
            s = "0x%08xL" % value
        if value >= 0:
            name = 'glong_%s' % s
        else:
            # mae sure that the type ident is completely described by
            # the prefix  before the initial '_'
            name = 'glong_minus_%d' % abs(value)
        name = self.uniquename(name)
        # allow literally short longs only, meaning they
        # must fit into a machine word.
        if (sys.maxint*2+1)&value == value:
            self.initcode.append1('%s = space.wrap(%s) # XXX implement long!' % (name, s))
        else:
            long_helper(self, name, value)
        return name

    def nameof_float(self, value):
        name = 'gfloat_%s' % value
        name = (name.replace('-', 'minus')
                    .replace('.', 'dot'))
        name = self.uniquename(name)
        # handle overflows
        if value != 0.0 and 2*value == value:
            self.initcode.append1('float_inf = 1e200\nfloat_inf *= float_inf')
            sign = '-+'[value >= 0]
            self.initcode.append('%s = space.wrap(%sfloat_inf)' % (name, sign))
        else:
            self.initcode.append('%s = space.wrap(%r)' % (name, value))
        return name
    
    def nameof_str(self, value):
        if [c for c in value if c<' ' or c>'~' or c=='"' or c=='\\']:
            # non-printable string
            namestr = repr(value)[1:-1]
        else:
            # printable string
            namestr = value
        if not namestr:
            namestr = "_emptystr_"
        name = self.uniquename('gs_' + namestr[:32])
        if len(value) < 30 and "\n" not in value:
            txt = '%s = space.new_interned_str(%r)' % (name, value)
        else:
            txt = render_docstr(value, '%s = space.new_interned_str(\n' % name, ')')
            txt = txt,  # not splitted
        self.initcode.append(txt)
        return name

    def skipped_function(self, func):
        # debugging only!  Generates a placeholder for missing functions
        # that raises an exception when called.
        name = self.uniquename('gskippedfunc_' + func.__name__)
        self.globaldecl.append('# global decl %s' % (name, ))
        self.initcode.append('# build func %s' % name)
        return name

    def skipped_class(self, cls):
        # debugging only!  Generates a placeholder for missing classes
        # that raises an exception when called.
        name = self.uniquename('gskippedclass_' + cls.__name__)
        self.globaldecl.append('# global decl %s' % (name, ))
        self.initcode.append1('# build class %s' % name)
        return name

    def trans_funcname(self, s):
        return s.translate(C_IDENTIFIER)

    def nameof_function(self, func, namehint=''):
        if hasattr(func, 'geninterplevel_name'):
            return func.geninterplevel_name(self)
        if func.func_globals is None:
            # built-in functions on top of PyPy
            return self.nameof_builtin_function(func)

        printable_name = '(%s:%d) %s' % (
            self.trans_funcname(func.func_globals.get('__name__', '?')),
            func.func_code.co_firstlineno,
            func.__name__)
        if (func.func_doc and
            func.func_doc.lstrip().startswith('NOT_RPYTHON')):
            log.WARNING("skipped %s" % printable_name)
            return self.skipped_function(func)
        name = self.uniquename('gfunc_' + self.trans_funcname(
            namehint + func.__name__))

        positional, varargs, varkwds, defs = inspect.getargspec(func)
        if varargs is varkwds is defs is None:
            unwrap = ', '.join(['gateway.W_Root']*len(positional))
            interp_name = 'fastf_' + name[6:]            
        else:
            unwrap = 'gateway.Arguments'
            interp_name = 'f_' + name[6:]
        
        self.initcode.append1('from pypy.interpreter import gateway')
        self.initcode.append1('%s = space.wrap(gateway.interp2app(%s, unwrap_spec=[gateway.ObjSpace, %s]))' %
                              (name, interp_name, unwrap))
        self.pendingfunctions.append(func)
        return name

    def nameof_staticmethod(self, sm):
        # XXX XXX XXXX
        func = sm.__get__(42.5)
        name = self.uniquename('gsm_' + func.__name__)
        functionname = self.nameof(func)
        self.initcode.append1('%s = space.wrap(%s)' % (name, functionname))
        return name

    def nameof_instancemethod(self, meth):
        if meth.im_func.func_globals is None:
            # built-in methods (bound or not) on top of PyPy
            return self.nameof_builtin_method(meth)
        if meth.im_self is None:
            # no error checking here
            return self.nameof(meth.im_func, namehint="%s_" % meth.im_class.__name__)
        else:
            ob = self.nameof(meth.im_self)
            func = self.nameof(meth.im_func)
            typ = self.nameof(meth.im_class)
            name = self.uniquename('gmeth_' + meth.im_func.__name__)
            funcname = self.nameof(meth.im_func.__name__)
            self.initcode.append1(
                '%s = space.getattr(%s, %s)' % (name, ob, funcname))
            return name

    nameof_method = nameof_instancemethod   # when run on top of PyPy

    def should_translate_attr(self, pbc, attr):
        ignore = getattr(pbc.__class__, 'NOT_RPYTHON_ATTRIBUTES', [])
        if attr in ignore:
            return False
        else:
            return "probably"   # True

    def later(self, gen):
        self.latercode.append1((gen, self.debugstack))

    def nameof_instance(self, instance):
        klass = instance.__class__
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
                    try:
                            yield 'space.setattr(%s, %s, %s)' % (
                                name, self.nameof(key), self.nameof(value))
                    except:
                        log.ERROR("Problem while generating %s of %r" % (
                                name, instance))
                        raise
        self.initcode.append1("%s = space.call_method(%s, '__new__', %s)" % (
                             name, cls, cls))
        self.later(initinstance())
        return name

    def space_arities(self):
        if self._space_arities is None:
            arities = self._space_arities = {}
            for name, sym, arity, specnames in self.space.MethodTable:
                arities[name] = arity
            arities['isinstance'] = 2
        return self._space_arities
        
    def try_space_shortcut_for_builtin(self, v, nargs, args):
        if isinstance(v, Constant) and id(v.value) in self.builtin_ids:
            name = self.builtin_ids[id(v.value)].__name__
            if hasattr(self.space, name):
                if self.space_arities().get(name, -1) == nargs:
                    if name != 'isinstance':
                        return "space.%s" % name
                    else:
                        arg = args[1]
                        if (isinstance(arg, Constant)
                            and isinstance(arg.value, (type, types.ClassType))):
                            return "space.isinstance"
        return None
        
    def nameof_builtin_function_or_method(self, func):
        if func.__self__ is None:
            return self.nameof_builtin_function(func)
        else:
            return self.nameof_builtin_method(func)

    def nameof_builtin_function(self, func):
        # builtin function
        if id(func) in self.builtin_ids:
            func = self.builtin_ids[id(func)]
            return "(space.builtin.get(space.str_w(%s)))" % self.nameof(func.__name__)
        # where does it come from? Python2.2 doesn't have func.__module__
        for modname, module in sys.modules.items():
            if not self.is_module_builtin(module):
                continue    # skip non-builtin modules
            if func is getattr(module, func.__name__, None):
                break
        else:
            raise Exception, '%r not found in any built-in module' % (func,)
        #if modname == '__builtin__':
        #    # be lazy
        #    return "(space.builtin.get(space.str_w(%s)))" % self.nameof(func.__name__)
        if modname == 'sys':
            # be lazy
            return "(space.sys.get(space.str_w(%s)))" % self.nameof(func.__name__)                
        else:
            name = self.uniquename('gbltin_' + func.__name__)
            self.initcode.append1('%s = space.getattr(%s, %s)' % (
                name, self.nameof(module), self.nameof(func.__name__)))
        return name

    def nameof_builtin_method(self, meth):
        try:
            im_self = meth.__self__
        except AttributeError:
            im_self = meth.im_self    # on top of PyPy
        if im_self is None:
            # builtin unbound method (only on top of PyPy)
            name = self.nameof_wrapper_descriptor(meth)
        else:
            # builtin (bound) method
            name = self.uniquename('gbltinmethod_' + meth.__name__)
            self.initcode.append1('%s = space.getattr(%s, %s)' % (
                name, self.nameof(im_self), self.nameof(meth.__name__)))
        return name

    def nameof_classobj(self, cls):
        initcode = []
        printable_name = cls.__name__
        if cls.__doc__ and cls.__doc__.lstrip().startswith('NOT_RPYTHON'):
            #raise Exception, "%r should never be reached" % (cls,)
            log.WARNING("skipped class %s" % printable_name)
            return self.skipped_class(cls)

        metaclass = "space.w_type"
        name = self.uniquename('gcls_' + cls.__name__)

        if issubclass(cls, py.builtin.BaseException):
            # if cls.__module__ == 'exceptions':
            # don't rely on this, py.magic redefines AssertionError
            if getattr(__builtin__,cls.__name__,None) is cls:
                # exception are defined on the space
                return 'space.w_%s' % cls.__name__

        if not isinstance(cls, type):
            assert type(cls) is types.ClassType
            # do *not* change metaclass, but leave the
            # decision to what PyPy thinks is correct.
            # metaclass = 'space.w_classobj'

        basenames = [self.nameof(base) for base in cls.__bases__]

        def initclassobj():
            content = cls.__dict__.items()
            content.sort()
            for key, value in content:
                if key.startswith('__'):
                    if key in ['__module__', '__doc__', '__dict__',
                               '__weakref__', '__metaclass__', '__slots__',
                               '__new__', '__del__']:
                        continue

                # redirect value through class interface, in order to
                # get methods instead of functions.
                value = getattr(cls, key)

                if isinstance(value, staticmethod) and value.__get__(1) not in self.translator.flowgraphs and self.translator.frozen:
                    log.WARNING("skipped staticmethod: %s" % value)
                    continue
##                 if isinstance(value, FunctionType) and value not in self.translator.flowgraphs and self.translator.frozen:
##                     log.WARNING("skipped function: %s" % value)
##                     continue
                if isinstance(value, MethodType) and value.im_self is cls:
                    log.WARNING("skipped classmethod: %s" % value)
                    continue
                    
                yield 'space.setattr(%s, %s, %s)' % (
                    name, self.nameof(key), self.nameof(value))

        baseargs = ", ".join(basenames)
        initcode.append('_dic = space.newdict()')
        for key, value in cls.__dict__.items():
            if key.startswith('__'):
                if key in ['__module__', '__metaclass__', '__slots__',
                           '__new__', '__del__']:
                    keyname = self.nameof(key)
                    valname = self.nameof(value)
                    initcode.append("space.setitem(_dic, %s, %s)" % (
                        keyname, valname))

        if cls.__doc__ is not None:
            sdoc = self.nameof("__doc__")
            docobj = cls.__dict__["__doc__"]
            if type(docobj) in (str, unicode):
                docstr = render_docstr(cls, "_doc = space.wrap(", ")")
                initcode.append((docstr,)) # not splitted
            else:
                initcode.append("_doc = %s" % self.nameof(docobj) )
            initcode.append("space.setitem(_dic, %s, _doc)" % (sdoc,))
        cls_name = self.nameof(cls.__name__)
        for l in initcode:
            self.initcode.append(l)
        self.initcode.append1('_bases = space.newtuple([%(bases)s])\n'
                             '_args = space.newtuple([%(name)s, _bases, _dic])\n'
                             '%(klass)s = space.call(%(meta)s, _args)'
                             % {"bases": baseargs,
                                "klass": name,
                                "name" : cls_name,
                                "meta" : metaclass} )
        
        self.later(initclassobj())
        return name

    nameof_class = nameof_classobj   # for Python 2.2

    typename_mapping = {
        object: 'space.w_object',
        int:    'space.w_int',
        long:   'space.w_long',
        bool:   'space.w_bool',
        list:   'space.w_list',
        tuple:  'space.w_tuple',
        dict:   'space.w_dict',
        str:    'space.w_str',
        float:  'space.w_float',
        slice:  'space.w_slice',
        types.InstanceType: (eval_helper, 'InstanceType', 'types.InstanceType'),
        type:   'space.w_type',
        complex: (eval_helper, 'complex', 'types.ComplexType'),
        unicode:'space.w_unicode',
        basestring: (eval_helper, 'basestring', 'basestring'),
        file:   (eval_helper, 'file', 'file'),
        type(None): (eval_helper, 'NoneType', 'type(None)'),
        CodeType: (eval_helper, 'code', 'type((lambda:42).func_code)'),
        ModuleType: (eval_helper, 'ModuleType', 'types.ModuleType'),
        xrange: (eval_helper, 'xrange', 'xrange'),

        ##r_int:  'space.w_int',
        ##r_uint: 'space.w_int',

        type(len): (eval_helper, 'FunctionType', 'type(lambda:42)'),
        # type 'method_descriptor':
        # XXX small problem here:
        # XXX with space.eval, we get <W_TypeObject(method)>
        # XXX but with wrap, we get <W_TypeObject(instancemethod)>
        type(list.append): (eval_helper, "method_descriptor", "type(list.append)"),
        # type 'wrapper_descriptor':
        type(type(None).__repr__): (eval_helper, "wrapper_descriptor",
                                    "type(type(None).__repr__)"),
        # type 'getset_descriptor':
        # XXX here we get <W_TypeObject(FakeDescriptor)>,
        # while eval gives us <W_TypeObject(GetSetProperty)>
        type(type.__dict__['__dict__']): (eval_helper, "getset_descriptor",
            "type(type.__dict__[\'__dict__\'])"),
        # type 'member_descriptor':
        # XXX this does not work in eval!
        # type(type.__dict__['__basicsize__']): "cannot eval type(type.__dict__['__basicsize__'])",
        # XXX there seems to be no working support for member descriptors ???
        type(types.GeneratorType.gi_frame):
            (eval_helper, "member_descriptor", 'type(property.fdel)'),
        types.ClassType: 'space.w_classobj',
        types.MethodType: (eval_helper, "instancemethod",
            "type((lambda:42).__get__(42))"),
        type(Ellipsis): (eval_helper, 'EllipsisType', 'types.EllipsisType'),
        builtin_set: (eval_helper, "set", "set"),
        builtin_frozenset: (eval_helper, "frozenset", "frozenset"),
        buffer: (eval_helper, "buffer", "buffer"),
    }

    def nameof_type(self, cls):
        if cls in self.typename_mapping:
            ret = self.typename_mapping[cls]
            if type(ret) is tuple:
                ret = ret[0](self, ret[1], ret[2])
            return ret
        if issubclass(cls, py.builtin.BaseException):   # Python 2.5 only
            # if cls.__module__ == 'exceptions':
            # don't rely on this, py.magic redefines AssertionError
            if getattr(__builtin__,cls.__name__,None) is cls:
                # exception are defined on the space
                return 'space.w_%s' % cls.__name__
        assert cls.__module__ != '__builtin__' or cls.__flags__&_HEAPTYPE, (
            "built-in class %r not found in typename_mapping "
            "while compiling %s" % (cls, self.currentfunc and
                                    self.currentfunc.__name__ or "*no function at all*"))
        return self.nameof_classobj(cls)

    def nameof_tuple(self, tup):
        name = self.uniquename('g%dtuple' % len(tup))
        args = [self.nameof(x) for x in tup]
        args = ', '.join(args)
        self.initcode.append1('%s = space.newtuple([%s])' % (name, args))
        return name

    def nameof_list(self, lis):
        name = self.uniquename('g%dlist' % len(lis))
        # note that self.latercode led to too late initialization.
        self.register_early(lis, name)
        # try to save at least one assignment.
        if lis and lis[0] is not lis:
            default = lis[0]
        else:
            default = None
        self.initcode.append('%s = space.newlist([%s])' % (name, self.nameof(default)))
        self.initcode.append('%s = space.mul(%s, %s)' % (name, name, self.nameof(len(lis))))
        for i in range(len(lis)):
            if lis[i] is not default:
                item = self.nameof(lis[i])
                self.initcode.append('space.setitem(%s, %s, %s);' % (
                    name, self.nameof(i), item))
        return name

    def nameof_dict(self, dic):
        assert dic is not __builtins__
        name = self.uniquename('g%ddict' % len(dic))
        self.register_early(dic, name)
        self.initcode.append('%s = space.newdict()' % (name,))
        for k in dic:
            if k == '__builtins__':
                continue
            self.initcode.append('space.setitem(%s, %s, %s)'%(
                name, self.nameof(k), self.nameof(dic[k])))
        return name

    # strange prebuilt instances below, don't look too closely
    # XXX oh well.
    def nameof_member_descriptor(self, md):
        try:
            im_class = md.__objclass__
        except AttributeError:
            im_class = md.im_class    # on top of PyPy
        name = self.uniquename('gdescriptor_%s_%s' % (
            im_class.__name__, md.__name__))
        cls = self.nameof(im_class)
        self.initcode.append1('%s = space.getattr(%s, %s)' %
                                (name, cls, self.nameof(md.__name__)))
        return name
    nameof_getset_descriptor  = nameof_member_descriptor
    nameof_method_descriptor  = nameof_member_descriptor
    nameof_wrapper_descriptor = nameof_member_descriptor

    def nameof_property(self, prop):
        origin = prop.__doc__ # XXX quite a hack
        name = self.uniquename('gprop_' + origin)
        if not origin:
            raise ValueError("sorry, cannot build properties"
                             " without a helper in __doc__")
        # property is lazy loaded app-level as well, trigger it*s creation
        self.initcode.append1('space.builtin.get("property") # pull it in')
        globname = self.nameof(self.moddict)
        self.initcode.append('space.setitem(%s, space.new_interned_str("__builtins__"), '
                             'space.builtin.w_dict)' % globname)
        self.initcode.append('%s = space.eval("property(%s)", %s, %s)' %(
            name, origin, globname, globname) )
        self.initcode.append('space.delitem(%s, space.new_interned_str("__builtins__"))'
                             % globname)
        return name

    def nameof_file(self, fil):
        if fil is sys.stdin:
            return 'space.sys.get("stdin")'
        if fil is sys.stdout:
            return 'space.sys.get("stdout")'
        if fil is sys.stderr:
            return 'space.sys.get("stderr")'
        raise Exception, 'Cannot translate an already-open file: %r' % (fil,)

    def gen_source(self, fname, ftmpname=None, file=file):
        self.fname = fname
        self.ftmpname = ftmpname

        # generate unordered source file, first.
        # I prefer this over ordering everything in memory.
        fname = self.fname
        if self.ftmpname:
            fname = self.ftmpname
        f = file(fname, "w")
        # generate ordered source file
        try:
            self.f = f
            self.gen_source_temp()
        finally:
            f.close()

        def copyfile(source, target):
            f = file(source)
            data = f.read()
            f.close()
            f = file(target, "w")
            f.write(data)
            f.close()

        def order_sections(fname):
            sep = "\n##SECTION##\n"
            f = file(fname)
            txt = f.read()
            f.close()
            pieces = txt.split(sep)
            prelude = pieces.pop(0)
            postlude = pieces.pop()
            dic = {}
            while pieces:
                func = pieces.pop()
                head = pieces.pop()
                key = makekey(head, len(pieces))
                dic[key] = head + sep + func
            lis = dic.items()
            lis.sort()
            lis = [prelude] + [func for head, func in lis] + [postlude]
            txt = sep.join(lis)
            f = file(fname, "w")
            f.write(txt)
            f.close()

        def makekey(txt, uniqueno):
            dic = {}
            for line in txt.split("\n"):
                ign, name, value = line.split(None, 2)
                dic[name] = eval(value, {})
            key = (dic["filename"], dic["firstlineno"],
                   dic["function"], uniqueno)
            return key

        order_sections(fname)
        if self.ftmpname:
            copyfile(self.ftmpname, self.fname)
        
    def gen_source_temp(self):
        f = self.f

        # header
        print >> f, self.RPY_HEADER
        print >> f

        info = {
            'modname': self.modname,
             # the side-effects of this is kick-start the process
            'entrypoint': None # self.nameof(self.entrypoint),
            }
        # header """def initmodule(space):"""
        print >> f, self.RPY_INIT_HEADER % info

        # doc
        if self.moddict and self.moddict.get("__doc__"):
            doc = self.moddict["__doc__"]
            print >> f, render_docstr(doc, "  __doc__ = \\\n")
            print >> f
            # make sure it is not rendered again
            key = Constant(doc).key
            self.rpynames[key] = "w__doc__"
            self.initcode.append("w__doc__ = space.new_interned_str(__doc__)")

        # info.entrypoint must be done *after* __doc__ is handled,
        # because nameof(entrypoint) might touch __doc__ early.
        info["entrypoint"] = self.nameof(self.entrypoint)
        
        # function implementations
        while self.pendingfunctions or self.latercode:
            if self.pendingfunctions:
                func = self.pendingfunctions.pop()
                self.currentfunc = func
                self.gen_rpyfunction(func)
            # collect more of the latercode after each function
            while self.latercode:
                gen, self.debugstack = self.latercode.pop()
                #self.initcode.extend(gen) -- eats TypeError! bad CPython!
                for line in gen:
                    self.initcode.append1(line)
                self.debugstack = ()
            self.gen_global_declarations()

        # set the final splitter
        print >> f, "##SECTION##"
        # footer, init code
        for codelines in self.initcode:
            # keep docstrings unindented
            indent = "  "
            if type(codelines) is tuple:
                codelines = codelines[0].split("\n", 1)
                codelines[0] = indent + codelines[0]
                indent = ""
            else:
                codelines = codelines.split("\n")
            for codeline in codelines:
                print >> f, indent + codeline

        self.gen_trailer(info, "  ")
        # do not close the file here!

    def gen_trailer(self, info, indent):
        if self.moddict:
            # we are generating a module, no __main__ etc.
            print >> self.f, indent + "return %s" % self.nameof(self.entrypoint)
            print >> self.f
        else:
            # we should have an entrypoint function
            info['entrypointname'] = self.trans_funcname(self.entrypoint.__name__)
            print >> self.f, self.RPY_INIT_FOOTER % info
       
    def gen_global_declarations(self):
        g = self.globaldecl
        if g:
            f = self.f
            print >> f, '# global declaration%s' % ('s'*(len(g)>1))
            for line in g:
                print >> f, line
            print >> f
            del g[:]
        g = self.globalobjects
        for name in g:
            pass # self.initcode.append1('# REGISTER_GLOBAL(%s)' % (name,))
        del g[:]

    def rel_filename(self, name):
        # try to find a name relative to pypy and unify.
        # if not possible, stick with the original.
        ref = py.path.local(pypy.__path__[0])
        rel = py.path.local(name).relto(ref)
        if rel:
            # make it os independent
            return rel.replace('\\', '/')
        return name # no success

    def gen_rpyfunction(self, func):
        try:
            graph = self.translator.buildflowgraph(func, True)
        except Exception, e:
            print 20*"*", e
            print func
            raise
        SSI_to_SSA(graph)
        checkgraph(graph)

        f = self.f
        print >> f, "##SECTION##" # simple to split, afterwards
        print >> f, ("## filename    %r\n"
                     "## function    %r\n"
                     "## firstlineno %d") % (
            self.rel_filename(func.func_code.co_filename),
            func.func_code.co_name,
            func.func_code.co_firstlineno)
        print >> f, "##SECTION##"
        localscope = self.namespace.localScope()
        body = list(self.rpyfunction_body(graph, localscope))
        name_of_defaults = [self.nameof(x, debug=('Default argument of', func))
                            for x in (func.func_defaults or ())]
        self.gen_global_declarations()

        # print header
        docstr = render_docstr(func, "    ")
        cname = self.nameof(func)
        assert cname.startswith('gfunc_')
        f_name = 'f_' + cname[6:]

##        # collect all the local variables
##        graph = self.translator.getflowgraph(func)
##        localslst = []
##        def visit(node):
##            if isinstance(node, Block):
##                localslst.extend(node.getvariables())
##        traverse(visit, graph)
##        localnames = [self.expr(a, localscope) for a in uniqueitems(localslst)]

        # collect all the arguments
        vararg = varkw = None
        varargname = varkwname = None
        all_args = graph.getargs()
        p = len(all_args)
        if func.func_code.co_flags & CO_VARKEYWORDS:
            p -= 1
            varkw = graph.getargs()[p]
            varkwname = func.func_code.co_varnames[p]
        if func.func_code.co_flags & CO_VARARGS:
            p -= 1
            vararg = graph.getargs()[p]
            varargname = func.func_code.co_varnames[p]
        positional_args = all_args[:p]

        fast_args = [self.expr(a, localscope) for a in positional_args]
        if vararg is not None:
            vararg = self.expr(vararg, localscope)
            fast_args.append(vararg)
        if varkw is not None:
            varkw = self.expr(varkw, localscope)
            fast_args.append(varkw)
        fast_name = 'fast' + f_name

        fast_set = dict(zip(fast_args, fast_args))

        simple = (varargname is varkwname is None) and not name_of_defaults

        # create function declaration
        name = self.trans_funcname(func.__name__) # for <lambda>
        argstr = ", ".join(['space'] + fast_args)
        fast_function_header = ('  def %s(%s):'
                                % (name, argstr))

        def install_func(f_name, name):
            yield ''
            yield '  %s = %s' % (f_name, name)
            #import __builtin__
            #dic = __builtin__.__dict__
            #if dic.get(name):
            #    yield 'del %s # hiding a builtin!' % name
            #else:
            #    self.initcode.append1('del m.%s' % (name,))

        def tupstr(seq):
            if len(seq) == 1:
                fmt = '%s,'
            else:
                fmt = '%s'
            return fmt % ', '.join(seq)
        def tupassstr(seq):
            if not seq:
                return ""
            else:
                return tupstr(seq) + " = "

        if not simple:
            print >> f, '  def %s(space, __args__):' % (name,)
            if docstr is not None:
                print >> f, docstr
                print >> f

            print >> f, '    funcname = "%s"' % func.__name__
            kwlist = list(func.func_code.co_varnames[:func.func_code.co_argcount])
            signature = '    signature = %r' % kwlist
            signature = ", ".join([signature, repr(varargname), repr(varkwname)])
            print >> f, signature

            print >> f, '    defaults_w = [%s]' % ", ".join(name_of_defaults)

            print >> f, '    %s__args__.parse(funcname, signature, defaults_w)' % (
                tupassstr(fast_args),)
            print >> f, '    return %s(%s)' % (fast_name, ', '.join(["space"]+fast_args))

            for line in install_func(f_name, name):
                print >> f, line

            print >> f
        
        print >> f, fast_function_header
        if docstr is not None:
            print >> f, docstr

##        fast_locals = [arg for arg in localnames if arg not in fast_set]
##        # if goto is specialized, the false detection of
##        # uninitialized variables goes away.
##        if fast_locals and not self.specialize_goto:
##            print >> f
##            for line in self.large_initialize(fast_locals):
##                print >> f, "    %s" % line
##            print >> f

        # print the body
        for line in body:
            print >> f, line
        for line in install_func("fast"+f_name, name):
            print >> f, line
        print >> f

        # print the PyMethodDef
        # skipped


    def rpyfunction_body(self, graph, localscope):
        start = graph.startblock
        allblocks = ordered_blocks(graph)
        nblocks = len(allblocks)

        blocknum = {}
        for block in allblocks:
            blocknum[block] = len(blocknum)+1

        yield "    goto = %s # startblock" % self.mklabel(blocknum[start])
        yield "    while True:"
                
        def render_block(block):
            catch_exception = block.exitswitch == c_last_exception
            regular_op = len(block.operations) - catch_exception
            # render all but maybe the last op
            for op in block.operations[:regular_op]:
                for line in self.oper(op, localscope).split("\n"):
                    yield "%s" % line
            # render the last op if it is exception handled
            for op in block.operations[regular_op:]:
                yield "try:"
                for line in self.oper(op, localscope).split("\n"):
                    yield "    %s" % line

            if len(block.exits) == 0:
                if len(block.inputargs) == 2:   # exc_cls, exc_value
                    # exceptional return block
                    exc_cls = self.expr(block.inputargs[0], localscope)
                    exc_val = self.expr(block.inputargs[1], localscope)
                    yield "raise %s(%s, %s)" % (self.nameof(OperationError),
                                                exc_cls, exc_val)
                else:
                    # regular return block
                    retval = self.expr(block.inputargs[0], localscope)
                    yield "return %s" % retval
                return
            elif block.exitswitch is None:
                # single-exit block
                assert len(block.exits) == 1
                for op in self.gen_link(block.exits[0], localscope, blocknum, block):
                    yield "%s" % op
            elif catch_exception:
                # block catching the exceptions raised by its last operation
                # we handle the non-exceptional case first
                link = block.exits[0]
                assert link.exitcase is None
                for op in self.gen_link(link, localscope, blocknum, block):
                    yield "    %s" % op
                # we must catch the exception raised by the last operation,
                # which goes to the last err%d_%d label written above.
                # Since we only have OperationError, we need to select:
                yield "except %s, e:" % (self.nameof(OperationError),)
                yield "    e.normalize_exception(space)"
                q = "if"
                for link in block.exits[1:]:
                    assert issubclass(link.exitcase, py.builtin.BaseException)
                    # Exeption classes come unwrapped in link.exitcase
                    yield "    %s e.match(space, %s):" % (q,
                                            self.nameof(link.exitcase))
                    q = "elif"
                    for op in self.gen_link(link, localscope, blocknum, block, {
                                link.last_exception: 'e.w_type',
                                link.last_exc_value: 'e.w_value'}):
                        yield "        %s" % op
                yield "    else:raise # unhandled case, should not happen"
            else:
                # block ending in a switch on a value
                exits = list(block.exits)
                if len(exits) == 2 and (
                    exits[0].exitcase is False and exits[1].exitcase is True):
                    # order these guys like Python does
                    exits.reverse()
                q = "if"
                for link in exits[:-1]:
                    yield "%s %s == %s:" % (q, self.expr(block.exitswitch,
                                                     localscope),
                                                     link.exitcase)
                    for op in self.gen_link(link, localscope, blocknum, block):
                        yield "    %s" % op
                    q = "elif"
                link = exits[-1]
                yield "else:"
                # debug only, creates lots of fluffy C code
                ##yield "    assert %s == %s" % (self.expr(block.exitswitch,
                ##                                    localscope),
                ##                                    link.exitcase)
                for op in self.gen_link(exits[-1], localscope, blocknum, block):
                    yield "    %s" % op

        cmpop = ('==', 'is') [self.specialize_goto]
        for block in allblocks:
            blockno = blocknum[block]
            yield ""
            yield "        if goto %s %s:" % (cmpop, self.mklabel(blockno))
            for line in render_block(block):
                yield "            %s" % line

# ____________________________________________________________

    RPY_HEADER = '''#!/bin/env python
# -*- coding: LATIN-1 -*-'''

    RPY_SEP = "#*************************************************************"

    RPY_INIT_HEADER = RPY_SEP + '''
#__name__ = %(modname)r
_geninterp_ = True

def init%(modname)s(space):
  """NOT_RPYTHON"""
'''

    RPY_INIT_FOOTER = '''
# entry point: %(entrypointname)s, %(entrypoint)s
if __name__ == "__main__":
    from pypy.objspace.std import StdObjSpace
    from pypy.objspace.std.model import UnwrapError
    space = StdObjSpace()
    init%(modname)s(space)
    ret = space.call(%(entrypoint)s, space.newtuple([]))
    try:
        print space.unwrap(ret)
    except UnwrapError:
        print "cannot unwrap, here the wrapped result:"
        print ret
'''

# _____________________________________________________________________

# implementation of the interface that is finally only
# used: translate_as_module

import py.code
import cStringIO as StringIO

class memfile(object):
    _storage = {}
    def __init__(self, name, mode="r"):
        if mode == "w":
            self._storage[name] = StringIO.StringIO()
        elif mode == "r":
            try:
                data = self._storage[name].getvalue()
            except IndexError:
                f = file(name)
                data = f.read()
                f.close()
            self._storage[name] = StringIO.StringIO(data)
        else:
            raise ValueError, "mode %s not supported" % mode
        self._file = self._storage[name]
    def __getattr__(self, name):
        return getattr(self._file, name)
    def close(self):
        pass

def translate_as_module(sourcetext, filename=None, modname="app2interpexec",
                        do_imports_immediately=False, tmpname=None):
    """ compile sourcetext as a module, translating to interp level.
    The result is the init function that creates the wrapped module dict,
    together with the generated source text.
    This init function needs a space as argument.
    tmpname can be passed for debugging purposes.

    Example:

    initfunc, newsrc = translate_as_module(text)
    from pypy.objspace.std import Space
    space = Space()
    dic = initfunc(space)
    # and now use the members of the dict
    """
    # create something like a module
    if type(sourcetext) is str:
        if filename is None: 
            code = py.code.Source(sourcetext).compile()
        else: 
            code = NiceCompile(filename)(sourcetext)
    else:
        # assume we got an already compiled source
        code = sourcetext
    dic = {'__name__': modname}
    if filename:
        dic['__file__'] = filename

    # XXX allow the app-level code to contain e.g. "import _formatting"
    for pkgdir in pypy.__path__:
        libdir = os.path.join(pkgdir, "lib")
        if os.path.isdir(libdir):
            break
    else:
        raise Exception, "cannot find pypy/lib directory"
    sys.path.insert(0, libdir)
    try:
        if faked_set:
            import __builtin__
            __builtin__.set = fake_set
            __builtin__.frozenset = fake_frozenset
        try:
            exec code in dic
        finally:
            if libdir in sys.path:
                sys.path.remove(libdir)

        entrypoint = dic
        t = TranslationContext(verbose=False, simplifying=True,
                               builtins_can_raise_exceptions=True,
                               list_comprehension_operations=False)
        t.no_annotator_but_do_imports_immediately = do_imports_immediately
        gen = GenRpy(t, entrypoint, modname, dic)

    finally:
        if faked_set:
            del __builtin__.set
            del __builtin__.frozenset

    if tmpname:
        _file = file
    else:
        _file = memfile
        tmpname = 'nada'
    out = _file(tmpname, 'w')
    gen.f = out
    try:
        if faked_set:
            import __builtin__
            __builtin__.set = fake_set
            __builtin__.frozenset = fake_frozenset
        gen.gen_source(tmpname, file=_file)
    finally:
        if faked_set:
            del __builtin__.set
            del __builtin__.frozenset
    out.close()
    f = _file(tmpname)
    newsrc = f.read()
    f.close()
    code = py.code.Source(newsrc).compile()
    dic = {'__name__': modname}
    exec code in dic
    # now we just need to return the init function,
    # which then needs to be called with the space to return the dict.
    return dic['init%s' % modname], newsrc

#___________________________________________________________________

# some testing code

testcode = """
def f(a, b):
    return a + b

def g():
    return f(f(1, 2), f(4, 8))
"""

if __name__ == '__main__':
    res = translate_as_module(testcode, tmpname='/tmp/look.py')
