"""
Implementation of a translator from application Python to interpreter level RPython.

The idea is that we can automatically transform app-space implementations
of methods into some equivalent representation at interpreter level.
Then, the RPython to C translation might hopefully spit out some
more efficient code than always interpreting these methods.

Note that the appspace functions are treated as rpythonic, in a sense
that globals are constants, for instance. This definition is not
exact and might change.

This module appears to be already quite usable.
But I need to ask how we want to integrate it.

XXX open questions:
- do we wantamoduleperapp-spaceoperation?
- do we want to auto-generate stuff?
- do we want to create code that is more similar to the app code?
- do we want to create specialized code for constants?
- do we want to use small tail-functions instead of goto?
- do we want to inline small functions?
- do we want to translate non-rpythonic code as well?
"""

from __future__ import generators
import autopath, os, sys, exceptions, inspect
from pypy.objspace.flow.model import Variable, Constant, SpaceOperation
from pypy.objspace.flow.model import FunctionGraph, Block, Link
from pypy.objspace.flow.model import last_exception, last_exc_value
from pypy.objspace.flow.model import traverse, uniqueitems, checkgraph
from pypy.translator.simplify import remove_direct_loops
from pypy.interpreter.pycode import CO_VARARGS
from pypy.annotation import model as annmodel
from types import FunctionType, CodeType
from pypy.interpreter.error import OperationError
from pypy.objspace.std.restricted_int import r_int, r_uint

from pypy.translator.translator import Translator
from pypy.objspace.std import StdObjSpace
from pypy.objspace.flow import FlowObjSpace

from pypy.interpreter.gateway import app2interp, interp2app

from pypy.tool.sourcetools import render_docstr

# ____________________________________________________________

def c_string(s):
    return '"%s"' % (s.replace('\\', '\\\\').replace('"', '\"'),)

def uniquemodulename(name, SEEN={}):
    # never reuse the same module name within a Python session!
    i = 0
    while True:
        i += 1
        result = '%s_%d' % (name, i)
        if result not in SEEN:
            SEEN[result] = True
            return result

def ordered_blocks(graph):
    # collect all blocks
    allblocks = []
    def visit(block):
        if isinstance(block, Block):
            # first we order by offset in the code string
            if block.operations:
                ofs = block.operations[0].offset
            else:
                ofs = sys.maxint
            # then we order by input variable name or value
            if block.inputargs:
                txt = str(block.inputargs[0])
            else:
                txt = "dummy"
            allblocks.append((ofs, txt, block))
    traverse(visit, graph)
    allblocks.sort()
    #for ofs, txt, block in allblocks:
    #    print ofs, txt, block
    return [block for ofs, txt, block in allblocks]

class UniqueList(list):
    def __init__(self, *args, **kwds):
        list.__init__(self, *args, **kwds)
        self.dic = {}

    def append(self, arg):
        try:
            self.dic[arg]
        except KeyError:
            self.dic[arg] = 1
            list.append(self, arg)
        except TypeError: # not hashable
            if arg not in self:
                list.append(self, arg)
    def appendnew(self, arg):
        "always append"
        list.append(self, arg)
        
class GenRpy:
    def __init__(self, translator, modname=None):
        self.translator = translator
        self.modname = self.trans_funcname(modname or
                        uniquemodulename(translator.functions[0].__name__))
        self.moddict = None # the dict if we translate a module
        self.rpynames = {Constant(None).key:  'space.w_None',
                         Constant(False).key: 'space.w_False',
                         Constant(True).key:  'space.w_True',
                       }
        
        self.seennames = {}
        u = UniqueList
        self.initcode = u()    # list of lines for the module's initxxx()
        self.latercode = u()   # list of generators generating extra lines
                               #   for later in initxxx() -- for recursive
                               #   objects
        self.globaldecl = []
        self.globalobjects = []
        self.pendingfunctions = []
        self.currentfunc = None
        self.debugstack = ()  # linked list of nested nameof()

        # special constructors:
        self.has_listarg = {}
        for name in "newtuple newlist newdict newstring".split():
            self.has_listarg[name] = name

        self.space = FlowObjSpace() # for introspection
        
        self.use_fast_call = False        
        
    def expr(self, v, localnames, wrapped = True):
        if isinstance(v, Variable):
            n = v.name
            if n.startswith("v") and n[1:].isdigit():
                ret = localnames.get(v.name)
                if not ret:
                    if wrapped:
                        localnames[v.name] = ret = "w_%d" % len(localnames)
                    else:
                        localnames[v.name] = ret = "v%d" % len(localnames)
                return ret
            scorepos = n.rfind("_")
            if scorepos >= 0 and n[scorepos+1:].isdigit():
                name = n[:scorepos]
                ret = localnames.get(v.name)
                if not ret:
                    if wrapped:
                        fmt = "w_%s_%d"
                    else:
                        fmt = "%s_%d"
                    localnames[v.name] = ret = fmt % (name, len(localnames))
                return ret
        elif isinstance(v, Constant):
            return self.nameof(v.value,
                               debug=('Constant in the graph of', self.currentfunc))
        else:
            raise TypeError, "expr(%r)" % (v,)

    def arglist(self, args, localnames):
        res = [self.expr(arg, localnames) for arg in args]
        return ", ".join(res)

    def oper(self, op, localnames):
        if op.opname == "simple_call":
            v = op.args[0]
            exv = self.expr(v, localnames)
            if exv.startswith("space.") and not exv.startswith("space.w_"):
                # it is a space method
                fmt = "%(res)s = %(func)s(%(args)s)"
            else:
                # default for a spacecall:
                fmt = ("_tup = space.newtuple([%(args)s])\n"
                        "%(res)s = space.call(%(func)s, _tup)")
                # see if we can optimize for a fast call.
                # we just do the very simple ones.
                if self.use_fast_call and (isinstance(v, Constant)
                                           and exv.startswith('gfunc_')):
                    func = v.value
                    if (not func.func_code.co_flags & CO_VARARGS) and (
                        func.func_defaults is None):
                        fmt = "%(res)s = fastf_%(func)s(space, %(args)s)"
                        exv = exv[6:]
            return fmt % {"res" : self.expr(op.result, localnames),
                          "func": exv,
                          "args": self.arglist(op.args[1:], localnames) }
        if op.opname in self.has_listarg:
            fmt = "%s = %s([%s])"
        else:
            fmt = "%s = %s(%s)"
        # special case is_true
        wrapped = op.opname != "is_true"
        oper = "space.%s" % op.opname
        return fmt % (self.expr(op.result, localnames, wrapped), oper,
                      self.arglist(op.args, localnames))

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

    def gen_link(self, link, localvars, blocknum, block, linklocalvars=None):
        "Generate the code to jump across the given Link."
        linklocalvars = linklocalvars or {}
        left, right = [], []
        for a1, a2 in zip(link.args, link.target.inputargs):
            if a1 in linklocalvars:
                src = linklocalvars[a1]
            else:
                src = self.expr(a1, localvars)
            left.append(self.expr(a2, localvars))
            right.append(src)
        txt = "%s = %s" % (", ".join(left), ", ".join(right))
        if len(txt) <= 65: # arbitrary
            yield txt
        else:
            for line in self.large_assignment(left, right):
                yield line
        goto = blocknum[link.target]
        yield 'goto = %d' % goto
        if goto <= blocknum[block]:
            yield 'continue'

    def nameof(self, obj, debug=None, namehint=None):
        key = Constant(obj).key
        try:
            return self.rpynames[key]
        except KeyError:
            if debug:
                stackentry = debug, obj
            else:
                stackentry = obj
            self.debugstack = (self.debugstack, stackentry)
            if (type(obj).__module__ != '__builtin__' and
                not isinstance(obj, type)):   # skip user-defined metaclasses
                # assume it's a user defined thingy
                name = self.nameof_instance(obj)
            else:
                for cls in type(obj).__mro__:
                    meth = getattr(self,
                                   'nameof_' + cls.__name__.replace(' ', ''),
                                   None)
                    if meth:
                        break
                else:
                    raise Exception, "nameof(%r)" % (obj,)

                code=meth.im_func.func_code
                if namehint and 'namehint' in code.co_varnames[:code.co_argcount]:
                    name = meth(obj, namehint=namehint)
                else:
                    name = meth(obj)
            self.debugstack, x = self.debugstack
            assert x is stackentry
            self.rpynames[key] = name
            return name

    def uniquename(self, basename):
        basename = basename.translate(C_IDENTIFIER)
        n = self.seennames.get(basename, 0)
        self.seennames[basename] = n+1
        if n == 0:
            self.globalobjects.append(basename)
            self.globaldecl.append('# global object %s' % (basename,))
            return basename
        else:
            return self.uniquename('%s_%d' % (basename, n))

    def uniquelocalname(self, basename, seennames):
        basename = basename.translate(C_IDENTIFIER)
        n = seennames.get(basename, 0)
        seennames[basename] = n+1
        if n == 0:
            return basename
        else:
            return self.uniquelocalname('%s_%d' % (basename, n), seennames)

    def nameof_object(self, value):
        if type(value) is not object:
            #raise Exception, "nameof(%r) in %r" % (value, self.currentfunc)
            name = self.uniquename('g_unknown_%r' % value)
            self.initcode.append('# cannot build %s as %r' % (name, object))
            return name
        name = self.uniquename('g_object')
        self.initcode.append('m.%s = object()'%name)
        return name

    def nameof_module(self, value):
        assert value is os or not hasattr(value, "__file__") or \
               not (value.__file__.endswith('.pyc') or
                    value.__file__.endswith('.py') or
                    value.__file__.endswith('.pyo')), \
               "%r is not a builtin module (probably :)"%value
        name = self.uniquename('mod_%s'%value.__name__)
        self.initcode.append('import %s as _tmp' % value.__name__)
        self.initcode.append('m.%s = space.wrap(_tmp)' % (name))
        return name
        

    def nameof_int(self, value):
        if value >= 0:
            name = 'gi_%d' % value
        else:
            # make sure that the type ident is completely described by
            # the prefixbefore the initial '_' for easy postprocessing
            name = 'gi_minus_%d' % abs(value)
        name = self.uniquename(name)
        self.initcode.append('m.%s = space.newint(%d)' % (name, value))
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
        self.initcode.append('m.%s = space.wrap(%s) # XXX implement long!' % (name, s))
        return name

    def nameof_float(self, value):
        name = 'gfloat_%s' % value
        name = (name.replace('-', 'minus')
                    .replace('.', 'dot'))
        name = self.uniquename(name)
        self.initcode.append('m.%s = space.newfloat(%r)' % (name, value))
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
        # self.initcode.append('m.%s = space.newstring(%r)' % (name, value))
        # ick! very unhandy
        self.initcode.append('m.%s = space.wrap(%r)' % (name, value))
        return name

    def skipped_function(self, func):
        # debugging only!  Generates a placeholder for missing functions
        # that raises an exception when called.
        name = self.uniquename('gskippedfunc_' + func.__name__)
        self.globaldecl.append('# global decl %s' % (name, ))
        self.initcode.append('# build func %s' % name)
        return name

    def trans_funcname(self, s):
        return s.translate(C_IDENTIFIER)

    def nameof_function(self, func, namehint=''):
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
        self.initcode.append('from pypy.interpreter.gateway import interp2app')
        self.initcode.append('m.%s = space.wrap(interp2app(%s))' % (name, f_name))
        self.pendingfunctions.append(func)
        return name

    def nameof_staticmethod(self, sm):
        # XXX XXX XXXX
        func = sm.__get__(42.5)
        name = self.uniquename('gsm_' + func.__name__)
        functionname = self.nameof(func)
        self.initcode.append('m.%s = space.wrap(%s)' % (name, functionname))
        return name

    def nameof_instancemethod(self, meth):
        if meth.im_self is None:
            # no error checking here
            return self.nameof(meth.im_func, namehint="%s_" % meth.im_class.__name__)
        else:
            ob = self.nameof(meth.im_self)
            func = self.nameof(meth.im_func)
            typ = self.nameof(meth.im_class)
            name = self.uniquename('gmeth_'+meth.im_func.__name__)
            self.initcode.append(
                '%s = space.getattr(%s, %s)'%(name, ob, func))
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
        self.latercode.append((gen, self.debugstack))

    def nameof_instance(self, instance):
        name = self.uniquename('ginst_' + instance.__class__.__name__)
        cls = self.nameof(instance.__class__)
        def initinstance():
            content = instance.__dict__.items()
            content.sort()
            for key, value in content:
                if self.should_translate_attr(instance, key):
                    try:
                            yield 'space.setattr(%s, %s, %s)' % (
                                name, self.nameof(key), self.nameof(value))
                    except:
                        print >>sys.stderr, "Problem while generating %s of %r" % (
                                name, instance)
                        raise
        if isinstance(instance, Exception):
            # special-case for exception instances: wrap them directly
            self.initcode.append('_ins = %s()\n'
                                 'm.%s = space.wrap(_ins)' % (
                instance.__class__.__name__, name))
        else:
            # this seems to hardly work with the faked stuff
            self.initcode.append('from types import InstanceType')
            self.initcode.append('w_InstanceType = space.wrap(InstanceType)')
            self.initcode.append('_tup = space.newtuple([%s])\n'
                                 'm.%s = space.call(w_InstanceType, _tup)' % (
                cls, name))
        self.later(initinstance())
        return name

    def nameof_builtin_function_or_method(self, func):
        if func.__self__ is None:
            # builtin function
            if hasattr(self.space, func.__name__):
                return "space.%s" % func.__name__
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
                self.initcode.append('m.%s = space.getattr(space.w_builtin, %s)'% (
                    name, self.nameof(func.__name__)))
            else:
                self.initcode.append('m.%s = space.getattr(%s, %s)' % (
                    name, self.nameof(module), self.nameof(func.__name__)))
        else:
            # builtin (bound) method
            name = self.uniquename('gbltinmethod_' + func.__name__)
            self.initcode.append('m.%s = space.getattr(%s, %s)' % (
                name, self.nameof(func.__self__), self.nameof(func.__name__)))
        return name

    def nameof_classobj(self, cls):
        if cls.__doc__ and cls.__doc__.lstrip().startswith('NOT_RPYTHON'):
            raise Exception, "%r should never be reached" % (cls,)

        metaclass = "space.w_type"
        name = self.uniquename('gcls_' + cls.__name__)
        if issubclass(cls, Exception):
            if cls.__module__ == 'exceptions':
                if hasattr(self.space, "w_%s" % cls.__name__):
                    return 'space.w_%s'%cls.__name__
                else:
                    self.initcode.append('m.%s = space.wrap(%s)' % (
                                         name, cls.__name__))
                    return name
            #else:
            #    # exceptions must be old-style classes (grr!)
            #    metaclass = "&PyClass_Type"
        # For the moment, use old-style classes exactly when the
        # pypy source uses old-style classes, to avoid strange problems.
        if not isinstance(cls, type):
            assert type(cls) is type(Exception)
            # self.initcode.append("import types\n"
            #                      "m.classtype = space.wrap(types.ClassType)\n")
            # metaclass = "m.classtype"
            # XXX I cannot instantiate these.
            # XXX using type instead, since we still inherit from exception
            # XXX what is the future of classes in pypy?

        basenames = [self.nameof(base) for base in cls.__bases__]
        def initclassobj():
            content = cls.__dict__.items()
            content.sort()
            for key, value in content:
                if key.startswith('__'):
                    if key in ['__module__', '__doc__', '__dict__',
                               '__weakref__', '__repr__', '__metaclass__']:
                        continue
                    # XXX some __NAMES__ are important... nicer solution sought
                    #raise Exception, "unexpected name %r in class %s"%(key, cls)

                # redirect value through class interface, in order to
                # get methods instead of functions.
                value = getattr(cls, key)

                if isinstance(value, staticmethod) and value.__get__(1) not in self.translator.flowgraphs and self.translator.frozen:
                    print "skipped staticmethod:", value
                    continue
                if isinstance(value, FunctionType) and value not in self.translator.flowgraphs and self.translator.frozen:
                    print "skippedfunction:", value
                    continue
                    
                yield 'space.setattr(%s, %s, %s)' % (
                    name, self.nameof(key), self.nameof(value))

        baseargs = ", ".join(basenames)
        self.initcode.appendnew('_dic = space.newdict([])')
        for key, value in cls.__dict__.items():
            if key.startswith('__'):
                if key in ['__module__', '__metaclass__']:
                    keyname = self.nameof(key)
                    valname = self.nameof(value)
                    self.initcode.appendnew("space.setitem(_dic, %s, %s)" % (
                        keyname, valname))

        if cls.__doc__ is not None:
            sdoc = self.nameof("__doc__")
            lines = list(render_docstr(cls, "_doc = space.wrap(", ")"))
            self.initcode.extend(lines)
            self.initcode.appendnew("space.setitem(_dic, %s, _doc)" % (
                self.nameof("__doc__"),))
        self.initcode.append('_bases = space.newtuple([%(bases)s])\n'
                             '_args = space.newtuple([%(name)s, _bases, _dic])\n'
                             'm.%(klass)s = space.call(%(meta)s, _args)'
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
        type(Exception()): 'space.wrap(types.InstanceType)',
        type:   'space.w_type',
        complex:'space.wrap(types.ComplexType)',
        unicode:'space.w_unicode',
        file:   'space.wrap(file)',
        type(None): 'space.wrap(types.NoneType)',
        CodeType: 'space.wrap(types.CodeType)',

        ##r_int:  'space.w_int',
        ##r_uint: 'space.w_int',

        # XXX we leak 5 references here, but that's the least of the
        #     problems with this section of code
        # type 'builtin_function_or_method':
        type(len): 'space.wrap(types.FunctionType)',
        # type 'method_descriptor':
        # XXX small problem here:
        # XXX with space.eval, we get <W_TypeObject(method)>
        # XXX but with wrap, we get <W_TypeObject(instancemethod)>
        type(list.append): 'eval_helper(space, "list.append")',
        # type 'wrapper_descriptor':
        type(type(None).__repr__): 'eval_helper(space, ".type(None).__repr__")',
        # type 'getset_descriptor':
        # XXX here we get <W_TypeObject(FakeDescriptor)>,
        # while eval gives us <W_TypeObject(GetSetProperty)>
        type(type.__dict__['__dict__']): 'eval_helper(space,'\
            ' "type(type.__dict__[\'__dict__\'])")',
        # type 'member_descriptor':
        # XXX this does not work in eval!
        # type(type.__dict__['__basicsize__']): "cannot eval type(type.__dict__['__basicsize__'])",
        # XXX there seems to be no working support for member descriptors ???
        type(type.__dict__['__basicsize__']): "space.wrap(type(type.__dict__['__basicsize__']))",
        }

    def nameof_type(self, cls):
        if cls in self.typename_mapping:
            return self.typename_mapping[cls]
        assert cls.__module__ != '__builtin__', \
            "built-in class %r not found in typename_mapping" % (cls,)
        return self.nameof_classobj(cls)

    def nameof_tuple(self, tup):
        name = self.uniquename('g%dtuple' % len(tup))
        args = [self.nameof(x) for x in tup]
        args = ', '.join(args)
        self.initcode.append('m.%s = space.newtuple([%s])' % (name, args))
        return name

    def nameof_list(self, lis):
        name = self.uniquename('g%dlist' % len(lis))
        def initlist():
            for i in range(len(lis)):
                item = self.nameof(lis[i])
                yield 'space.setitem(%s, %s, %s);' % (
                    name, self.nameof(i), self.nameof(item))
        self.initcode.append('m.%s = space.newlist(%s)' % (name, self.nameof(0)))
        self.initcode.append('m.%s = space.mul(%s, %s)' % (name, name, self.nameof(len(lis))))
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
        self.initcode.append('m.%s = space.newdict([])' % (name,))
        self.later(initdict())
        return name

    # strange prebuilt instances below, don't look too closely
    # XXX oh well.
    def nameof_member_descriptor(self, md):
        name = self.uniquename('gdescriptor_%s_%s' % (
            md.__objclass__.__name__, md.__name__))
        cls = self.nameof(md.__objclass__)
        # do I need to take the dict and then getitem???
        self.initcode.append('m.%s = space.getattr(%s, %s)' %
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

    def gen_source(self, fname, ftmpname=None):
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
                dic[name] = eval(value)
            key = dic["filename"], dic["firstlineno"], uniqueno
            return key

        order_sections(fname)
        if self.ftmpname:
            copyfile(self.ftmpname, self.fname)
        
    def gen_source_temp(self):
        f = self.f
        info = {
            'modname': self.modname,
            'entrypointname': self.trans_funcname(
                self.translator.functions[0].__name__),
            'entrypoint': self.nameof(self.translator.functions[0]),
            }
        # header
        print >> f, self.RPY_HEADER
        print >> f

        # doc
        if self.moddict and self.moddict.get("__doc__"):
            doc = self.moddict["__doc__"]
            for line in render_docstr(doc):
                print >> f, line
            print >> f
            # make sure it is not rendered again
            key = Constant(doc).key
            self.rpynames[key] = "__doc__"
            self.seennames["__doc__"] = 1
            self.initcode.append("m.__doc__ = space.wrap(m.__doc__)")
        # function implementations
        while self.pendingfunctions:
            func = self.pendingfunctions.pop()
            self.currentfunc = func
            self.gen_rpyfunction(func)
            # collect more of the latercode after each function
            while self.latercode:
                gen, self.debugstack = self.latercode.pop()
                #self.initcode.extend(gen) -- eats TypeError! bad CPython!
                for line in gen:
                    self.initcode.append(line)
                self.debugstack = ()
            self.gen_global_declarations()

        # set the final splitter
        print >> f, "##SECTION##"
        # footer
        print >> f, self.RPY_INIT_HEADER % info
        for codelines in self.initcode:
            for codeline in codelines.split("\n"):
                print >> f, "    %s" % codeline
        print >> f, self.RPY_INIT_FOOTER % info
        f.close()

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
            pass # self.initcode.append('# REGISTER_GLOBAL(%s)' % (name,))
        del g[:]
    
    def gen_rpyfunction(self, func):

        f = self.f
        print >> f, "##SECTION##" # simple to split, afterwards
        print >> f, ("## filename    %r\n"
                     "## function    %r\n"
                     "## firstlineno %d") % (
            func.func_code.co_filename,
            func.func_code.co_name,
            func.func_code.co_firstlineno)
        print >> f, "##SECTION##"
        locals = {}
        body = list(self.rpyfunction_body(func, locals))
        name_of_defaults = [self.nameof(x, debug=('Default argument of', func))
                            for x in (func.func_defaults or ())]
        self.gen_global_declarations()

        # print header
        doc_lines = render_docstr(func, "    ")
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
        localnames = [self.expr(a, locals) for a in uniqueitems(localslst)]

        # collect all the arguments
        if func.func_code.co_flags & CO_VARARGS:
            vararg = graph.getargs()[-1]
            positional_args = graph.getargs()[:-1]
        else:
            vararg = None
            positional_args = graph.getargs()
        min_number_of_args = len(positional_args) - len(name_of_defaults)

        fast_args = [self.expr(a, locals) for a in positional_args]
        if vararg is not None:
            fast_args.append(self.expr(vararg, locals))
        fast_name = 'fast' + f_name

        fast_set = dict(zip(fast_args, fast_args))

        # create function declaration
        name = self.trans_funcname(func.__name__) # for <lambda>
        argstr = ", ".join(fast_args)
        fast_function_header = ('def %s(space, %s):'
                                % (name, argstr))

        print >> f, 'def %s(space, *args_w):' % (name,)
        for line in doc_lines:
            print >> f, line
        kwlist = ['"%s"' % var for var in
                      func.func_code.co_varnames[:func.func_code.co_argcount]]
        print >> f, '    kwlist = [%s]' % (', '.join(kwlist),)

        # argument unpacking
        if vararg is not None:
            varname = self.expr(vararg, locals)
            lenargs = len(positional_args)
            print >> f, '    %s = space.newtuple(list(args_w[%d:]))' % (
                varname, lenargs)
            print >> f, '    _args_w = args_w[:%d]' % (lenargs,)
        else:
            print >> f, '    _args_w = args_w'
            varname = None

        def tupstr(seq):
            if len(seq) == 1:
                fmt = '%s,'
            else:
                fmt = '%s'
            return fmt % ', '.join(seq)

        print >> f, '    defaults_w = (%s)' % tupstr(name_of_defaults)

        theargs = [arg for arg in fast_args if arg != varname]
        txt = inspect.getsource(PyArg_ParseMini) + ('\n'
               'm.PyArg_ParseMini = PyArg_ParseMini\n'
               'from pypy.interpreter.error import OperationError\n'
               'm.OperationError = OperationError')
        self.initcode.append(txt)
        print >> f, '    funcname = "%s"' % func.__name__
        if theargs:
            txt = '    %s = PyArg_ParseMini(space, funcname, %d, %d, _args_w, defaults_w)'
            print >>f, txt % (tupstr(theargs),
                              min_number_of_args, len(positional_args))
        else:
            txt = '    PyArg_ParseMini(space, funcname, %d, %d, _args_w, defaults_w)'
            print >>f, txt % (min_number_of_args, len(positional_args))
        print >> f, '    return %s(space, %s)' % (fast_name, ', '.join(fast_args))
        print >> f, '%s = globals().pop("%s")' % (f_name, name)
        print >> f

        print >> f, fast_function_header
        for line in doc_lines:
            print >> f, line

        fast_locals = [arg for arg in localnames if arg not in fast_set]
        if fast_locals:
            print >> f
            for line in self.large_initialize(fast_locals):
                print >> f, "    %s" % line
            print >> f
        # generate an incref for each input argument
        # skipped

        # print the body
        for line in body:
            print >> f, line
        print >> f, '%s = globals().pop("%s")' % (fast_name, name)
        print >> f

        # print the PyMethodDef
        # skipped

        if not self.translator.frozen:
            # this is only to keep the RAM consumption under control
            del self.translator.flowgraphs[func]
            Variable.instances.clear()

    def rpyfunction_body(self, func, localvars):
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

        yield "    goto = %d # startblock" % blocknum[start]
        yield "    while True:"
                
        def render_block(block):
            catch_exception = block.exitswitch == Constant(last_exception)
            regular_op = len(block.operations) - catch_exception
            # render all but maybe the last op
            for op in block.operations[:regular_op]:
                for line in self.oper(op, localvars).split("\n"):
                    yield "%s" % line
            # render the last op if it is exception handled
            for op in block.operations[regular_op:]:
                yield "try:"
                for line in self.oper(op, localvars).split("\n"):
                    yield "    %s" % line

            if len(block.exits) == 0:
                if len(block.inputargs) == 2:   # exc_cls, exc_value
                    # exceptional return block
                    exc_cls = self.expr(block.inputargs[0], localvars)
                    exc_val = self.expr(block.inputargs[1], localvars)
                    yield "raise OperationError(%s, %s)" % (exc_cls, exc_val)
                else:
                    # regular return block
                    retval = self.expr(block.inputargs[0], localvars)
                    yield "return %s" % retval
                return
            elif block.exitswitch is None:
                # single-exit block
                assert len(block.exits) == 1
                for op in self.gen_link(block.exits[0], localvars, blocknum, block):
                    yield "%s" % op
            elif catch_exception:
                # block catching the exceptions raised by its last operation
                # we handle the non-exceptional case first
                link = block.exits[0]
                assert link.exitcase is None
                for op in self.gen_link(link, localvars, blocknum, block):
                    yield "    %s" % op
                # we must catch the exception raised by the last operation,
                # which goes to the last err%d_%d label written above.
                # Since we only have OperationError, we need to select:
                yield "except OperationError, e:"
                q = "if"
                for link in block.exits[1:]:
                    assert issubclass(link.exitcase, Exception)
                    # Exeption classes come unwrapped in link.exitcase
                    yield "    %s space.is_true(space.issubtype(e.w_type, %s)):" % (q,
                                            self.nameof(link.exitcase))
                    q = "elif"
                    for op in self.gen_link(link, localvars, blocknum, block, {
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
                                                     localvars),
                                                     link.exitcase)
                    for op in self.gen_link(link, localvars, blocknum, block):
                        yield "    %s" % op
                    q = "elif"
                link = exits[-1]
                yield "else:"
                yield "    assert %s == %s" % (self.expr(block.exitswitch,
                                                    localvars),
                                                    link.exitcase)
                for op in self.gen_link(exits[-1], localvars, blocknum, block):
                    yield "    %s" % op

        for block in allblocks:
            blockno = blocknum[block]
            yield ""
            yield "        if goto == %d:" % blockno
            for line in render_block(block):
                yield "            %s" % line

# ____________________________________________________________

    RPY_HEADER = '#!/bin/env python\n# -*- coding: LATIN-1 -*-'

    RPY_SEP = "#*************************************************************"

    RPY_INIT_HEADER = RPY_SEP + '''

def init%(modname)s(space):
    """NOT_RPYTHON"""
    class m: pass # fake module
    m.__dict__ = globals()
'''

    RPY_INIT_FOOTER = '''
# entry point: %(entrypointname)s, %(entrypoint)s)
if __name__ == "__main__":
    from pypy.objspace.std import StdObjSpace
    space = StdObjSpace()
    init%(modname)s(space)
    print space.unwrap(space.call(
            gfunc_%(entrypointname)s, space.newtuple([])))
'''

# a translation table suitable for str.translate() to remove
# non-C characters from an identifier
C_IDENTIFIER = ''.join([(('0' <= chr(i) <= '9' or
                          'a' <= chr(i) <= 'z' or
                          'A' <= chr(i) <= 'Z') and chr(i) or '_')
                        for i in range(256)])

# temporary arg parsing
# what about keywords? Gateway doesn't support it.
def PyArg_ParseMini(space, name, minargs, maxargs, args_w, defaults_w):
    err = None
    if len(args_w) < minargs:
        txt = "%s() takes at least %d argument%s (%d given)"
        plural = ['s', ''][minargs == 1]
        err = (name, minargs, plural, len(args_w))
    if len(args_w) > maxargs:
        plural = ['s', ''][maxargs == 1]
        if minargs == maxargs:
            if minargs == 0:
                txt = '%s() takes no arguments (%d given)'
                err = (name, len(args_w))
            elif minargs == 1:
                txt = '%s() takes exactly %d argument%s (%d given)'
                err = (name, maxargs, plural, len(args_w))
        else:
            txt = '%s() takes at most %d argument%s (%d given)'
            err = (name, maxargs, plural, len(args_w))
    if err:
        w_txt = space.wrap(txt)
        w_tup = space.wrap(err)
        w_txt = space.mod(w_txt, w_tup)
        raise OperationError(space.w_TypeError, w_txt)

    # finally, we create the result ;-)
    res_w = args_w + defaults_w[len(args_w) - minargs:]
    assert len(res_w) == maxargs
    return res_w
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

def test_exceptions_helper():
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
                test_strutil,
                test_struct,
                test_exceptions_helper,
                all_entries)
entrypoint = entrypoints[-2]

if __name__ == "__main__":
    import os, sys
    from pypy.interpreter import autopath
    srcdir = os.path.dirname(autopath.pypydir)
    appdir = os.path.join(autopath.pypydir, 'appspace')

    if appdir not in sys.path:
        sys.path.insert(0, appdir)

    dic = None
    if entrypoint.__name__.endswith("_helper"):
        dic, entrypoint = entrypoint()
    t = Translator(entrypoint, verbose=False, simplifying=True)
    gen = GenRpy(t)
    gen.use_fast_call = True
    if dic: gen.moddict = dic
    import pypy.appspace.generated as tmp
    pth = os.path.dirname(tmp.__file__)
    ftmpname = "/tmp/look.py"
    fname = os.path.join(pth, gen.modname+".py")
    gen.gen_source(fname, ftmpname)

    #t.simplify()
    #t.view()
    # debugging
    graph = t.getflowgraph()
    ab = ordered_blocks(graph) # use ctrl-b in PyWin with ab

def crazy_test():
    """ this thingy is generating the whole interpreter in itself"""
    # but doesn't work, my goto's give a problem for flow space
    dic = {"__builtins__": __builtins__, "__name__": "__main__"}
    execfile("/tmp/look.py", dic)
    
    def test():
        f_ff(space, 2, 3)
    test = type(test)(test.func_code, dic)
        
    t = Translator(test, verbose=False, simplifying=True)
    gen = GenRpy(t)
    gen.gen_source("/tmp/look2.py")
