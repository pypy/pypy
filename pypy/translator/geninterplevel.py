"""
Implementation of a translator from application Python to interpreter level RPython.

The idea is that we can automatically transform app-space implementations
of methods into some equivalent representation at interpreter level.
Then, the RPython to C translation might hopefully spit out some
more efficient code than always interpreting these methods.

Note that the appspace functions are treated as rpythonic, in a sense
that globals are constants, for instance. This definition is not
exact and might change.

Integration of this module will be done half-automatically
using a simple caching mechanism. The generated files are
not meant to be checked into svn, although this currently
still happens.
"""

from __future__ import generators
import autopath, os, sys, exceptions, inspect, types
from pypy.objspace.flow.model import Variable, Constant, SpaceOperation
from pypy.objspace.flow.model import FunctionGraph, Block, Link
from pypy.objspace.flow.model import last_exception, last_exc_value
from pypy.objspace.flow.model import traverse, uniqueitems, checkgraph
from pypy.translator.simplify import remove_direct_loops
from pypy.interpreter.pycode import CO_VARARGS, CO_VARKEYWORDS
from pypy.annotation import model as annmodel
from types import FunctionType, CodeType, ModuleType
from pypy.interpreter.error import OperationError
from pypy.interpreter.argument import Arguments
from pypy.objspace.std.restricted_int import r_int, r_uint

from pypy.translator.translator import Translator
from pypy.objspace.flow import FlowObjSpace

from pypy.interpreter.gateway import app2interp, interp2app

from pypy.tool.sourcetools import render_docstr

from pypy.translator.gensupp import ordered_blocks, UniqueList, builtin_base, \
     c_string, uniquemodulename, C_IDENTIFIER, NameManager

import pypy # __path__
import py.path
# ____________________________________________________________

def eval_helper(self, typename, expr):
    name = self.uniquename("gtype_%s" % typename)
    bltinsname = self.nameof('__builtins__')
    self.initcode.append1(
        'def eval_helper(expr):\n'
        '    import types\n'
        '    dic = space.newdict([(%s, space.w_builtins)])\n'
        '    space.exec_("import types", dic, dic)\n'
        '    return space.eval(expr, dic, dic)' % bltinsname)
    self.initcode.append1('%s = eval_helper(%r)' % (name, expr))
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
        for name in "newtuple newlist newdict newstring".split():
            self.has_listarg[name] = name

        # catching all builtins in advance, to avoid problems
        # with modified builtins
        import __builtin__
        
        class bltinstub:
            def __init__(self, name):
                self.__name__ = name
            def __repr__(self):
                return '<%s>' % self.__name__
            
        self.builtin_ids = dict( [
            (id(value), bltinstub(key))
            for key, value in __builtin__.__dict__.items()
            if callable(value) and type(value) not in [type(Exception), type] ] )
        
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
        if op.opname == "simple_call":
            v = op.args[0]
            space_shortcut = self.try_space_shortcut_for_builtin(v, len(op.args)-1)
            if space_shortcut is not None:
                # space method call
                exv = space_shortcut
                fmt = "%(res)s = %(func)s(%(args)s)"
            else:
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
            return fmt % {"res": self.expr(op.result, localscope),
                          "func": exv,
                          "shape": repr(shape),
                          "data_w": self.arglist(op.args[2:], localscope),
                          'Arg': self.nameof(Arguments) }
        if op.opname in self.has_listarg:
            fmt = "%s = %s([%s])"
        else:
            fmt = "%s = %s(%s)"
        # special case is_true
        wrapped = op.opname != "is_true"
        oper = "space.%s" % op.opname
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
            left.append(self.expr(a2, localscope))
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

    def uniquename(self, basename):
        name = self.namespace.uniquename(basename)
        self.globalobjects.append(name)
        self.globaldecl.append('# global object %s' % (name,))
        return name

    def nameof_NotImplementedType(self, value):
        return "space.w_NotImplemented"

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

    def nameof_module(self, value):
        assert value is os or not hasattr(value, "__file__") or \
               not (value.__file__.endswith('.pyc') or
                    value.__file__.endswith('.py') or
                    value.__file__.endswith('.pyo')), \
               "%r is not a builtin module (probably :)"%value
        name = self.uniquename('mod_%s' % value.__name__)
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
        self.initcode.append1('%s = space.newint(%d)' % (name, value))
        return name

    def nameof_long(self, value):
        # allow short longs only, meaning they
        # must fit into a machine word.
        assert (sys.maxint*2+1)&value==value, "your literal long is too long"
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
        self.initcode.append1('%s = space.wrap(%s) # XXX implement long!' % (name, s))
        return name

    def nameof_float(self, value):
        name = 'gfloat_%s' % value
        name = (name.replace('-', 'minus')
                    .replace('.', 'dot'))
        name = self.uniquename(name)
        self.initcode.append1('%s = space.newfloat(%r)' % (name, value))
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
        # self.initcode.append1('%s = space.newstring(%r)' % (name, value))
        # ick! very unhandy
        self.initcode.append1('%s = space.wrap(%r)' % (name, value))
        return name

    def skipped_function(self, func):
        # debugging only!  Generates a placeholder for missing functions
        # that raises an exception when called.
        name = self.uniquename('gskippedfunc_' + func.__name__)
        self.globaldecl.append('# global decl %s' % (name, ))
        self.initcode.append1('# build func %s' % name)
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

        printable_name = '(%s:%d) %s' % (
            self.trans_funcname(func.func_globals.get('__name__', '?')),
            func.func_code.co_firstlineno,
            func.__name__)
        if self.translator.frozen:
            if func not in self.translator.flowgraphs:
                print "NOT GENERATING", printable_name
                return self.skipped_function(func)
        else:
            if (func.func_doc and
                func.func_doc.lstrip().startswith('NOT_RPYTHON')):
                print "skipped", printable_name
                return self.skipped_function(func)
        name = self.uniquename('gfunc_' + self.trans_funcname(
            namehint + func.__name__))
        f_name = 'f_' + name[6:]
        self.initcode.append1('from pypy.interpreter import gateway')
        self.initcode.append1('%s = space.wrap(gateway.interp2app(%s, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))' % (name, f_name))
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

    def should_translate_attr(self, pbc, attr):
        ann = self.translator.annotator
        if ann is None:
            ignore = getattr(pbc.__class__, 'NOT_RPYTHON_ATTRIBUTES', [])
            if attr in ignore:
                return False
            else:
                return "probably"   # True
        classdef = ann.getuserclasses().get(pbc.__class__)
        if classdef and classdef.about_attribute(attr) is not None:
            return True
        return False

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
                        print >> sys.stderr, "Problem while generating %s of %r" % (
                                name, instance)
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
        
    def try_space_shortcut_for_builtin(self, v, nargs):
        if isinstance(v, Constant) and id(v.value) in self.builtin_ids:
            name = self.builtin_ids[id(v.value)].__name__
            if hasattr(self.space, name):
                if self.space_arities().get(name, -1) == nargs:
                    return "space.%s" % name
        return None
        
    def nameof_builtin_function_or_method(self, func):
        if func.__self__ is None:
            # builtin function
            if id(func) in self.builtin_ids:
                func = self.builtin_ids[id(func)]
                return "(space.builtin.get(space.str_w(%s)))" % self.nameof(func.__name__)
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
            if modname == '__builtin__':
                # be lazy
                return "(space.builtin.get(space.str_w(%s)))" % self.nameof(func.__name__)
            elif modname == 'sys':
                # be lazy
                return "(space.sys.get(space.str_w(%s)))" % self.nameof(func.__name__)                
            else:
                print ("WARNING: accessing builtin modules different from sys or __builtin__"
                       " is likely producing non-sense: %s %s" % (module.__name__, func.__name__))
                name = self.uniquename('gbltin_' + func.__name__)
                self.initcode.append1('%s = space.getattr(%s, %s)' % (
                    name, self.nameof(module), self.nameof(func.__name__)))
        else:
            # builtin (bound) method
            name = self.uniquename('gbltinmethod_' + func.__name__)
            self.initcode.append1('%s = space.getattr(%s, %s)' % (
                name, self.nameof(func.__self__), self.nameof(func.__name__)))
        return name

    def nameof_classobj(self, cls):
        printable_name = cls.__name__
        if cls.__doc__ and cls.__doc__.lstrip().startswith('NOT_RPYTHON'):
            #raise Exception, "%r should never be reached" % (cls,)
            print "skipped class", printable_name
            return self.skipped_class(cls)

        metaclass = "space.w_type"
        name = self.uniquename('gcls_' + cls.__name__)

        if issubclass(cls, Exception):
            if cls.__module__ == 'exceptions':
                # exception are defined on the space
                return 'space.w_%s' % cls.__name__

        if not isinstance(cls, type):
            assert type(cls) is type(Exception)
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
                               '__weakref__', '__metaclass__', '__slots__','__new__']:
                        continue

                # redirect value through class interface, in order to
                # get methods instead of functions.
                value = getattr(cls, key)

                if isinstance(value, staticmethod) and value.__get__(1) not in self.translator.flowgraphs and self.translator.frozen:
                    print "skipped staticmethod:", value
                    continue
                if isinstance(value, FunctionType) and value not in self.translator.flowgraphs and self.translator.frozen:
                    print "skipped function:", value
                    continue
                    
                yield 'space.setattr(%s, %s, %s)' % (
                    name, self.nameof(key), self.nameof(value))

        baseargs = ", ".join(basenames)
        self.initcode.append('_dic = space.newdict([])')
        for key, value in cls.__dict__.items():
            if key.startswith('__'):
                if key in ['__module__', '__metaclass__', '__slots__','__new__']:
                    keyname = self.nameof(key)
                    valname = self.nameof(value)
                    self.initcode.append("space.setitem(_dic, %s, %s)" % (
                        keyname, valname))

        if cls.__doc__ is not None:
            sdoc = self.nameof("__doc__")
            docstr = render_docstr(cls, "_doc = space.wrap(", ")")
            self.initcode.append1((docstr,)) # not splitted
            self.initcode.append("space.setitem(_dic, %s, _doc)" % (
                self.nameof("__doc__"),))
        self.initcode.append1('_bases = space.newtuple([%(bases)s])\n'
                             '_args = space.newtuple([%(name)s, _bases, _dic])\n'
                             '%(klass)s = space.call(%(meta)s, _args)'
                             % {"bases": baseargs,
                                "klass": name,
                                "name" : self.nameof(cls.__name__),
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
        type(Exception()): 'space.wrap(types.InstanceType)',
        type:   'space.w_type',
        complex:'space.wrap(types.ComplexType)',
        unicode:'space.w_unicode',
        file:   (eval_helper, 'file', 'file'),
        type(None): (eval_helper, 'NoneType', 'types.NoneType'),
        CodeType: (eval_helper, 'code', 'types.CodeType'),
        ModuleType: (eval_helper, 'ModuleType', 'types.ModuleType'),
        xrange: (eval_helper, 'xrange', 'types.XRangeType'),

        ##r_int:  'space.w_int',
        ##r_uint: 'space.w_int',

        type(len): (eval_helper, 'FunctionType', 'types.FunctionType'),
        # type 'method_descriptor':
        # XXX small problem here:
        # XXX with space.eval, we get <W_TypeObject(method)>
        # XXX but with wrap, we get <W_TypeObject(instancemethod)>
        type(list.append): (eval_helper, "method_descriptor", "list.append"),
        # type 'wrapper_descriptor':
        type(type(None).__repr__): (eval_helper, "wrapper_descriptor",
                                    "type(type(None).__repr__)"),
        # type 'getset_descriptor':
        # XXX here we get <W_TypeObject(FakeDescriptor)>,
        # while eval gives us <W_TypeObject(GetSetProperty)>
        type(type.__dict__['__dict__']): (eval_helper, "getset_descriptor", '\
            ' "type(type.__dict__[\'__dict__\'])"),
        # type 'member_descriptor':
        # XXX this does not work in eval!
        # type(type.__dict__['__basicsize__']): "cannot eval type(type.__dict__['__basicsize__'])",
        # XXX there seems to be no working support for member descriptors ???
        type(types.GeneratorType.gi_frame):
            (eval_helper, "member_descriptor", 'type(types.GeneratorType.gi_frame)'),
        types.ClassType: 'space.w_classobj',
    }

    def nameof_type(self, cls):
        if cls in self.typename_mapping:
            ret = self.typename_mapping[cls]
            if type(ret) is tuple:
                ret = ret[0](self, ret[1], ret[2])
            return ret
        assert cls.__module__ != '__builtin__', (
            "built-in class %r not found in typename_mapping "
            "while compiling %s" % (cls, self.currentfunc.__name__))
        return self.nameof_classobj(cls)

    def nameof_tuple(self, tup):
        name = self.uniquename('g%dtuple' % len(tup))
        args = [self.nameof(x) for x in tup]
        args = ', '.join(args)
        self.initcode.append1('%s = space.newtuple([%s])' % (name, args))
        return name

    def nameof_list(self, lis):
        name = self.uniquename('g%dlist' % len(lis))
        def initlist():
            for i in range(len(lis)):
                item = self.nameof(lis[i])
                yield 'space.setitem(%s, %s, %s);' % (
                    name, self.nameof(i), item)
        self.initcode.append1('%s = space.newlist([space.w_None])' % (name,))
        self.initcode.append1('%s = space.mul(%s, %s)' % (name, name, self.nameof(len(lis))))
        self.later(initlist())
        return name

    def nameof_dict(self, dic):
        assert dic is not __builtins__
        assert '__builtins__' not in dic, 'Seems to be the globals of %s' % (
            dic.get('__name__', '?'),)
        name = self.uniquename('g%ddict' % len(dic))
        def initdict():
            for k in dic:
                yield ('space.setitem(%s, %s, %s)'%(
                            name, self.nameof(k), self.nameof(dic[k])))
        self.initcode.append1('%s = space.newdict([])' % (name,))
        self.later(initdict())
        return name

    # strange prebuilt instances below, don't look too closely
    # XXX oh well.
    def nameof_member_descriptor(self, md):
        name = self.uniquename('gdescriptor_%s_%s' % (
            md.__objclass__.__name__, md.__name__))
        cls = self.nameof(md.__objclass__)
        # do I need to take the dict and then getitem???
        self.initcode.append1('%s = space.getattr(%s, %s)' %
                                (name, cls, self.nameof(md.__name__)))
        return name
    nameof_getset_descriptor  = nameof_member_descriptor
    nameof_method_descriptor  = nameof_member_descriptor
    nameof_wrapper_descriptor = nameof_member_descriptor

    def nameof_file(self, fil):
        if fil is sys.stdin:
            return 'PySys_GetObject("stdin")'
        if fil is sys.stdout:
            return 'PySys_GetObject("stdout")'
        if fil is sys.stderr:
            return 'PySys_GetObject("stderr")'
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
            file(target, "w").write(file(source).read())

        def order_sections(fname):
            sep = "\n##SECTION##\n"
            txt = file(fname).read()
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
            file(fname, "w").write(txt)

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
        info = {
            'modname': self.modname,
             # the side-effects of this is kick-start the process
            'entrypoint': self.nameof(self.entrypoint),
            }
        # header
        print >> f, self.RPY_HEADER
        print >> f

        # doc
        if self.moddict and self.moddict.get("__doc__"):
            doc = self.moddict["__doc__"]
            print >> f, render_docstr(doc)
            print >> f
            # make sure it is not rendered again
            key = Constant(doc).key
            self.rpynames[key] = "__doc__"
            self.initcode.append1("__doc__ = space.wrap(globals()['__doc__'])")

        # header """def initmodule(space):"""
        print >> f, self.RPY_INIT_HEADER % info

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
        body = list(self.rpyfunction_body(func, localscope))
        name_of_defaults = [self.nameof(x, debug=('Default argument of', func))
                            for x in (func.func_defaults or ())]
        self.gen_global_declarations()

        # print header
        docstr = render_docstr(func, "    ")
        cname = self.nameof(func)
        assert cname.startswith('gfunc_')
        f_name = 'f_' + cname[6:]

        # collect all the local variables
        graph = self.translator.getflowgraph(func)
        localslst = []
        def visit(node):
            if isinstance(node, Block):
                localslst.extend(node.getvariables())
        traverse(visit, graph)
        localnames = [self.expr(a, localscope) for a in uniqueitems(localslst)]

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

        print >> f, '  def %s(space, __args__):' % (name,)
        if docstr is not None:
            print >> f, docstr
            print >> f
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

        fast_locals = [arg for arg in localnames if arg not in fast_set]
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

        if not self.translator.frozen:
            # this is only to keep the RAM consumption under control
            del self.translator.flowgraphs[func]
            Variable.instances.clear()

    def rpyfunction_body(self, func, localscope):
        try:
            graph = self.translator.getflowgraph(func)
        except Exception, e:
            print 20*"*", e
            print func
            raise
        # not needed, we use tuple assignment!
        # remove_direct_loops(graph)
        checkgraph(graph)

        allblocks = []
        
        f = self.f
        t = self.translator
        #t.simplify(func)
        graph = t.getflowgraph(func)


        start = graph.startblock
        allblocks = ordered_blocks(graph)
        nblocks = len(allblocks)

        blocknum = {}
        for block in allblocks:
            blocknum[block] = len(blocknum)+1

        yield "    goto = %s # startblock" % self.mklabel(blocknum[start])
        yield "    while True:"
                
        def render_block(block):
            catch_exception = block.exitswitch == Constant(last_exception)
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
                yield "    e.w_type, e.w_value, _ign = space.unpacktuple("
                yield "        space.normalize_exception(e.w_type, e.w_value, space.w_None), 3)"
                q = "if"
                for link in block.exits[1:]:
                    assert issubclass(link.exitcase, Exception)
                    # Exeption classes come unwrapped in link.exitcase
                    yield "    %s space.is_true(space.issubtype(e.w_type, %s)):" % (q,
                                            self.nameof(link.exitcase))
                    q = "elif"
                    for op in self.gen_link(link, localscope, blocknum, block, {
                                Constant(last_exception): 'e.w_type',
                                Constant(last_exc_value): 'e.w_value'}):
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
                yield "    assert %s == %s" % (self.expr(block.exitswitch,
                                                    localscope),
                                                    link.exitcase)
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

## this should go into some test file

def somefunc(arg):
    pass

# XXX problem with local functions:
def randint(low, high, seed = 1234567): # really not a real random
    return (seed % (high-low)) + low

def small_loop():
    ''' this is a test for small loops.
    How would we generate small blocks which call
    each other? Hey, and """ is a doc string test """
    '''
    #from random import randint
    # does not work. flowspace really complains on random.
    # XXX we also seem to have problems with local functions
    #def randint(low, high, seed = 1234567): # really not a real random
    #    return (seed % (high-low)) + low
                
    for i in range(10000):
        r = randint(0, 10000)
        if r > 9000:
            return r

def f(a,b):
##    print "start"
    a = []
    a.append(3)
    for i in range(3):
        pass#print i
    if a > b:
        try:
            if b == 123:
                raise ValueError
            elif b == 321:
                raise IndexError
            return 123
        except ValueError:
            raise TypeError
    else:
        dummy = somefunc(23)
        return 42

class TestClass:pass

def ff(a, b, c=3,*rest):
    """ this is
    some
    docstring
"""
    try:
        try:
            if rest:
                raise SystemError, 42
            return a+b
        finally:
            a = 7
            if rest:
                return len(rest),c
    except TypeError:
        print "eek"

glob = 100
def fff():
    global glob
    return 42+glob

def app_mod__String_ANY(format, values):
    import _formatting
    if isinstance(values, tuple):
        return _formatting.format(format, values, None)
    else:
        if hasattr(values, 'keys'):
            return _formatting.format(format, (values,), values)
        else:
            return _formatting.format(format, (values,), None)

def app_str_decode__String_ANY_ANY(str, encoding=None, errors=None):
    if encoding is None and errors is None:
        return unicode(str)
    elif errors is None:
        return unicode(str, encoding)
    else:
        return unicode(str, encoding, errors)
        

def test_md5():
    #import md5
    # how do I avoid the builtin module?
    from pypy.appspace import md5
    digest = md5.new("hello").hexdigest()
    return digest

def test_mod():
    return app_mod__String_ANY("-%s-", ["hallo"])

def test_join():
    return " ".join(["hi", "there"])

# cannot nest local classes, yet
# this appears to be a problem in flow space.
class AnIterClass(object):
    def __init__(self):
        self.lis = [c for c in "test"]
    def next(self):
        if self.lis:
            return self.lis.pop()
        raise StopIteration
    def __iter__(self):
        return self
    
def test_iter():
    res = []
    for i in "hallo":
        res.append(i)
    for i in AnIterClass():
        res.append(i)
    return res

def test_loop():
    res = []
    i = 0
    while 1:
        i += 1
        res.append(i)
        if i == 42:
            break
        res.append(-i)
    return res

def test_exc(a=5):
    try:
        b = 0
        return a / b
    except ZeroDivisionError:
        return 42

def test_strutil():
    from pypy.objspace.std import strutil
    return (strutil.string_to_int("42"),
            strutil.string_to_long("12345678901234567890"))

def test_struct():
    from pypy.appspace import struct
    import struct as stru
    res1 = stru.pack('f',1.23), struct.pack('f',1.23)
    res2 = struct.unpack('f', struct.pack('f',1.23))
    return res1, res2

def exceptions_helper():
    import pypy
    prefix = os.path.dirname(pypy.__file__)
    libdir = os.path.join(prefix, "lib")
    fname = "_exceptions.py"
    fpath = os.path.join(libdir, fname)
    dic = {"__name__": "exceptions"}
    execfile(fpath, dic)
    del dic["__builtins__"]
    def test_exceptions():
        """ enumerate all exceptions """
        return dic.keys()
        #return [thing for thing in _exceptions.__dict__.values()]
    return dic, test_exceptions

def make_class_instance_helper():
    import pypy
    prefix = os.path.dirname(pypy.__file__)
    libdir = os.path.join(prefix, "lib")
    hold = sys.path
    sys.path.insert(0, libdir)
    import _classobj
    sys.path = hold
    def make_class_instance():
        return _classobj.classobj, _classobj.instance
    return None, make_class_instance

def test_complex():
    return 1j

def test_NoneType():
    return types.NoneType
    
def all_entries():
    res = [func() for func in entrypoints[:-1]]
    return res

entrypoints = (small_loop,
                lambda: f(2, 3),
                lambda: ff(2, 3, 5),
                fff,
                lambda: app_str_decode__String_ANY_ANY("hugo"),
                test_mod,
                test_md5,
                test_join,
                test_iter,
                test_loop,
                test_exc,
                test_strutil,
                test_struct,
                exceptions_helper,
                make_class_instance_helper,
                test_complex,
                test_NoneType,
                all_entries)
entrypoint = entrypoints[-2]

if False and __name__ == "__main__":
    # XXX TODO:
    # extract certain stuff like a general module maker
    # and put this into tools/compile_exceptions, maybe???
    dic, entrypoint = exceptions_helper()
    t = Translator(None, verbose=False, simplifying=True,
                   builtins_can_raise_exceptions=True,
                   do_imports_immediately=False)
    gen = GenRpy(t, entrypoint)
    gen.moddict = dic
    gen.gen_source('/tmp/look.py')
    
    _oldcodetogointotestcases = '''
    import os, sys
    from pypy.interpreter import autopath
    srcdir = os.path.dirname(autopath.pypydir)
    appdir = os.path.join(autopath.pypydir, 'appspace')

    if appdir not in sys.path:
        sys.path.insert(0, appdir)

    dic = None
    if entrypoint.__name__.endswith("_helper"):
        dic, entrypoint = entrypoint()
    t = Translator(entrypoint, verbose=False, simplifying=True, builtins_can_raise_exceptions=True)
    gen = GenRpy(t)
    gen.use_fast_call = True
    if dic: gen.moddict = dic
    import pypy.appspace.generated as tmp
    pth = os.path.dirname(tmp.__file__)
    ftmpname = "/tmp/look.py"
    fname = os.path.join(pth, gen.modname+".py")
    gen.gen_source(fname, ftmpname)
    '''

def crazy_test():
    """ this thingy is generating the whole interpreter in itself"""
    dic = {"__builtins__": __builtins__, "__name__": "__main__"}
    execfile("/tmp/look.py", dic)

    entrypoint = dic[gen.entrypoint]
    def test():
        entrypoint()
        
    t = Translator(test, verbose=False, simplifying=True,
                   builtins_can_raise_exceptions=True,
                   do_imports_immediately=False)
    gen2 = GenRpy(t)
    gen2.gen_source("/tmp/look2.py")


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
                data = file(name).read()
            self._storage[name] = StringIO.StringIO(data)
        else:
            raise ValueError, "mode %s not supported" % mode
        self._file = self._storage[name]
    def __getattr__(self, name):
        return getattr(self._file, name)
    def close(self):
        pass

def translate_as_module(sourcetext, filename=None, modname="app2interpexec", tmpname=None):
    """ compile sourcetext as a module, translating to interp level.
    The result is the init function that creates the wrapped module dict.
    This init function needs a space as argument.
    tmpname can be passed for debugging purposes.

    Example:

    initfunc = translate_as_module(text)
    from pypy.objspace.stdimport Space
    space = Space()
    dic = ini(space)
    # and now use the members of the dict
    """
    # create something like a module
    if filename is None: 
        code = py.code.Source(sourcetext).compile()
    else: 
        code = compile(sourcetext, filename, 'exec') 
    dic = {'__name__': modname}
    exec code in dic
    del dic['__builtins__']
    entrypoint = dic
    t = Translator(None, verbose=False, simplifying=True,
                   builtins_can_raise_exceptions=True,
                   do_imports_immediately=False)
    gen = GenRpy(t, entrypoint, modname, dic)
    if tmpname:
        _file = file
    else:
        _file = memfile
        tmpname = "nada"
    out = _file(tmpname, 'w')
    gen.f = out
    gen.gen_source(tmpname, file=_file)
    out.close()
    newsrc = _file(tmpname).read()
    code = py.code.Source(newsrc).compile()
    dic = {'__name__': modname}
    exec code in dic
    # now we just need to return the init function,
    # which then needs to be called with the space to return the dict.
    return dic['init%s' % modname]

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
