import os
import sys
import types
import urllib

from pypy.objspace.flow.model import FunctionGraph
from pypy.rpython.rmodel import inputconst
from pypy.rpython.lltypesystem import lltype
from pypy.translator.llvm.codewriter import DEFAULT_CCONV

from pypy.tool.udir import udir

support_functions = [
    "%raisePyExc_IOError",
    "%raisePyExc_ValueError",
    "%raisePyExc_OverflowError",
    "%raisePyExc_ZeroDivisionError",
    "%raisePyExc_RuntimeError",
    "%raisePyExc_thread_error",
    "%RPyString_FromString",
    "%RPyString_AsString",
    "%RPyString_Size",
    "%RPyExceptionOccurred",
    "%LLVM_RPython_StartupCode",
    ]

def get_c_cpath():
    from pypy.translator import translator
    return os.path.dirname(translator.__file__)

def get_genexterns_path():
    return os.path.join(get_llvm_cpath(), "genexterns.c")

def get_llvm_cpath():
    return os.path.join(os.path.dirname(__file__), "module")

def get_ll(ccode, function_names):
    function_names += support_functions
    filename = str(udir.join("ccode.c"))
    f = open(filename, "w")
    f.write(ccode)
    f.close()

    plain = filename[:-2]
    cmd = "llvm-gcc -I%s -I%s -I%s -S %s.c -o %s.ll 2>&1" % (get_llvm_cpath(),
                                                             get_c_cpath(),
                                                             get_python_inc(),
                                                             plain,
                                                             plain)
    os.system(cmd)
    llcode = open(plain + '.ll').read()

    # strip lines
    ll_lines = []
    funcnames = dict([(k, True) for k in function_names])

    # strip declares that are in funcnames
    for line in llcode.split('\n'):

        # For some reason gcc introduces this and then we cant resolve it
        # XXX Get rid of this - when got more time on our hands
        if line.find("__main") >= 1:
           continue

        # get rid of any of the structs that llvm-gcc introduces to struct types
        line = line.replace("%struct.", "%")

        # strip comments
        comment = line.find(';')
        if comment >= 0:
            line = line[:comment]
        line = line.rstrip()

        # find function names, declare them with the default calling convertion
        if line[-1:] == '{':
           returntype, s = line.split(' ', 1)
           funcname  , s = s.split('(', 1)
           funcnames[funcname] = True
           if line.find("internal") == -1:
                if funcname not in ["%main", "%Pyrex_RPython_StartupCode"]:
                    internal = 'internal '
                    line = '%s%s %s' % (internal, DEFAULT_CCONV, line,)
        ll_lines.append(line)

    # patch calls to function that we just declared fastcc
    ll_lines2, calltag, declaretag = [], 'call ', 'declare '
    for line in ll_lines:
        i = line.find(calltag)
        if i >= 0:
            cconv = 'ccc'
            for funcname in funcnames.iterkeys():
                if line.find(funcname) >= 0:
                    cconv = DEFAULT_CCONV
                    break
            line = "%scall %s %s" % (line[:i], cconv, line[i+len(calltag):])
        if line[:len(declaretag)] == declaretag:
            cconv = 'ccc'
            for funcname in funcnames.keys():
                if line.find(funcname) >= 0:
                    cconv = DEFAULT_CCONV
                    break
            line = "declare %s %s" % (cconv, line[len(declaretag):])
        ll_lines2.append(line)

    llcode = '\n'.join(ll_lines2)
    try:
        decl, impl = llcode.split('implementation')
    except:
        raise "Can't compile external function code (llcode.c): ERROR:", llcode
    return decl, impl

def setup_externs(db):
    rtyper = db.translator.rtyper
    from pypy.translator.c.extfunc import predeclare_all

    # hacks to make predeclare_all work
    # XXX Rationalise this
    db.standalone = True
    db.externalfuncs = {}
    decls = list(predeclare_all(db, rtyper))

    for c_name, obj in decls:
        if isinstance(obj, lltype.LowLevelType):
            db.prepare_type(obj)
        elif isinstance(obj, FunctionGraph):
            funcptr = rtyper.getcallable(obj)
            c = inputconst(lltype.typeOf(funcptr), funcptr)
            db.prepare_arg_value(c)
        elif isinstance(lltype.typeOf(obj), lltype.Ptr):
            db.prepare_constant(lltype.typeOf(obj), obj)
        else:
            assert False, "unhandled predeclare %s %s %s" % (c_name, type(obj), obj)

    return decls

def get_python_inc():
    import distutils.sysconfig
    return distutils.sysconfig.get_python_inc()

def generate_llfile(db, extern_decls, entrynode, standalone):
    ccode = []
    function_names = []
        
    def predeclarefn(c_name, llname):
        function_names.append(llname)
        assert llname[0] == "%"
        llname = llname[1:]
        assert '\n' not in llname
        ccode.append('#define\t%s\t%s\n' % (c_name, llname))

    if standalone:
        predeclarefn("__ENTRY_POINT__", entrynode.get_ref())
        ccode.append('#define ENTRY_POINT_DEFINED 1\n\n')

    for c_name, obj in extern_decls:
        if isinstance(obj, lltype.LowLevelType):
            s = "#define %s struct %s\n%s;\n" % (c_name, c_name, c_name)
            ccode.append(s)
        elif isinstance(obj, FunctionGraph):
            funcptr = db.translator.rtyper.getcallable(obj)
            c = inputconst(lltype.typeOf(funcptr), funcptr)
            predeclarefn(c_name, db.repr_arg(c))
        elif isinstance(lltype.typeOf(obj), lltype.Ptr):
            if c_name.startswith("RPyExc_"):
                c_name = c_name[1:]
                ccode.append("void raise%s(char *);\n" % c_name)
            else:
                predeclarefn(c_name, db.obj2node[obj._obj].ref)                
        else:
            assert False, "unhandled extern_decls %s %s %s" % (c_name, type(obj), obj)

    # start building our source
    ccode = "".join(ccode)
    ccode += open(get_genexterns_path()).read()
    
    return get_ll(ccode, function_names)
