"""
Generate a C source file from the flowmodel.

"""
from __future__ import generators
import autopath, os, sys, __builtin__, marshal
from pypy.objspace.flow.model import Variable, Constant, SpaceOperation
from pypy.objspace.flow.model import FunctionGraph, Block, Link
from pypy.objspace.flow.model import last_exception, last_exc_value
from pypy.objspace.flow.model import traverse, uniqueitems, checkgraph
from pypy.translator.simplify import remove_direct_loops
from pypy.interpreter.pycode import CO_VARARGS
from pypy.annotation import model as annmodel
from types import FunctionType, CodeType, InstanceType, ClassType

from pypy.objspace.std.restricted_int import r_int, r_uint

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

#def go_figure_out_this_name(source):
#    # ahem
#    return 'PyRun_String("%s", Py_eval_input, PyEval_GetGlobals(), NULL)' % (
#        source, )

def builtin_base(obj):
    typ = type(obj)
    while typ.__module__ != '__builtin__':
        typ = typ.__base__
    return typ

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
        # just a few predefined names which cannot be reused.
        # I think this should come from some external file,
        # if we want to be complete
        self.reserved_names = {}
        for each in 'typedef static void const'.split():
            self.reserved_names[each] = 1
        self.latercode = []    # list of generators generating extra lines
                               #   for later in initxxx() -- for recursive
                               #   objects
        self.globaldecl = []
        self.globalobjects = []
        self.pendingfunctions = []
        self.currentfunc = None
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
        basename = basename.translate(C_IDENTIFIER)
        n = self.seennames.get(basename, 0)
        self.seennames[basename] = n+1
        if n == 0:
            self.globalobjects.append(basename)
            self.globaldecl.append('static PyObject *%s;' % (basename,))
            return basename
        else:
            return self.uniquename('%s_%d' % (basename, n))

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
        name = self.uniquename('gskippedfunc_' + func.__name__)
        self.initcode.append('def %s(*a,**k):' % name)
        self.initcode.append('  raise NotImplementedError')
        return name

    def nameof_function(self, func, progress=['-\x08', '\\\x08',
                                              '|\x08', '/\x08']):
        printable_name = '(%s:%d) %s' % (
            func.func_globals.get('__name__', '?'),
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
            p = progress.pop(0)
            sys.stderr.write(p)
            progress.append(p)
        name = self.uniquename('gfunc_' + func.__name__)
        self.pendingfunctions.append(func)
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
        print >> f, self.C_HEADER

        # function implementations
        while self.pendingfunctions:
            func = self.pendingfunctions.pop()
            self.gen_cfunction(func)
            # collect more of the latercode after each function
            while self.latercode:
                gen, self.debugstack = self.latercode.pop()
                #self.initcode.extend(gen) -- eats TypeError! bad CPython!
                for line in gen:
                    self.initcode.append(line)
                self.debugstack = ()
            self.gen_global_declarations()

        # after all the functions: global object table
        print >> f, self.C_OBJECT_TABLE
        for name in self.globalobjects:
            if not name.startswith('gfunc_'):
                print >> f, '\t{&%s, "%s"},' % (name, name)
        print >> f, self.C_TABLE_END

        # global function table
        print >> f, self.C_FUNCTION_TABLE
        for name in self.globalobjects:
            if name.startswith('gfunc_'):
                print >> f, ('\t{&%s, {"%s", (PyCFunction)f_%s, '
                             'METH_VARARGS|METH_KEYWORDS}},' % (
                    name, name[6:], name[6:]))
        print >> f, self.C_TABLE_END

        # frozen init bytecode
        print >> f, self.C_FROZEN_BEGIN
        bytecode = self.getfrozenbytecode()
        def char_repr(c):
            if c in '\\"': return '\\' + c
            if ' ' <= c < '\x7F': return c
            return '\\%03o' % ord(c)
        for i in range(0, len(bytecode), 20):
            print >> f, ''.join([char_repr(c) for c in bytecode[i:i+20]])+'\\'
        print >> f, self.C_FROZEN_END

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
        return marshal.dumps(co)

    def gen_cfunction(self, func):
##         print 'gen_cfunction (%s:%d) %s' % (
##             func.func_globals.get('__name__', '?'),
##             func.func_code.co_firstlineno,
##             func.__name__)

        f = self.f
        localvars = {}
        body = list(self.cfunction_body(func, localvars))
        name_of_defaults = [self.nameof(x, debug=('Default argument of', func))
                            for x in (func.func_defaults or ())]
        self.gen_global_declarations()

        # print header
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
        localnames = [self.expr(a, localvars) for a in uniqueitems(localslst)]

        # collect all the arguments
        if func.func_code.co_flags & CO_VARARGS:
            vararg = graph.getargs()[-1]
            positional_args = graph.getargs()[:-1]
        else:
            vararg = None
            positional_args = graph.getargs()
        min_number_of_args = len(positional_args) - len(name_of_defaults)

        fast_args = [self.expr(a, localvars) for a in positional_args]
        if vararg is not None:
            fast_args.append(str(vararg))
        fast_name = 'fast' + f_name

        fast_set = dict(zip(fast_args, fast_args))

        declare_fast_args = [('PyObject *' + a) for a in fast_args]
        if declare_fast_args:
            declare_fast_args = 'TRACE_ARGS ' + ', '.join(declare_fast_args)
        else:
            declare_fast_args = 'TRACE_ARGS_VOID'
        fast_function_header = ('static PyObject *\n'
                                '%s(%s)' % (fast_name, declare_fast_args))

        print >> f, fast_function_header + ';'  # forward
        print >> f

        print >> f, 'static PyObject *'
        print >> f, '%s(PyObject* self, PyObject* args, PyObject* kwds)' % (
            f_name,)
        print >> f, '{'
        print >> f, '\tFUNCTION_HEAD(%s, %s, args, %s, __FILE__, __LINE__ - 2)' % (
            c_string('%s(%s)' % (cname, ', '.join(name_of_defaults))),
            cname,
            '(%s)' % (', '.join(map(c_string, name_of_defaults) + ['NULL']),),
        )

        kwlist = ['"%s"' % name for name in
                      func.func_code.co_varnames[:func.func_code.co_argcount]]
        kwlist.append('0')
        print >> f, '\tstatic char* kwlist[] = {%s};' % (', '.join(kwlist),)

        if fast_args:
            print >> f, '\tPyObject *%s;' % (', *'.join(fast_args))
        print >> f

        print >> f, '\tFUNCTION_CHECK()'

        # argument unpacking
        if vararg is not None:
            print >> f, '\t%s = PyTuple_GetSlice(args, %d, INT_MAX);' % (
                vararg, len(positional_args))
            print >> f, '\tif (%s == NULL)' % (vararg,)
            print >> f, '\t\tFUNCTION_RETURN(NULL)'
            print >> f, '\targs = PyTuple_GetSlice(args, 0, %d);' % (
                len(positional_args),)
            print >> f, '\tif (args == NULL) {'
            print >> f, '\t\tERR_DECREF(%s)' % (vararg,)
            print >> f, '\t\tFUNCTION_RETURN(NULL)'
            print >> f, '\t}'
            tail = """{
\t\tERR_DECREF(args)
\t\tERR_DECREF(%s)
\t\tFUNCTION_RETURN(NULL);
\t}
\tPy_DECREF(args);""" % vararg
        else:
            tail = '\n\t\tFUNCTION_RETURN(NULL)'
        for i in range(len(name_of_defaults)):
            print >> f, '\t%s = %s;' % (
                self.expr(positional_args[min_number_of_args+i], localvars),
                name_of_defaults[i])
        fmt = 'O'*min_number_of_args
        if min_number_of_args < len(positional_args):
            fmt += '|' + 'O'*(len(positional_args)-min_number_of_args)
        lst = ['args', 'kwds',
               '"%s:%s"' % (fmt, func.__name__),
               'kwlist',
               ]
        lst += ['&' + self.expr(a, localvars) for a in positional_args]
        print >> f, '\tif (!PyArg_ParseTupleAndKeywords(%s))' % ', '.join(lst),
        print >> f, tail

        call_fast_args = list(fast_args)
        if call_fast_args:
            call_fast_args = 'TRACE_CALL ' + ', '.join(call_fast_args)
        else:
            call_fast_args = 'TRACE_CALL_VOID'
        print >> f, '\treturn %s(%s);' % (fast_name, call_fast_args)
        print >> f, '}'
        print >> f

        print >> f, fast_function_header
        print >> f, '{'

        fast_locals = [arg for arg in localnames if arg not in fast_set]
        if fast_locals:
            print >> f, '\tPyObject *%s;' % (', *'.join(fast_locals),)
            print >> f
        
        # generate an incref for each input argument
        for v in positional_args:
            print >> f, '\tPy_INCREF(%s);' % self.expr(v, localvars)

        # print the body
        for line in body:
            if line.endswith(':'):
                if line.startswith('err'):
                    fmt = '\t%s'
                else:
                    fmt = '    %s\n'
            elif line:
                fmt = '\t%s\n'
            else:
                fmt = '%s\n'
            f.write(fmt % line)
        print >> f, '}'

        if not self.translator.frozen:
            # this is only to keep the RAM consumption under control
            del self.translator.flowgraphs[func]
            Variable.instances.clear()

    def expr(self, v, localnames, wrapped = False):
        # this function is copied from geninterp just with a different default.
        # the purpose is to generate short local names.
        # This is intermediate. Common code will be extracted into a base class.
        if isinstance(v, Variable):
            n = v.name
            # there is a problem at the moment.
            # use the name as is until this is solved
            return v.name
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
                # do individual numbering on named vars
                thesenames = localnames.setdefault(name, {})
                ret = thesenames.get(v.name)
                if not ret:
                    if wrapped:
                        fmt = "w_%s_%d"
                    else:
                        fmt = "%s_%d"
                    # don't use zero
                    if len(thesenames) == 0 and name not in self.reserved_names:
                        fmt = fmt[:-3]
                        thesenames[v.name] = ret = fmt % name
                    else:
                        thesenames[v.name] = ret = fmt % (name, len(thesenames))
                return ret
        elif isinstance(v, Constant):
            return self.nameof(v.value,
                               debug=('Constant in the graph of', self.currentfunc))
        else:
            raise TypeError, "expr(%r)" % (v,)

    def cfunction_body(self, func, localvars):
        graph = self.translator.getflowgraph(func)
        remove_direct_loops(graph)
        checkgraph(graph)

        blocknum = {}
        allblocks = []

        def gen_link(link, linklocalvars=None):
            "Generate the code to jump across the given Link."
            has_ref = {}
            linklocalvars = linklocalvars or {}
            for v in to_release:
                linklocalvars[v] = self.expr(v, localvars)
            has_ref = linklocalvars.copy()
            for a1, a2 in zip(link.args, link.target.inputargs):
                if a1 in linklocalvars:
                    src = linklocalvars[a1]
                else:
                    src = self.expr(a1, localvars)
                line = 'MOVE(%s, %s)' % (src, self.expr(a2, localvars))
                if a1 in has_ref:
                    del has_ref[a1]
                else:
                    line += '\tPy_INCREF(%s);' % self.expr(a2, localvars)
                yield line
            for v in has_ref:
                yield 'Py_DECREF(%s);' % linklocalvars[v]
            yield 'goto block%d;' % blocknum[link.target]

        # collect all blocks
        def visit(block):
            if isinstance(block, Block):
                allblocks.append(block)
                blocknum[block] = len(blocknum)
        traverse(visit, graph)

        # generate the body of each block
        for block in allblocks:
            yield ''
            yield 'block%d:' % blocknum[block]
            to_release = list(block.inputargs)
            for op in block.operations:
                lst = [self.expr(v, localvars) for v in op.args]
                lst.append(self.expr(op.result, localvars))
                lst.append('err%d_%d' % (blocknum[block], len(to_release)))
                macro = 'OP_%s' % op.opname.upper()
                meth = getattr(self, macro, None)
                if meth:
                    yield meth(lst[:-2], lst[-2], lst[-1])
                else:
                    yield '%s(%s)' % (macro, ', '.join(lst))
                to_release.append(op.result)

            err_reachable = False
            if len(block.exits) == 0:
                if len(block.inputargs) == 2:   # exc_cls, exc_value
                    # exceptional return block
                    exc_cls   = self.expr(block.inputargs[0], localvars)
                    exc_value = self.expr(block.inputargs[1], localvars)
                    yield 'PyErr_Restore(%s, %s, NULL);' % (exc_cls, exc_value)
                    yield 'FUNCTION_RETURN(NULL)'
                else:
                    # regular return block
                    retval = self.expr(block.inputargs[0], localvars)
                    yield 'FUNCTION_RETURN(%s)' % retval
                continue
            elif block.exitswitch is None:
                # single-exit block
                assert len(block.exits) == 1
                for op in gen_link(block.exits[0]):
                    yield op
                yield ''
            elif block.exitswitch == Constant(last_exception):
                # block catching the exceptions raised by its last operation
                # we handle the non-exceptional case first
                link = block.exits[0]
                assert link.exitcase is None
                for op in gen_link(link):
                    yield op
                # we must catch the exception raised by the last operation,
                # which goes to the last err%d_%d label written above.
                yield ''
                to_release.pop()  # skip default error handling for this label
                yield 'err%d_%d:' % (blocknum[block], len(to_release))
                yield ''
                for link in block.exits[1:]:
                    assert issubclass(link.exitcase, Exception)
                    yield 'if (PyErr_ExceptionMatches(%s)) {' % (
                        self.nameof(link.exitcase),)
                    yield '\tPyObject *exc_cls, *exc_value, *exc_tb;'
                    yield '\tPyErr_Fetch(&exc_cls, &exc_value, &exc_tb);'
                    yield '\tif (exc_value == NULL) {'
                    yield '\t\texc_value = Py_None;'
                    yield '\t\tPy_INCREF(Py_None);'
                    yield '\t}'
                    yield '\tPy_XDECREF(exc_tb);'
                    for op in gen_link(link, {
                                Constant(last_exception): 'exc_cls',
                                Constant(last_exc_value): 'exc_value'}):
                        yield '\t' + op
                    yield '}'
                err_reachable = True
            else:
                # block ending in a switch on a value
                for link in block.exits[:-1]:
                    yield 'if (EQ_%s(%s)) {' % (link.exitcase,
                                                self.expr(block.exitswitch, localvars))
                    for op in gen_link(link):
                        yield '\t' + op
                    yield '}'
                link = block.exits[-1]
                yield 'assert(EQ_%s(%s));' % (link.exitcase,
                                              self.expr(block.exitswitch, localvars))
                for op in gen_link(block.exits[-1]):
                    yield op
                yield ''

            while to_release:
                v = to_release.pop()
                if err_reachable:
                    yield 'ERR_DECREF(%s)' % self.expr(v, localvars)
                yield 'err%d_%d:' % (blocknum[block], len(to_release))
                err_reachable = True
            if err_reachable:
                yield 'FUNCTION_RETURN(NULL)'

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
static char frozen_initcode[] = "\\'''

    C_FROZEN_END = '''";\n'''

    C_FOOTER = C_SEP + '''

MODULE_INITFUNC(%(modname)s)
{
\tSETUP_MODULE(%(modname)s)
\tPyModule_AddObject(m, "%(entrypointname)s", %(entrypoint)s);
}'''

    # the C preprocessor cannot handle operations taking a variable number
    # of arguments, so here are Python methods that do it
    
    def OP_NEWLIST(self, args, r, err):
        if len(args) == 0:
            return 'OP_NEWLIST0(%s, %s)' % (r, err)
        else:
            args.insert(0, '%d' % len(args))
            return 'OP_NEWLIST((%s), %s, %s)' % (', '.join(args), r, err)

    def OP_NEWDICT(self, args, r, err):
        if len(args) == 0:
            return 'OP_NEWDICT0(%s, %s)' % (r, err)
        else:
            assert len(args) % 2 == 0
            args.insert(0, '%d' % (len(args)//2))
            return 'OP_NEWDICT((%s), %s, %s)' % (', '.join(args), r, err)

    def OP_NEWTUPLE(self, args, r, err):
        args.insert(0, '%d' % len(args))
        return 'OP_NEWTUPLE((%s), %s, %s)' % (', '.join(args), r, err)

    def OP_SIMPLE_CALL(self, args, r, err):
        args.append('NULL')
        return 'OP_SIMPLE_CALL((%s), %s, %s)' % (', '.join(args), r, err)

    def OP_CALL_ARGS(self, args, r, err):
        return 'OP_CALL_ARGS((%s), %s, %s)' % (', '.join(args), r, err)

# ____________________________________________________________

def cdecl(type, name):
    # Utility to generate a typed name declaration in C syntax.
    # For local variables, struct fields, function declarations, etc.
    # For complex C types, the 'type' can contain a '@' character that
    # specifies where the 'name' should be inserted; for example, an
    # array of 10 ints has a type of "int @[10]".
    if '@' in type:
        return type.replace('@', name)
    else:
        return ('%s %s' % (type, name)).rstrip()

# a translation table suitable for str.translate() to remove
# non-C characters from an identifier
C_IDENTIFIER = ''.join([(('0' <= chr(i) <= '9' or
                          'a' <= chr(i) <= 'z' or
                          'A' <= chr(i) <= 'Z') and chr(i) or '_')
                        for i in range(256)])
