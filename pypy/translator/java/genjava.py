"""
Generate a Java source file from the flowmodel.

"""

import sys, os
from pypy.objspace.flow.model import traverse
from pypy.objspace.flow import FlowObjSpace
from pypy.objspace.flow.model import FunctionGraph, Block, Link, Variable, Constant
from pypy.objspace.flow.model import last_exception, last_exc_value, checkgraph
from pypy.translator.unsimplify import remove_direct_loops
from pypy.interpreter.error import OperationError
from types import FunctionType

from pypy.translator.translator import Translator


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


class GenJava:
    def __init__(self, jdir, translator, modname=None):
        self.jdir = jdir
        self.translator = translator
        self.modname = (modname or
                        translator.functions[0].__name__)
        self.javanames = {Constant(None).key:  'null',
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
        self.callpatterns = {}    # for now, arities seen in simple_call()

        # special constructors:
        self.has_listarg = {
            'newlist':  'PyList',
            'newtuple': 'PyTuple',
            'newdict':  'PyDict',
            'newstring':'PyString',
            }

        self.nameof(self.translator.functions[0])
        self.gen_source()

    def gen_test_class(self, inputargs, expectedresult):
        entrypoint = self.nameof(self.translator.functions[0])
        f = self.jdir.join('test.java').open('w')
        print >> f, 'class test extends PyObject {'
        print >> f, '    static public void main(String[] argv) {'
        print >> f, '        PyObject result = %s.op_simple_call(%s);' % (
            entrypoint, ', '.join([self.nameof(x) for x in inputargs]))
        print >> f, '        if (result.eq(%s))' % (
            self.nameof(expectedresult),)
        print >> f, '            System.out.println("OK");'
        print >> f, '        else'
        print >> f, '            System.out.println("FAIL");'
        print >> f, '    }'
        self.gen_initcode(f)
        print >> f, '};'
        f.close()

    def nameof(self, obj):
        key = Constant(obj).key
        try:
            return self.javanames[key]
        except KeyError:
            #name = "w(%s)" % str(obj)
            #self.javanames[key] = name
            #return name
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
                    raise Exception, "nameof(%r) in %r" % (obj, self.current_func)
                name = meth(obj)
            self.javanames[key] = name
            return name

    def uniquename(self, basename):
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
            raise Exception, "nameof(%r) in %r" % (value, self.current_func)
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
        return "new PyInt(%d)" % value

    def nameof_long(self, value):
        # assume we want them in hex most of the time
        if value < 256L:
            return "%dL" % value
        else:
            return "0x%08xL" % value

    def nameof_float(self, value):
        return "w(%s)" % value

    def nameof_str(self, value):
        content = []
        for c in value:
            if not (' ' <= c < '\x7f'):
                c = '\\%03o' % ord(c)
            content.append(c)
        return 'new PyString("%s")' % (''.join(content),)

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

    def nameof_function(self, func):
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
        name = self.uniquename('gfunc_' + func.__name__)
        self.initcode.append('static PyObject %s = new C_%s();' % (name, name))
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
        if attr in ann.getpbcattrs(pbc):
            return True
        classdef = ann.getuserclasses().get(pbc.__class__)
        if (classdef and
            classdef.about_attribute(attr) != annmodel.SomeImpossibleValue()):
            return True
        return False

    def later(self, gen):
        self.latercode.append(gen)

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
            return "Builtin.%s" % func.__name__
        else:
            # builtin (bound) method
            assert False, "to do"

    def nameof_classobj(self, cls):
        if cls.__doc__ and cls.__doc__.lstrip().startswith('NOT_RPYTHON'):
            raise Exception, "%r should never be reached" % (cls,)

        metaclass = "&PyType_Type"
        if issubclass(cls, Exception):
            if cls.__module__ == 'exceptions':
                return 'w(%s)'%cls.__name__
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


    def nameof_type(self, cls):
        return "w(%s)" % cls.__name__ ##??
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
        return 'space.newdict([w("sorry", "not yet"])'
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
##        info = {
##            'modname': self.modname,
##            'entrypointname': self.translator.functions[0].__name__,
##            'entrypoint': self.nameof(self.translator.functions[0]),
##            }

        # function implementations
        while self.pendingfunctions:
            func = self.current_func = self.pendingfunctions.pop()
            self.gen_javafunction(func)
            # collect more of the latercode after each function
            self.collect_latercode()
            #self.gen_global_declarations()

        # copy over the PyXxx classes
        mydir = os.path.dirname(__file__)
        for fn in os.listdir(mydir):
            if fn.lower().endswith('.java'):
                g = open(os.path.join(mydir, fn), 'r')
                f = self.jdir.join(fn).open('w')
                data = g.read()
                i = data.find('/* CUT HERE')
                if i < 0:
                    f.write(data)
                else:
                    f.write(data[:i])
                    print >> f
                    print >> f, '    /* call patterns */'
                    arities = self.callpatterns.keys()
                    arities.sort()
                    for arity in arities:
                        args = ['PyObject x%d' % i for i in range(arity)]
                        print >> f, ('    PyObject op_simple_call(%s) { throw '
                                     'new TypeError(); }' % ', '.join(args))
                    print >> f
                    self.gen_initcode(f)
                    print >> f, '};'
                f.close()
                g.close()

    def collect_latercode(self):
        while self.latercode:
            gen = self.latercode.pop()
            #self.initcode.extend(gen) -- eats TypeError! bad CPython!
            for line in gen:
                self.initcode.append(line)

    def gen_initcode(self, f):
        self.collect_latercode()
        print >> f, '    /* init code */'
        for line in self.initcode:
            print >> f, '    ' + line
        print >> f
        self.initcode = []

    def gen_javafunction(self, func):
        t = self.translator
        #t.simplify(func)
        graph = t.getflowgraph(func)
        remove_direct_loops(t, graph)
        checkgraph(graph)

        name = self.nameof(func)
        f = self.jdir.join('C_%s.java' % name).open('w')
        try:
            src = graph.source
        except AttributeError:
            pass
        else:
            print >> f, '//'
            for line in src.rstrip().split('\n'):
                print >> f, '// ', line
            print >> f, '//'
        print >> f
        print >> f, 'class C_%s extends PyObject {' % name
        print >> f

        def expr(v):
            if isinstance(v, Variable):
                return v.name
            elif isinstance(v, Constant):
                return self.nameof(v.value)
            else:
                raise TypeError, "expr(%r)" % (v,)

        def arglist(args, prefix=''):
            res = [prefix + expr(arg) for arg in args]
            return ", ".join(res)
        
        def oper(op):
            if op.opname in self.has_listarg:
                fmt = "PyObject[] a_%s = {%s}; PyObject %s = new %s(a_%s);"
                v = expr(op.result)
                return fmt % (v, arglist(op.args), v,
                              self.has_listarg[op.opname], v)
            else:
                fmt = "PyObject %s = %s.op_%s(%s);"
                return fmt % (expr(op.result), expr(op.args[0]),
                              op.opname, arglist(op.args[1:]))

        def gen_link(link, linklocalvars={}):
            "Generate the code to jump across the given Link."
            for a1, a2 in zip(link.args, link.target.inputargs):
                if a1 in linklocalvars:
                    src = linklocalvars[a1]
                else:
                    src = expr(a1)
                yield "%s = %s;" % (expr(a2), src)
            goto = blocknum[link.target]
            if goto == blocknum[block]+1:
                yield '// falls through'
            else:
                yield 'block = %d;' % goto
                yield 'continue;'
        
        start = graph.startblock
        blocks = ordered_blocks(graph)
        nblocks = len(blocks)

        blocknum = {}
        localvars = []
        for block in blocks:
            blocknum[block] = len(blocknum)+1
            if block is not start:
                localvars += block.inputargs

        # create function declaration
        args = arglist(start.inputargs, prefix='PyObject ')
        self.callpatterns[len(start.inputargs)] = True
        print >> f, "    PyObject op_simple_call(%s) {" % args
        for v in localvars:
            print >> f, "        PyObject %s = null;" % v
        print >> f, "        int block = %d; // startblock" % blocknum[start]
        print >> f, "        while (true) switch (block) {"
        
        def render_block(block):
            catch_exception = block.exitswitch == Constant(last_exception)
            regular_op = len(block.operations) - catch_exception
            # render all but maybe the last op
            for op in block.operations[:regular_op]:
                yield "%s" % oper(op)
            # render the last op if it is exception handled
            for op in block.operations[regular_op:]:
                yield "try {"
                yield "    %s" % oper(op)

            if len(block.exits) == 0:
                if len(block.inputargs) == 2:   # exc_cls, exc_value
                    # exceptional return block
                    exc_cls = expr(block.inputargs[0])
                    exc_val = expr(block.inputargs[1])
                    XXX
                    yield "raise OperationError(%s, %s)" % (exc_cls, exc_val)
                else:
                    # regular return block
                    retval = expr(block.inputargs[0])
                    yield "return %s;" % retval
                return
            elif block.exitswitch is None:
                # single-exit block
                assert len(block.exits) == 1
                for op in gen_link(block.exits[0]):
                    yield "%s" % op
            elif catch_exception:
                XXX
                # block catching the exceptions raised by its last operation
                # we handle the non-exceptional case first
                link = block.exits[0]
                assert link.exitcase is None
                for op in gen_link(link):
                    yield "    %s" % op
                # we must catch the exception raised by the last operation,
                # which goes to the last err%d_%d label written above.
                for link in block.exits[1:]:
                    assert issubclass(link.exitcase, Exception)
                    yield "except OperationError, e:"
                    print "*"*10, link.exitcase
                    for op in gen_link(link, {
                                Constant(last_exception): 'e.w_type',
                                Constant(last_exc_value): 'e.w_value'}):
                        yield "    %s" % op
            else:
                # block ending in a switch on a value
                exits = list(block.exits)
                if len(exits) == 2 and (
                    exits[0].exitcase is False and exits[1].exitcase is True):
                    # order these guys like Python does
                    exits.reverse()
                q = "if"
                for link in exits[:-1]:
                    yield "%s (%s.eq(%s)) {" % (q, expr(block.exitswitch),
                                               self.nameof(link.exitcase))
                    for op in gen_link(link):
                        yield "    %s" % op
                    yield "}"
                    q = "else if"
                link = exits[-1]
                yield "else {"
                yield "    // assert %s.eq(%s)" % (expr(block.exitswitch),
                                                  self.nameof(link.exitcase))
                for op in gen_link(exits[-1]):
                    yield "    %s" % op
                yield "}"

        for block in blocks:
            blockno = blocknum[block]
            print >> f
            print >> f, "        case %d:" % blockno
            for line in render_block(block):
                print >> f, "            %s" % line

        print >> f, "        }"
        print >> f, "    }"
        print >> f
        print >> f, "};"
        f.close()
