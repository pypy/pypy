"""
Generate a C source file from the flowmodel.

"""
from __future__ import generators
import autopath, os, sys
from pypy.objspace.flow.model import Variable, Constant, SpaceOperation
from pypy.objspace.flow.model import FunctionGraph, Block, Link
from pypy.objspace.flow.model import last_exception, last_exc_value
from pypy.objspace.flow.model import traverse, uniqueitems, checkgraph
from pypy.translator.simplify import remove_direct_loops
from pypy.interpreter.pycode import CO_VARARGS
from pypy.annotation import model as annmodel
from types import FunctionType

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

def go_figure_out_this_name(source):
    # ahem
    return 'PyRun_String("%s", Py_eval_input, PyEval_GetGlobals(), NULL)' % (
        source, )


class GenC:
    MODNAMES = {}
    # XXX - I don't know how to make a macro do this.. so..
    USE_CALL_TRACE = True

    def __init__(self, f, translator, modname=None, f2=None, f2name=None):
        self.f = f
        self.f2 = f2
        self.f2name = f2name
        self.translator = translator
        self.modname = (modname or
                        uniquemodulename(translator.functions[0].__name__))
        self.cnames = {Constant(None).key:  'Py_None',
                       Constant(False).key: 'Py_False',
                       Constant(True).key:  'Py_True',
                       }
        self.seennames = {}
        self.initcode = []     # list of lines for the module's initxxx()
        self.latercode = []    # list of generators generating extra lines
                               #   for later in initxxx() -- for recursive
                               #   objects
        self.globaldecl = []
        self.globalobjects = []
        self.pendingfunctions = []
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

    def nameof_object(self, value):
        if type(value) is not object:
            raise Exception, "nameof(%r)" % (value,)
        name = self.uniquename('g_object')
        self.initcode.append('INITCHK(%s = PyObject_CallFunction((PyObject*)&PyBaseObject_Type, ""))'%name)
        return name

    def nameof_module(self, value):
        assert value is os or not hasattr(value, "__file__") or \
               not (value.__file__.endswith('.pyc') or
                    value.__file__.endswith('.py') or
                    value.__file__.endswith('.pyo')), \
               "%r is not a builtin module (probably :)"%value
        name = self.uniquename('mod%s'%value.__name__)
        self.initcode.append('INITCHK(%s = PyImport_ImportModule("%s"))'%(name, value.__name__))
        return name
        

    def nameof_int(self, value):
        if value >= 0:
            name = 'gint_%d' % value
        else:
            name = 'gint_minus%d' % abs(value)
        name = self.uniquename(name)
        self.initcode.append('INITCHK(%s = '
                             'PyInt_FromLong(%d))' % (name, value))
        return name

    def nameof_long(self, value):
        assert type(int(value)) is int, "your literal long is too long"
        if value >= 0:
            name = 'glong%d' % value
        else:
            name = 'glong_minus%d' % abs(value)
        name = self.uniquename(name)
        self.initcode.append('INITCHK(%s = '
                             'PyLong_FromLong(%d))' % (name, value))
        return name

    def nameof_float(self, value):
        name = 'gfloat_%s' % value
        name = (name.replace('-', 'minus')
                    .replace('.', 'dot'))
        name = self.uniquename(name)
        self.initcode.append('INITCHK(%s = '
                             'PyFloat_FromDouble(%r))' % (name, value))
        return name

    def nameof_str(self, value):
        name = self.uniquename('gstr_' + value[:32])
        if [c for c in value if c<' ' or c>'~' or c=='"' or c=='\\']:
            # non-printable string
            s = 'chr_%s' % name
            self.globaldecl.append('static char %s[] = { %s };' % (
                s, ', '.join(['%d' % ord(c) for c in value])))
        else:
            # printable string
            s = '"%s"' % value
        self.initcode.append('INITCHK(%s = PyString_FromStringAndSize('
                             '%s, %d))' % (name, s, len(value)))
        return name

    def skipped_function(self, func):
        # debugging only!  Generates a placeholder for missing functions
        # that raises an exception when called.
        name = self.uniquename('gskippedfunc_' + func.__name__)
        self.globaldecl.append('static PyMethodDef ml_%s = { "%s", &skipped, METH_VARARGS };' % (name, name))
        self.initcode.append('INITCHK(%s = PyCFunction_New('
                             '&ml_%s, NULL))' % (name, name))
        self.initcode.append('\tPy_INCREF(%s);' % name)
        self.initcode.append('\tPyCFunction_GET_SELF(%s) = %s;' % (name, name))
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
        self.initcode.append('INITCHK(%s = PyCFunction_New('
                             '&ml_%s, NULL))' % (name, name))
        self.initcode.append('\t%s->ob_type = &PyGenCFunction_Type;' % name)
        self.pendingfunctions.append(func)
        return name

    def nameof_staticmethod(self, sm):
        # XXX XXX XXXX
        func = sm.__get__(42.5)
        name = self.uniquename('gsm_' + func.__name__)
        functionname = self.nameof(func)
        self.initcode.append('INITCHK(%s = PyCFunction_New('
                             '&ml_%s, NULL))' % (name, functionname))
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
            self.initcode.append(
                'INITCHK(%s = gencfunc_descr_get(%s, %s, %s))'%(
                name, func, ob, typ))
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
                    yield 'INITCHK(SETUP_INSTANCE_ATTR(%s, "%s", %s))' % (
                        name, key, self.nameof(value))
        self.initcode.append('INITCHK(SETUP_INSTANCE(%s, %s))' % (
            name, cls))
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
                self.initcode.append('INITCHK(%s = PyMapping_GetItemString('
                                     'PyEval_GetBuiltins(), "%s"))' % (
                    name, func.__name__))
            else:
                self.initcode.append('INITCHK(%s = PyObject_GetAttrString('
                                     '%s, "%s"))' % (
                    name, self.nameof(module), func.__name__))
        else:
            # builtin (bound) method
            name = self.uniquename('gbltinmethod_' + func.__name__)
            self.initcode.append('INITCHK(%s = PyObject_GetAttrString('
                                 '%s, "%s"))' % (
                name, self.nameof(func.__self__), func.__name__))
        return name

    def nameof_classobj(self, cls):
        if cls.__doc__ and cls.__doc__.lstrip().startswith('NOT_RPYTHON'):
            raise Exception, "%r should never be reached" % (cls,)

        metaclass = "&PyType_Type"
        if issubclass(cls, Exception):
            if cls.__module__ == 'exceptions':
                return 'PyExc_%s'%cls.__name__
            #else:
            #    # exceptions must be old-style classes (grr!)
            #    metaclass = "&PyClass_Type"
        # For the moment, use old-style classes exactly when the
        # pypy source uses old-style classes, to avoid strange problems.
        if not isinstance(cls, type):
            assert type(cls) is type(Exception)
            metaclass = "&PyClass_Type"

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
                if isinstance(value, FunctionType) and value not in self.translator.flowgraphs and self.translator.frozen:
                    print value
                    continue
                    
                yield 'INITCHK(SETUP_CLASS_ATTR(%s, "%s", %s))' % (
                    name, key, self.nameof(value))

        baseargs = ", ".join(basenames)
        if baseargs:
            baseargs = ', '+baseargs
        self.initcode.append('INITCHK(%s = PyObject_CallFunction((PyObject*) %s,'
                             %(name, metaclass))
        self.initcode.append('\t\t"s(%s){}", "%s"%s))'
                             %("O"*len(basenames), cls.__name__, baseargs))
        
        self.later(initclassobj())
        return name

    nameof_class = nameof_classobj   # for Python 2.2

    typename_mapping = {
        object: '&PyBaseObject_Type',
        int:    '&PyInt_Type',
        long:   '&PyLong_Type',
        bool:   '&PyBool_Type',
        list:   '&PyList_Type',
        tuple:  '&PyTuple_Type',
        dict:   '&PyDict_Type',
        str:    '&PyString_Type',
        float:  '&PyFloat_Type',
        type(Exception()): '&PyInstance_Type',
        type:   '&PyType_Type',
        complex:'&PyComplex_Type',
        unicode:'&PyUnicode_Type',
        file:   '&PyFile_Type',
        type(None): 'Py_None->ob_type',

        r_int:  '&PyInt_Type',
        r_uint: '&PyInt_Type',

        # XXX we leak 5 references here, but that's the least of the
        #     problems with this section of code
        # type 'builtin_function_or_method':
        type(len): go_figure_out_this_name('type(len)'),
        # type 'method_descriptor':
        type(list.append): go_figure_out_this_name('type(list.append)'),
        # type 'wrapper_descriptor':
        type(type(None).__repr__): go_figure_out_this_name(
            'type(type(None).__repr__)'),
        # type 'getset_descriptor':
        type(type.__dict__['__dict__']): go_figure_out_this_name(
            "type(type.__dict__['__dict__'])"),
        # type 'member_descriptor':
        type(type.__dict__['__basicsize__']): go_figure_out_this_name(
            "type(type.__dict__['__basicsize__'])"),
        }

    def nameof_type(self, cls):
        if cls in self.typename_mapping:
            return '(PyObject*) %s' % self.typename_mapping[cls]
        assert cls.__module__ != '__builtin__', \
            "built-in class %r not found in typename_mapping" % (cls,)
        return self.nameof_classobj(cls)

    def nameof_tuple(self, tup):
        name = self.uniquename('g%dtuple' % len(tup))
        args = [self.nameof(x) for x in tup]
        args.insert(0, '%d' % len(tup))
        args = ', '.join(args)
        self.initcode.append('INITCHK(%s = PyTuple_Pack(%s))' % (name, args))
        return name

    def nameof_list(self, lis):
        name = self.uniquename('g%dlist' % len(lis))
        def initlist():
            for i in range(len(lis)):
                item = self.nameof(lis[i])
                yield '\tPy_INCREF(%s);' % item
                yield '\tPyList_SET_ITEM(%s, %d, %s);' % (name, i, item)
        self.initcode.append('INITCHK(%s = PyList_New(%d))' % (name, len(lis)))
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
                    yield ('\tINITCHK(PyDict_SetItemString'
                           '(%s, "%s", %s) >= 0)'%(
                               name, k, self.nameof(dic[k])))
                else:
                    yield ('\tINITCHK(PyDict_SetItem'
                           '(%s, %s, %s) >= 0)'%(
                               name, self.nameof(k), self.nameof(dic[k])))
        self.initcode.append('INITCHK(%s = PyDict_New())' % (name,))
        self.later(initdict())
        return name

    # strange prebuilt instances below, don't look too closely
    # XXX oh well.
    def nameof_member_descriptor(self, md):
        name = self.uniquename('gdescriptor_%s_%s' % (
            md.__objclass__.__name__, md.__name__))
        cls = self.nameof(md.__objclass__)
        self.initcode.append('INITCHK(PyType_Ready((PyTypeObject*) %s) >= 0)' %
                             cls)
        self.initcode.append('INITCHK(%s = PyMapping_GetItemString('
                             '((PyTypeObject*) %s)->tp_dict, "%s"))' %
                                (name, cls, md.__name__))
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

    def gen_source(self):
        f = self.f
        info = {
            'modname': self.modname,
            'entrypointname': self.translator.functions[0].__name__,
            'entrypoint': self.nameof(self.translator.functions[0]),
            }
        # header
        if self.USE_CALL_TRACE:
            print >> f, '#define USE_CALL_TRACE'
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

        # footer
        print >> f, self.C_INIT_HEADER % info
        if self.f2name is not None:
            print >> f, '#include "%s"' % self.f2name
        for codeline in self.initcode:
            print >> f, '\t' + codeline
        print >> f, self.C_INIT_FOOTER % info

    def gen_global_declarations(self):
        g = self.globaldecl
        if g:
            f = self.f
            print >> f, '/* global declaration%s */' % ('s'*(len(g)>1))
            for line in g:
                print >> f, line
            print >> f
            del g[:]
        g = self.globalobjects
        for name in g:
            self.initcode.append('REGISTER_GLOBAL(%s)' % (name,))
        del g[:]
        if self.f2 is not None:
            for line in self.initcode:
                print >> self.f2, line
            del self.initcode[:]

    def gen_cfunction(self, func):
##         print 'gen_cfunction (%s:%d) %s' % (
##             func.func_globals.get('__name__', '?'),
##             func.func_code.co_firstlineno,
##             func.__name__)

        f = self.f
        body = list(self.cfunction_body(func))
        name_of_defaults = [self.nameof(x, debug=('Default argument of', func))
                            for x in (func.func_defaults or ())]
        self.gen_global_declarations()

        # print header
        name = self.nameof(func)
        assert name.startswith('gfunc_')
        f_name = 'f_' + name[6:]

        # collect all the local variables
        graph = self.translator.getflowgraph(func)
        localslst = []
        def visit(node):
            if isinstance(node, Block):
                localslst.extend(node.getvariables())
        traverse(visit, graph)
        localnames = [a.name for a in uniqueitems(localslst)]

        # collect all the arguments
        if func.func_code.co_flags & CO_VARARGS:
            vararg = graph.getargs()[-1]
            positional_args = graph.getargs()[:-1]
        else:
            vararg = None
            positional_args = graph.getargs()
        min_number_of_args = len(positional_args) - len(name_of_defaults)

        fast_args = [a.name for a in positional_args]
        if vararg is not None:
            fast_args.append(str(vararg))
        fast_name = 'fast' + f_name

        fast_set = dict(zip(fast_args, fast_args))

        declare_fast_args = [('PyObject *' + a) for a in fast_args]
        if self.USE_CALL_TRACE:
            declare_fast_args[:0] = ['PyFrameObject *__f', 'PyThreadState *__tstate']

        print >> f, 'static PyObject *'
        print >> f, '%s(%s);' % (fast_name, ', '.join(declare_fast_args))
        print >> f

        print >> f, 'static PyObject *'
        print >> f, '%s(PyObject* self, PyObject* args)' % (f_name,)
        print >> f, '{'
        print >> f, '\tFUNCTION_HEAD(%s, %s, args, %s, __FILE__, __LINE__ - 2)' % (
            c_string('%s(%s)' % (name, ', '.join(name_of_defaults))),
            name,
            '(%s)' % (', '.join(map(c_string, name_of_defaults) + ['NULL']),),
        )

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
                positional_args[min_number_of_args+i],
                name_of_defaults[i])
        lst = ['args',
               '"%s"' % func.__name__,
               '%d' % min_number_of_args,
               '%d' % len(positional_args),
               ]
        lst += ['&' + a.name for a in positional_args]
        print >> f, '\tif (!PyArg_UnpackTuple(%s))' % ', '.join(lst),
        print >> f, tail

        call_fast_args = list(fast_args)
        if self.USE_CALL_TRACE:
            call_fast_args[:0] = ['__f', '__tstate']
        print >> f, '\treturn %s(%s);' % (fast_name, ', '.join(call_fast_args))
        print >> f, '}'
        print >> f

        print >> f, 'static PyObject *'
        print >> f, '%s(%s)' % (fast_name, ', '.join(declare_fast_args))
        print >> f, '{'

        fast_locals = [arg for arg in localnames if arg not in fast_set]
        if fast_locals:
            print >> f, '\tPyObject *%s;' % (', *'.join(fast_locals),)
            print >> f
        
        # generate an incref for each input argument
        for v in positional_args:
            print >> f, '\tPy_INCREF(%s);' % v.name

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

        # print the PyMethodDef
        print >> f, 'static PyMethodDef ml_%s = { "%s", %s, METH_VARARGS };' % (
            name, func.__name__, f_name)
        print >> f

        if not self.translator.frozen:
            # this is only to keep the RAM consumption under control
            del self.translator.flowgraphs[func]
            Variable.instances.clear()

    def cfunction_body(self, func):
        graph = self.translator.getflowgraph(func)
        remove_direct_loops(graph)
        checkgraph(graph)

        blocknum = {}
        allblocks = []

        def expr(v):
            if isinstance(v, Variable):
                return v.name
            elif isinstance(v, Constant):
                return self.nameof(v.value,
                                   debug=('Constant in the graph of',func))
            else:
                raise TypeError, "expr(%r)" % (v,)

        def gen_link(link, linklocalvars=None):
            "Generate the code to jump across the given Link."
            has_ref = {}
            linklocalvars = linklocalvars or {}
            for v in to_release:
                linklocalvars[v] = v.name
            has_ref = linklocalvars.copy()
            for a1, a2 in zip(link.args, link.target.inputargs):
                if a1 in linklocalvars:
                    src = linklocalvars[a1]
                else:
                    src = expr(a1)
                line = 'MOVE(%s, %s)' % (src, a2.name)
                if a1 in has_ref:
                    del has_ref[a1]
                else:
                    line += '\tPy_INCREF(%s);' % a2.name
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
                lst = [expr(v) for v in op.args]
                lst.append(op.result.name)
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
                    exc_cls   = expr(block.inputargs[0])
                    exc_value = expr(block.inputargs[1])
                    yield 'PyErr_Restore(%s, %s, NULL);' % (exc_cls, exc_value)
                    yield 'FUNCTION_RETURN(NULL)'
                else:
                    # regular return block
                    retval = expr(block.inputargs[0])
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
                                                block.exitswitch.name)
                    for op in gen_link(link):
                        yield '\t' + op
                    yield '}'
                link = block.exits[-1]
                yield 'assert(EQ_%s(%s));' % (link.exitcase,
                                              block.exitswitch.name)
                for op in gen_link(block.exits[-1]):
                    yield op
                yield ''

            while to_release:
                v = to_release.pop()
                if err_reachable:
                    yield 'ERR_DECREF(%s)' % v.name
                yield 'err%d_%d:' % (blocknum[block], len(to_release))
                err_reachable = True
            if err_reachable:
                yield 'FUNCTION_RETURN(NULL)'

# ____________________________________________________________

    C_HEADER = '#include "genc.h"\n'

    C_SEP = "/************************************************************/"

    C_INIT_HEADER = C_SEP + '''

MODULE_INITFUNC(%(modname)s)
{
\tSETUP_MODULE(%(modname)s)
'''

    C_INIT_FOOTER = '''
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
