"""
Generate a C source file from the flowmodel.

"""
import autopath, os
from pypy.objspace.flow.model import Variable, Constant

from pypy.translator.gensupp import uniquemodulename
from pypy.translator.gensupp import NameManager

from pypy.translator.genc_funcdef import FunctionDef, USE_CALL_TRACE
from pypy.translator.genc_pyobj import CType_PyObject

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
        self.pendingfunctions = []
        self.funcdefs = {}
        self.allfuncdefs = []
        self.ctyperepresenters = {}
        self.pyobjrepr = self.getrepresenter(CType_PyObject)
        self.gen_source()

    def getrepresenter(self, type_cls):
        try:
            return self.ctyperepresenters[type_cls]
        except KeyError:
            crepr = self.ctyperepresenters[type_cls] = type_cls(self)
            return crepr

    def nameofconst(self, c, type_cls=None, debug=None):
        if type_cls is None:
            type_cls = getattr(c, 'type_cls', CType_PyObject)
        crepr = self.getrepresenter(type_cls)
        return crepr.nameof(c.value, debug=debug)

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

    # ____________________________________________________________

    def gen_source(self):
        f = self.f
        info = {
            'modname': self.modname,
            'entrypointname': self.translator.functions[0].__name__,
            'entrypoint': self.pyobjrepr.nameof(self.translator.functions[0]),
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
            for crepr in self.ctyperepresenters.values():
                if hasattr(crepr, 'collect_globals'):
                    crepr.collect_globals()
            self.gen_global_declarations()

        # after all the ff_xxx() functions we generate the pyff_xxx() wrappers
        for funcdef in self.allfuncdefs:
            if funcdef.wrapper_name is not None:
                funcdef.gen_wrapper(f)

        # global object table
        print >> f, self.C_OBJECT_TABLE
        for name in self.pyobjrepr.globalobjects:
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
        bytecode = self.pyobjrepr.getfrozenbytecode()
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
