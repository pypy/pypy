"""
Generate a C source file from the flowmodel.

"""
from __future__ import generators
import autopath, os
from pypy.objspace.flow.model import Variable, Constant, SpaceOperation
from pypy.objspace.flow.model import FunctionGraph, Block, Link
from pypy.translator.typer import LLFunction, LLOp, LLVar, LLConst
from pypy.translator.classtyper import LLClass
from pypy.translator.genc_typeset import CTypeSet
from pypy.translator.genc_op import ERROR_RETVAL
from pypy.translator.genc_repr import R_INT, R_OBJECT, cdecl

# ____________________________________________________________

def uniquemodulename(name, SEEN={}):
    # never reuse the same module name within a Python session!
    i = 0
    while True:
        i += 1
        result = '%s_%d' % (name, i)
        if result not in SEEN:
            SEEN[result] = True
            return result


class GenC:
    MODNAMES = {}

    def __init__(self, f, translator, modname=None):
        self.f = f
        self.translator = translator
        self.modname = (modname or
                        uniquemodulename(translator.functions[0].__name__))
        if translator.annotator:
            bindings = translator.annotator.bindings.copy()
        else:
            bindings = {}
        self.typeset = CTypeSet(self, bindings)
        self.initializationcode = []
        self.llclasses = {};   self.classeslist = []
        self.llfunctions = {}; self.functionslist = []
        # must build functions first, otherwise methods are not found
        self.build_llfunctions()
        self.build_llclasses()
        self.build_llentrypoint()
        self.gen_source()

    def gen_source(self):
        f = self.f
        info = {
            'modname': self.modname,
            'exported': self.translator.functions[0].__name__,
            }
        # header
        print >> f, self.C_HEADER

        # forward declarations
        print >> f, '/* forward declarations */'
        for llfunc in self.functionslist:
            print >> f, '%s;' % self.cfunction_header(llfunc)
        print >> f

        # declaration of class structures
        for llclass in self.classeslist:
            self.gen_cclass(llclass)

        # function implementation
        print >> f, self.C_SEP
        print >> f
        for llfunc in self.functionslist:
            self.gen_cfunction(llfunc)
            print >> f

        # entry point
        print >> f, self.C_SEP
        print >> f, self.C_ENTRYPOINT_HEADER % info
        self.gen_entrypoint()
        print >> f, self.C_ENTRYPOINT_FOOTER % info

        # footer
        print >> f, self.C_METHOD_TABLE % info
        print >> f, self.C_INIT_HEADER % info
        for codeline in self.initializationcode:
            print >> f, '\t' + codeline
        print >> f, self.C_INIT_FOOTER % info


    def build_llclasses(self):
        if not self.translator.annotator:
            return
        n = 0
        for cdef in self.translator.annotator.getuserclassdefinitions():
            # annotation.factory guarantees that this will enumerate
            # the ClassDefs in a parent-first, children-last order.
            cls = cdef.cls
            assert cls not in self.llclasses, '%r duplicate' % (cls,)
            if cdef.basedef is None:
                llparent = None
            else:
                llparent = self.llclasses[cdef.basedef.cls]
            llclass = LLClass(
                typeset = self.typeset,
                name = '%s__%d' % (cls.__name__, n),
                cdef = cdef,
                llparent = llparent,
                )
            self.llclasses[cls] = llclass
            self.classeslist.append(llclass)
            n += 1
        for llclass in self.classeslist:
            llclass.setup()
        management_functions = []
        for llclass in self.classeslist:
            management_functions += llclass.get_management_functions()
        self.functionslist[:0] = management_functions

    def build_llfunctions(self):
        n = 0
        for func in self.translator.functions:
            assert func not in self.llfunctions, '%r duplicate' % (func,)
            llfunc = LLFunction(
                typeset = self.typeset,
                name    = 'f%d_%s' % (n, func.func_name),
                graph   = self.translator.flowgraphs[func])
            self.llfunctions[func] = llfunc
            self.functionslist.append(llfunc)
            n += 1

    def build_llentrypoint(self):
        # create a LLFunc that calls the entry point function and returns
        # whatever it returns, but converted to PyObject*.
        main = self.translator.functions[0]
        llmain = self.llfunctions[main]
        inputargs = llmain.graph.getargs()
        b = Block(inputargs)
        v1 = Variable()
        b.operations.append(SpaceOperation('simple_call',
                                           [Constant(main)] + inputargs,
                                           v1))
        # finally, return v1
        graph = FunctionGraph('entry_point', b)
        b.closeblock(Link([v1], graph.returnblock))
        llfunc = LLFunction(self.typeset, graph.name, graph)
        self.functionslist.append(llfunc)

    def get_llfunc_header(self, llfunc):
        llargs, llret = llfunc.ll_header()
        if len(llret) == 0:
            retlltype = None
        elif len(llret) == 1:
            retlltype = llret[0].type
        else:
            # if there is more than one return LLVar, only the first one is
            # returned and the other ones are returned via ptr output args
            retlltype = llret[0].type
            llargs += [LLVar(a.type, '*output_'+a.name) for a in llret[1:]]
        return llargs, retlltype

    def cfunction_header(self, llfunc):
        llargs, rettype = self.get_llfunc_header(llfunc)
        l = [cdecl(a.type, a.name) for a in llargs]
        l = l or ['void']
        return 'static ' + cdecl(rettype or 'int',
                                 '%s(%s)' % (llfunc.name, ', '.join(l)))

    def gen_entrypoint(self):
        f = self.f
        llfunc = self.functionslist[-1]
        llargs, rettype = self.get_llfunc_header(llfunc)
        assert llfunc.name == 'entry_point', llfunc.name
        assert rettype == 'PyObject*', rettype
        l = []
        l2 = []
        for a in llargs:
            print >> f, '\t%s;' % cdecl(a.type, a.name)
            l.append('&' + a.name)
            l2.append(a.name)
        formatstr = []
        for v in llfunc.graph.getargs():
            hltype = self.typeset.gethltype(v)
            assert hltype.parse_code, (
                "entry point arg %s has unsupported type %s" % (v, hltype))
            formatstr.append(hltype.parse_code)
        l.insert(0, '"' + ''.join(formatstr) + '"')
        print >> f, '\tif (!PyArg_ParseTuple(args, %s))' % ', '.join(l)
        print >> f, '\t\treturn NULL;'
        print >> f, '\treturn entry_point(%s);' % (', '.join(l2))

    def gen_cfunction(self, llfunc):
        f = self.f

        # generate the body of the function
        llargs, rettype = self.get_llfunc_header(llfunc)
        error_retval = LLConst(rettype, ERROR_RETVAL.get(rettype, 'NULL'))
        body = list(llfunc.ll_body([error_retval]))

        # print the declaration of the new global constants needed by
        # the current function
        to_declare = []
        for line in body:
            if isinstance(line, LLOp):
                for a in line.using():
                    if isinstance(a, LLConst) and a.to_declare:
                        to_declare.append(a)
                        if a.initexpr:
                            self.initializationcode.append('%s = %s;' % (
                                a.name, a.initexpr))
                        a.to_declare = False
        if to_declare:
            print >> f, '/* global constant%s */' % ('s'*(len(to_declare)>1))
            for a in to_declare:
                print >> f, 'static %s;' % cdecl(a.type, a.name)
            print >> f

        # print header
        print >> f, self.cfunction_header(llfunc)
        print >> f, '{'

        # collect and print all the local variables from the body
        lllocals = []
        for line in body:
            if isinstance(line, LLOp):
                lllocals += line.using()
        seen = {}
        for a in llargs:
            seen[a] = True
        for a in lllocals:
            if a not in seen:
                if not isinstance(a, LLConst):
                    print >> f, '\t%s;' % cdecl(a.type, a.name)
                seen[a] = True
        print >> f

        # print the body
        for line in body:
            if isinstance(line, LLOp):
                code = line.write()
                if code:
                    for codeline in code.split('\n'):
                        print >> f, '\t' + codeline
            elif line:  # label
                print >> f, '   %s:' % line
            else:  # empty line
                print >> f
        print >> f, '}'

    def gen_cclass(self, llclass):
        f = self.f
        cls = llclass.cdef.cls
        info = {
            'module': cls.__module__,
            'basename': cls.__name__,
            'name': llclass.name,
            'base': '0',
            }
        if llclass.llparent is not None:
            info['base'] = '&g_Type_%s.type' % llclass.llparent.name

        # print the C struct declaration
        print >> f, self.C_STRUCT_HEADER % info
        for fld in llclass.instance_fields:
            for llvar in fld.llvars:
                print >> f, '\t%s;' % cdecl(llvar.type, llvar.name)
        print >> f, self.C_STRUCT_FOOTER % info

        # print the struct PyTypeObject_Xxx, which is an extension of
        # PyTypeObject with the class attributes of this class
        print >> f, self.C_TYPESTRUCT_HEADER % info
        for fld in llclass.class_fields:
            for llvar in fld.llvars:
                print >> f, '\t%s;' % cdecl(llvar.type, llvar.name)
        print >> f, self.C_TYPESTRUCT_FOOTER % info

        # generate the deallocator function -- must special-case it;
        # other functions are generated by LLClass.get_management_functions()
        print >> f, self.C_DEALLOC_HEADER % info
        llxdecref = self.typeset.rawoperations['xdecref']
        for fld in llclass.instance_fields:
            llvars = fld.getllvars('op->%s')
            line = llxdecref(llvars)
            code = line.write()
            if code:
                for codeline in code.split('\n'):
                    print >> f, '\t' + codeline
        print >> f, self.C_DEALLOC_FOOTER % info

        # generate the member list for the type object
        print >> f, self.C_MEMBERLIST_HEADER % info
        # XXX write member definitions for member with well-known types only
        #     members from the parents are inherited via tp_base
        for fld in llclass.fields_here:
            if fld.is_class_attr:
                continue   # XXX should provide a reader
            if fld.hltype == R_OBJECT:
                t = 'T_OBJECT_EX'
            elif fld.hltype == R_INT:
                t = 'T_INT'
            else:
                continue   # ignored
            print >> f, '\t{"%s",\t%s,\toffsetof(PyObj_%s, %s)},' % (
                fld.name, t, llclass.name, fld.llvars[0].name)
        print >> f, self.C_MEMBERLIST_FOOTER % info

        # declare and initialize the static PyTypeObject
        print >> f, self.C_TYPEOBJECT % info

        self.initializationcode.append('SETUP_TYPE(%s)' % llclass.name)

# ____________________________________________________________

    C_HEADER = open(os.path.join(autopath.this_dir, 'genc.h')).read()

    C_SEP = "/************************************************************/"

    C_ENTRYPOINT_HEADER = '''
static PyObject* c_%(exported)s(PyObject* self, PyObject* args)
{'''

    C_ENTRYPOINT_FOOTER = '''}'''

    C_METHOD_TABLE = '''
static PyMethodDef g_methods_%(modname)s[] = {
\t{"%(exported)s", (PyCFunction)c_%(exported)s, METH_VARARGS},
\t{NULL, NULL}
};'''

    C_INIT_HEADER = '''
void init%(modname)s(void)
{
\tPy_InitModule("%(modname)s", g_methods_%(modname)s);'''

    C_INIT_FOOTER = '''}'''

    C_STRUCT_HEADER = C_SEP + '''
/*** Definition of class %(module)s.%(basename)s ***/

typedef struct {
	PyObject_HEAD'''

    C_STRUCT_FOOTER = '''} PyObj_%(name)s;
'''

    C_DEALLOC_HEADER = '''static void dealloc_%(name)s(PyObj_%(name)s* op)
{'''

    C_DEALLOC_FOOTER = '''	PyObject_Del((PyObject*) op);
}
'''

    C_MEMBERLIST_HEADER = '''static PyMemberDef g_memberlist_%(name)s[] = {'''

    C_MEMBERLIST_FOOTER = '''	{NULL}	/* Sentinel */
};
'''

    # NB: our types don't have Py_TPFLAGS_BASETYPE because we do not want
    #     the complications of dynamically created subclasses.  This doesn't
    #     prevent the various types from inheriting from each other via
    #     tp_base.  This is ok because we expect all RPython classes to exist
    #     and be analyzed in advance.  This allows class attributes to be stored
    #     as an extensison of the PyTypeObject structure, which are then
    #     accessed with ((PyTypeObject_Xxx*)op->ob_type)->classattrname.
    #     This doesn't work if op->ob_type can point to a heap-allocated
    #     type object over which we have no control.

    C_TYPESTRUCT_HEADER = '''typedef struct {
	PyTypeObject type;
	/* class attributes follow */'''

    C_TYPESTRUCT_FOOTER = '''} PyTypeObject_%(name)s;
'''

    C_TYPEOBJECT = '''static PyTypeObject_%(name)s g_Type_%(name)s = {
	PyObject_HEAD_INIT(&PyType_Type)
	0,
	"%(name)s",
	sizeof(PyObj_%(name)s),
	0,
	(destructor)dealloc_%(name)s,		/* tp_dealloc */
	0,					/* tp_print */
	0,					/* tp_getattr */
	0,					/* tp_setattr */
	0,					/* tp_compare */
	0,					/* tp_repr */
	0,					/* tp_as_number */
	0,					/* tp_as_sequence */
	0,					/* tp_as_mapping */
	0,					/* tp_hash */
	0,					/* tp_call */
	0,					/* tp_str */
	PyObject_GenericGetAttr,		/* tp_getattro */
	PyObject_GenericSetAttr,		/* tp_setattro */
	0,					/* tp_as_buffer */
	Py_TPFLAGS_DEFAULT,			/* tp_flags */
 	0,					/* tp_doc */
 	0,	/* XXX need GC */		/* tp_traverse */
 	0,					/* tp_clear */
	0,					/* tp_richcompare */
	0,					/* tp_weaklistoffset */
	0,					/* tp_iter */
	0,					/* tp_iternext */
	0,					/* tp_methods */
	g_memberlist_%(name)s,			/* tp_members */
	0,					/* tp_getset */
	%(base)s,				/* tp_base */
	0,					/* tp_dict */
	0,					/* tp_descr_get */
	0,					/* tp_descr_set */
	0,					/* tp_dictoffset */
	0,  /* XXX call %(name)s_new() */	/* tp_init */
	PyType_GenericAlloc,			/* tp_alloc */
	PyType_GenericNew,			/* tp_new */
	PyObject_Del,				/* tp_free */
};
'''

# ____________________________________________________________
