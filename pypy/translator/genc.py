"""
Generate a C source file from the flowmodel.

"""
from __future__ import generators
import autopath, os, sys, __builtin__, marshal, zlib
from pypy.objspace.flow.model import Variable, Constant
from types import FunctionType, CodeType, InstanceType, ClassType

from pypy.translator.gensupp import builtin_base, uniquemodulename
from pypy.translator.gensupp import NameManager

from pypy.objspace.std.restricted_int import r_int, r_uint

from pypy.translator.genc_funcdef import FunctionDef, USE_CALL_TRACE

# ____________________________________________________________

#def go_figure_out_this_name(source):
#    # ahem
#    return 'PyRun_String("%s", Py_eval_input, PyEval_GetGlobals(), NULL)' % (
#        source, )

class GenC:
    MODNAMES = {}

    def __init__(self, f, translator, modname=None, f2=None):
        self.f = f
        self.f2 = f2
        self.translator = translator
        self.modname = (modname or
                        uniquemodulename(translator.functions[0].__name__))
        self.cnames = {Constant(None).key:  'Py_None',
                       Constant(False).key: 'Py_False',
                       Constant(True).key:  'Py_True',
                       }
        self.seennames = {}
        self.initcode = [      # list of lines for the module's initxxx()
            'import new, types, sys',
            'Py_None  = None',
            'Py_False = False',
            'Py_True  = True',
            ]

        self.latercode = []    # list of generators generating extra lines
                               #   for later in initxxx() -- for recursive
                               #   objects
        self.namespace= NameManager()
        # keywords cannot be reused.  This is the C99 draft's list.
        self.namespace.make_reserved_names('''
           auto      enum      restrict  unsigned
           break     extern    return    void
           case      float     short     volatile
           char      for       signed    while
           const     goto      sizeof    _Bool
           continue  if        static    _Complex
           default   inline    struct    _Imaginary
           do        int       switch
           double    long      typedef
           else      register  union
           ''')
        # these names are used in function headers,
        # therefore pseudo-preserved in scope 1:
        self.namespace.make_reserved_names('self args kwds')

        self.globaldecl = []
        self.globalobjects = []
        self.pendingfunctions = []
        self.funcdefs = {}
        self.allfuncdefs = []
        self.debugstack = ()  # linked list of nested nameof()
        self.gen_source()

    def nameof(self, obj, debug=None):
        key = Constant(obj).key
        try:
            return self.cnames[key]
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
                                   'nameof_' + cls.__name__.replace(' ', ''),
                                   None)
                    if meth:
                        break
                else:
                    raise Exception, "nameof(%r)" % (obj,)
                name = meth(obj)
            self.debugstack, x = self.debugstack
            assert x is stackentry
            self.cnames[key] = name
            return name

    def uniquename(self, basename):
        name = self.namespace.uniquename(basename)
        self.globalobjects.append(name)
        self.globaldecl.append('static PyObject *%s;' % (name,))
        return name

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
        assert value is os or not hasattr(value, "__file__") or \
               not (value.__file__.endswith('.pyc') or
                    value.__file__.endswith('.py') or
                    value.__file__.endswith('.pyo')), \
               "%r is not a builtin module (probably :)"%value
        name = self.uniquename('mod%s'%value.__name__)
        self.initcode_python(name, "__import__(%r)" % (value.__name__,))
        return name
        

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
##        if [c for c in value if c<' ' or c>'~' or c=='"' or c=='\\']:
##            # non-printable string
##            s = 'chr_%s' % name
##            self.globaldecl.append('static char %s[] = { %s };' % (
##                s, ', '.join(['%d' % ord(c) for c in value])))
##        else:
##            # printable string
##            s = '"%s"' % value
        self.initcode_python(name, repr(value))
        return name

    def skipped_function(self, func):
        # debugging only!  Generates a placeholder for missing functions
        # that raises an exception when called.
        if self.translator.frozen:
            warning = 'NOT GENERATING'
        else:
            warning = 'skipped'
        printable_name = '(%s:%d) %s' % (
            func.func_globals.get('__name__', '?'),
            func.func_code.co_firstlineno,
            func.__name__)
        print warning, printable_name
        name = self.uniquename('gskippedfunc_' + func.__name__)
        self.initcode.append('def %s(*a,**k):' % name)
        self.initcode.append('  raise NotImplementedError')
        return name

    def getfuncdef(self, func):
        if func not in self.funcdefs:
            if self.translator.frozen:
                if func not in self.translator.flowgraphs:
                    return None
            else:
                if (func.func_doc and
                    func.func_doc.lstrip().startswith('NOT_RPYTHON')):
                    return None
            funcdef = FunctionDef(func, self)
            self.funcdefs[func] = funcdef
            self.allfuncdefs.append(funcdef)
            self.pendingfunctions.append(funcdef)
        return self.funcdefs[func]

    def nameof_function(self, func, progress=['-\x08', '\\\x08',
                                              '|\x08', '/\x08']):
        funcdef = self.getfuncdef(func)
        if funcdef is None:
            return self.skipped_function(func)
        if not self.translator.frozen:
            p = progress.pop(0)
            sys.stderr.write(p)
            progress.append(p)
        return funcdef.get_globalobject()

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
        if cls.__doc__ and cls.__doc__.lstrip().startswith('NOT_RPYTHON'):
            raise Exception, "%r should never be reached" % (cls,)

        metaclass = "type"
        if issubclass(cls, Exception):
            if cls.__module__ == 'exceptions':
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
            for key, value in content:
                if key.startswith('__'):
                    if key in ['__module__', '__doc__', '__dict__',
                               '__weakref__', '__repr__', '__metaclass__']:
                        continue
                    # XXX some __NAMES__ are important... nicer solution sought
                    #raise Exception, "unexpected name %r in class %s"%(key, cls)
                if isinstance(value, staticmethod) and value.__get__(1) not in self.translator.flowgraphs and self.translator.frozen:
                    print value
                    continue
                if isinstance(value, classmethod) and value.__get__(cls).__doc__.lstrip().startswith("NOT_RPYTHON"):
                    continue
                if isinstance(value, FunctionType) and value not in self.translator.flowgraphs and self.translator.frozen:
                    print value
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

    def gen_source(self):
        f = self.f
        info = {
            'modname': self.modname,
            'entrypointname': self.translator.functions[0].__name__,
            'entrypoint': self.nameof(self.translator.functions[0]),
            }
        # header
        if USE_CALL_TRACE:
            print >> f, '#define USE_CALL_TRACE'
        print >> f, self.C_HEADER

        # function implementations
        while self.pendingfunctions:
            funcdef = self.pendingfunctions.pop()
            self.gen_cfunction(funcdef)
            # collect more of the latercode after each function
            while self.latercode:
                gen, self.debugstack = self.latercode.pop()
                #self.initcode.extend(gen) -- eats TypeError! bad CPython!
                for line in gen:
                    self.initcode.append(line)
                self.debugstack = ()
            self.gen_global_declarations()

        # after all the ff_xxx() functions we generate the pyff_xxx() wrappers
        for funcdef in self.allfuncdefs:
            if funcdef.wrapper_name is not None:
                funcdef.gen_wrapper(f)

        # global object table
        print >> f, self.C_OBJECT_TABLE
        for name in self.globalobjects:
            if not name.startswith('gfunc_'):
                print >> f, '\t{&%s, "%s"},' % (name, name)
        print >> f, self.C_TABLE_END

        # global function table
        print >> f, self.C_FUNCTION_TABLE
        for funcdef in self.allfuncdefs:
            if funcdef.globalobject_name is not None:
                print >> f, ('\t{&%s, {"%s", (PyCFunction)%s, '
                             'METH_VARARGS|METH_KEYWORDS}},' % (
                    funcdef.globalobject_name,
                    funcdef.base_name,
                    funcdef.wrapper_name))
        print >> f, self.C_TABLE_END

        # frozen init bytecode
        print >> f, self.C_FROZEN_BEGIN
        bytecode = self.getfrozenbytecode()
        def char_repr(c):
            if c in '\\"': return '\\' + c
            if ' ' <= c < '\x7F': return c
            return '\\%03o' % ord(c)
        for i in range(0, len(bytecode), 32):
            print >> f, ''.join([char_repr(c) for c in bytecode[i:i+32]])+'\\'
            if (i+32) % 1024 == 0:
                print >> f, self.C_FROZEN_BETWEEN
        print >> f, self.C_FROZEN_END
        print >> f, "#define FROZEN_INITCODE_SIZE %d" % len(bytecode)

        # the footer proper: the module init function */
        print >> f, self.C_FOOTER % info

    def gen_global_declarations(self):
        g = self.globaldecl
        if g:
            f = self.f
            print >> f, '/* global declaration%s */' % ('s'*(len(g)>1))
            for line in g:
                print >> f, line
            print >> f
            del g[:]
        if self.f2 is not None:
            for line in self.initcode:
                print >> self.f2, line
            del self.initcode[:]

    def getfrozenbytecode(self):
        if self.f2 is not None:
            self.f2.seek(0)
            self.initcode.insert(0, self.f2.read())
        self.initcode.append('')
        source = '\n'.join(self.initcode)
        del self.initcode[:]
        co = compile(source, self.modname, 'exec')
        del source
        small = zlib.compress(marshal.dumps(co))
        source = """if 1:
            import zlib, marshal
            exec marshal.loads(zlib.decompress(%r))""" % small
        co = compile(source, self.modname, 'exec')
        del source
        return marshal.dumps(co)
    
    def gen_cfunction(self, funcdef):
##         print 'gen_cfunction (%s:%d) %s' % (
##             func.func_globals.get('__name__', '?'),
##             func.func_code.co_firstlineno,
##             func.__name__)

        # compute the whole body
        body = list(funcdef.cfunction_body())

        # generate the source now
        self.gen_global_declarations() #.. before the body where they are needed
        funcdef.gen_cfunction(self.f, body)

        # this is only to keep the RAM consumption under control
        funcdef.clear()
        if not self.translator.frozen:
            del self.translator.flowgraphs[funcdef.func]
            Variable.instances.clear()

# ____________________________________________________________

    C_HEADER = '#include "genc.h"\n'

    C_SEP = "/************************************************************/"

    C_OBJECT_TABLE = C_SEP + '''

/* Table of global objects */
static globalobjectdef_t globalobjectdefs[] = {'''

    C_FUNCTION_TABLE = '''
/* Table of functions */
static globalfunctiondef_t globalfunctiondefs[] = {'''

    C_TABLE_END = '\t{ NULL }\t/* Sentinel */\n};'

    C_FROZEN_BEGIN = '''
/* Frozen Python bytecode: the initialization code */
static char *frozen_initcode[] = {"\\'''

    C_FROZEN_BETWEEN = '''", "\\'''

    C_FROZEN_END = '''"};\n'''

    C_FOOTER = C_SEP + '''

MODULE_INITFUNC(%(modname)s)
{
\tSETUP_MODULE(%(modname)s)
\tPyModule_AddObject(m, "%(entrypointname)s", %(entrypoint)s);
}'''
