"""
Generate a C source file from the flowmodel.

"""
from __future__ import generators
import autopath, os
from pypy.translator.typer import LLFunction, LLOp, LLConst
from pypy.translator.classtyper import LLClass
from pypy.translator.genc_typeset import CTypeSet, consts_used

# ____________________________________________________________

class GenC:

    def __init__(self, f, translator, modname=None):
        self.f = f
        self.translator = translator
        self.modname = modname or translator.functions[0].__name__
        if translator.annotator:
            bindings = translator.annotator.bindings.copy()
            # for simplicity, force the entry point's return type to be
            # 'PyObject*'
            try:
                entrypoint = translator.functions[0]
                del bindings[translator.flowgraphs[entrypoint].getreturnvar()]
            except KeyError:
                pass
        else:
            bindings = {}
        self.typeset = CTypeSet(self, bindings)
        self.initializationcode = []
        self.llclasses = {};   self.classeslist = []
        self.llfunctions = {}; self.functionslist = []
        self.build_llclasses()
        self.build_llfunctions()
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
        self.gen_entrypoint(self.translator.functions[0])
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
            cls = cdef.cls
            assert cls not in self.llclasses, '%r duplicate' % (cls,)
            llclass = LLClass(
                typeset = self.typeset,
                name = '%s__%d' % (cls.__name__, n),
                cdef = cdef,
                )
            self.llclasses[cls] = llclass
            self.classeslist.append(llclass)
            self.functionslist += llclass.get_management_functions()
            n += 1

    def build_llfunctions(self):
        n = 0
        for func in self.translator.functions:
            assert func not in self.llfunctions, '%r duplicate' % (func,)
            llfunc = LLFunction(
                typeset = self.typeset,
                name    = '%s__%d' % (func.func_name, n),
                graph   = self.translator.flowgraphs[func])
            self.llfunctions[func] = llfunc
            self.functionslist.append(llfunc)
            n += 1

    def cfunction_header(self, llfunc):
        llargs, rettype = llfunc.ll_header()
        l = ['%s %s' % (a.type, a.name) for a in llargs]
        l = l or ['void']
        return 'static %s %s(%s)' % (rettype or 'int',
                                     llfunc.name,
                                     ', '.join(l))

    def gen_entrypoint(self, func):
        f = self.f
        llfunc = self.llfunctions[func]
        llargs, rettype = llfunc.ll_header()
        assert rettype == 'PyObject*', rettype
        l = []
        l2 = []
        for a in llargs:
            print >> f, '\t%s %s;' % (a.type, a.name)
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
        print >> f, '\treturn %s(%s);' % (llfunc.name, ', '.join(l2))

    def gen_cfunction(self, llfunc):
        f = self.f

        # generate the body of the function
        body = list(llfunc.ll_body())

        # print the declaration of the new global constants needed by
        # the current function
        to_declare = []
        for line in body:
            if isinstance(line, LLOp):
                for a in line.args + consts_used(line.name):
                    if isinstance(a, LLConst) and a.to_declare:
                        to_declare.append(a)
                        if a.initexpr:
                            self.initializationcode.append('%s = %s;' % (
                                a.name, a.initexpr))
                        a.to_declare = False
        if to_declare:
            print >> f, '/* global constant%s */' % ('s'*(len(to_declare)>1))
            for a in to_declare:
                print >> f, 'static %s %s;' % (a.type, a.name)
            print >> f

        # print header
        print >> f, self.cfunction_header(llfunc)
        print >> f, '{'

        # collect and print all the local variables from the body
        llargs, rettype = llfunc.ll_header()
        lllocals = llargs[:]
        for line in body:
            if isinstance(line, LLOp):
                lllocals += line.args
        seen = {}
        for a in llargs:
            seen[a] = True
        for a in lllocals:
            if a not in seen:
                if not isinstance(a, LLConst):
                    print >> f, '\t%s %s;' % (a.type, a.name)
                seen[a] = True
        print >> f

        # print the body
        for line in body:
            if isinstance(line, LLOp):
                writer = line.name
                if isinstance(writer, str):   # special low-level operation
                    meth = getattr(self, 'lloperation_' + writer)
                    code = meth(line)
                else:
                    # line.name is actually not a string, but a callable that
                    # generates the C code.
                    args = [a.name for a in line.args]
                    if line.errtarget:
                        args.append(line.errtarget)
                    code = writer(*args)
                if code:
                    for codeline in code.split('\n'):
                        print >> f, '\t' + codeline

            elif line:  # label
                print >> f, '   %s:' % line
            else:  # empty line
                print >> f
        print >> f, '}'

    def lloperation_move(self, line):
        vx, vy = line.args
        return '%s = %s;' % (vy.name, vx.name)

    def lloperation_goto(self, line):
        return 'goto %s;' % line.errtarget

    def lloperation_copy(self, line):
        ls = []
        assert len(line.args) % 2 == 0
        half = len(line.args) // 2
        for i in range(half):
            vx = line.args[i]
            vy = line.args[half+i]
            ls.append('%s = %s;' % (vy.name, vx.name))
            if vy.type == 'PyObject*':
                ls.append('Py_INCREF(%s);' % vy.name)
        return ' '.join(ls)

    def lloperation_incref(self, line):
        ls = []
        for a in line.args:
            if a.type == 'PyObject*':
                ls.append('Py_INCREF(%s);' % a.name)
        return ' '.join(ls)

    def lloperation_decref(self, line):
        ls = []
        for a in line.args:
            if a.type == 'PyObject*':
                ls.append('Py_DECREF(%s);' % a.name)
        return ' '.join(ls)

    def lloperation_xdecref(self, line):
        ls = []
        for a in line.args:
            if a.type == 'PyObject*':
                ls.append('Py_XDECREF(%s);' % a.name)
        return ' '.join(ls)

    def gen_cclass(self, llclass):
        f = self.f
        cls = llclass.cdef.cls
        info = {
            'module': cls.__module__,
            'basename': cls.__name__,
            'name': llclass.name,
            }

        # print the C struct declaration
        print >> f, self.C_STRUCT_HEADER % info
        for fld in llclass.fields:
            for llvar in fld.llvars:
                print >> f, '\t%s %s;' % (llvar.type, llvar.name)
        print >> f, self.C_STRUCT_FOOTER % info

        # generate the deallocator function -- must special-case it;
        # other functions are generated by LLClass.get_management_functions()
        print >> f, self.C_DEALLOC_HEADER % info
        for fld in llclass.fields:
            try:
                sig = (fld.hltype,)
                llname, can_fail = self.typeset.lloperations['xdecref'][sig]
            except KeyError:
                continue    # ignore fields with no xdecref operation
            assert not can_fail
            args = ['op->%s' % llvar.name for llvar in fld.llvars]
            print >> f, '\t' + llname(*args)
        print >> f, self.C_DEALLOC_FOOTER % info

        # generate the member list for the type object
        print >> f, self.C_MEMBERLIST_HEADER % info
        # XXX write member definitions for member with well-known types only
        for fld in llclass.fields:
            if fld.hltype is self.typeset.R_OBJECT:
                t = 'T_OBJECT_EX'
            elif fld.hltype is self.typeset.R_INT:
                t = 'T_INT'
            else:
                continue   # ignored
            print >> f, '\t{"%s",\t%s,\toffsetof(%s_Object, %s)},' % (
                fld.name, t, llclass.name, fld.llvars[0].name)
        print >> f, self.C_MEMBERLIST_FOOTER % info

        # declare and initialize the static PyTypeObject
        print >> f, self.C_TYPEOBJECT % info

# ____________________________________________________________

    C_HEADER = open(os.path.join(autopath.this_dir, 'genc.h')).read()

    C_SEP = "/************************************************************/"

    C_ENTRYPOINT_HEADER = '''
static PyObject* c_%(exported)s(PyObject* self, PyObject* args)
{'''

    C_ENTRYPOINT_FOOTER = '''}'''

    C_METHOD_TABLE = '''
static PyMethodDef %(modname)sMethods[] = {
\t{"%(exported)s", (PyCFunction)c_%(exported)s, METH_VARARGS},
\t{NULL, NULL}
};'''

    C_INIT_HEADER = '''
void init%(modname)s(void)
{
\tPy_InitModule("%(modname)s", %(modname)sMethods);'''

    C_INIT_FOOTER = '''}'''

    C_STRUCT_HEADER = C_SEP + '''
/*** Definition of class %(module)s.%(basename)s ***/

typedef struct {
	PyObject_HEAD'''

    C_STRUCT_FOOTER = '''} %(name)s_Object;
'''

    C_DEALLOC_HEADER = '''static void %(name)s_dealloc(%(name)s_Object* op)
{'''

    C_DEALLOC_FOOTER = '''	op->ob_type->tp_free((PyObject*) op);
}
'''

    C_MEMBERLIST_HEADER = '''static PyMemberDef %(name)s_memberlist[] = {'''

    C_MEMBERLIST_FOOTER = '''	{NULL}	/* Sentinel */
};
'''

    C_TYPEOBJECT = '''static PyTypeObject %(name)s_Type = {
	PyObject_HEAD_INIT(&PyType_Type)
	0,
	"%(name)s",
	sizeof(%(name)s_Object),
	0,
	(destructor)%(name)s_dealloc,		/* tp_dealloc */
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
	Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,/* tp_flags */
 	0,					/* tp_doc */
 	0,	/* XXX need GC */		/* tp_traverse */
 	0,					/* tp_clear */
	0,					/* tp_richcompare */
	0,					/* tp_weaklistoffset */
	0,					/* tp_iter */
	0,					/* tp_iternext */
	0,					/* tp_methods */
	%(name)s_memberlist,			/* tp_members */
	0,					/* tp_getset */
	0,					/* tp_base */
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
