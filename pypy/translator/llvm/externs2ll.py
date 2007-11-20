import os
import sys
import types
import urllib

from pypy.objspace.flow.model import FunctionGraph
from pypy.rpython.rmodel import inputconst
from pypy.rpython.lltypesystem import lltype
from pypy.translator.llvm.buildllvm import llvm_gcc_version

from pypy.tool.udir import udir

def predeclare_stuff(c_db):
    exctransformer = c_db.exctransformer
    yield ('_rpyexc_occured_ptr',  exctransformer._rpyexc_occured_ptr.value)
    yield ('rpyexc_fetch_type_ptr', exctransformer.rpyexc_fetch_type_ptr.value)
    yield ('rpyexc_clear_ptr',     exctransformer.rpyexc_clear_ptr.value)

support_functions = [
    "@LLVM_RPython_StartupCode",
    ]

skip_lines = [
    "%RPyString = type opaque",
    "__main",
    ]

def get_module_file(name):
    return os.path.join(get_llvm_cpath(), name)

def get_ll(ccode, function_names, default_cconv):
    function_names += support_functions
    filename = str(udir.join("ccode.c"))
    f = open(filename, "w")
    f.write(ccode)
    f.close()

    plain = filename[:-2]
    includes = get_incdirs()

    if llvm_gcc_version() < 4.0:
        emit_llvm = ''
    else:
        emit_llvm = '-emit-llvm -O0'
        
    # XXX localize this
    include_path = '-I/sw/include'
    cmd = "llvm-gcc %s %s %s -S %s.c -o %s.ll 2>&1" % (
        include_path, includes, emit_llvm, plain, plain)

    if os.system(cmd) != 0:
        raise Exception("Failed to run '%s'")

    llcode = open(plain + '.ll').read()

    # strip lines
    ll_lines = []
    funcnames = dict([(k, True) for k in function_names])

    # strip declares that are in funcnames
    for line in llcode.split('\n'):

        # get rid of any of the structs that llvm-gcc introduces to struct types
        line = line.replace("%struct.", "%")

        # XXX slowwwwwww
        for x in skip_lines:
            if line.find(x) >= 0:
                line = ''
                break

        # strip comments
        comment = line.find(';')
        if comment >= 0:
            line = line[:comment]
        line = line.rstrip()

        # find function names, declare them with the default calling convertion
        #if '(' in  line and line[-1:] == '{':
        #   returntype, s = line.split(' ', 1)
        #   funcname  , s = s.split('(', 1)
        #   funcnames[funcname] = True
        #   if line.find("internal") == -1:
        #        if funcname not in ["@main", "@ctypes_RPython_StartupCode"]:
        #            internal = 'internal '
        #            line = '%s%s %s' % (internal, default_cconv, line,)
        ll_lines.append(line)

    # patch calls to function that we just declared with different cconv
    ll_lines2, calltag, declaretag, definetag = [], 'call ', 'declare ', 'define ' 
    for line in ll_lines:
        i = line.find(calltag)
        if i >= 0:
            cconv = 'ccc'
            for funcname in funcnames.iterkeys():
                if line.find(funcname) >= 0:
                    cconv = default_cconv
                    break
            line = "%scall %s %s" % (line[:i], cconv, line[i+len(calltag):])
        if line[:len(declaretag)] == declaretag:
            cconv = 'ccc'
            for funcname in funcnames.keys():
                if line.find(funcname) >= 0:
                    cconv = default_cconv
                    break
            line = "declare %s %s" % (cconv, line[len(declaretag):])
        if line[:len(definetag)] == definetag:
            line = line.replace("internal ", "")
            cconv = 'ccc'
            for funcname in funcnames.keys():
                if line.find(funcname) >= 0:
                    cconv = default_cconv
                    break
            line = "define %s %s" % (cconv, line[len(definetag):])
        ll_lines2.append(line)

    ll_lines2.append("declare ccc void @abort()")
    return'\n'.join(ll_lines2)

def find_list_of_str(rtyper):
    from pypy.rpython.lltypesystem import rlist
    for r in rtyper.reprs.itervalues():
        if isinstance(r, rlist.ListRepr) and r.item_repr is rstr.string_repr:
            return r.lowleveltype.TO
    return None

def setup_externs(c_db, db):
    # hacks to make predeclare_all work    

    rtyper = db.translator.rtyper
    decls = list(predeclare_stuff(c_db))
    
    for c_name, obj in decls:
        if isinstance(obj, lltype.LowLevelType):
            db.prepare_type(obj)
        elif isinstance(obj, FunctionGraph):
            funcptr = rtyper.getcallable(obj)
            c = inputconst(lltype.typeOf(funcptr), funcptr)
            db.prepare_arg_value(c)
        elif isinstance(lltype.typeOf(obj), lltype.Ptr):
            db.prepare_constant(lltype.typeOf(obj), obj)
        elif type(c_name) is str and type(obj) is int:
            pass    #define c_name obj
        else:
            assert False, "unhandled predeclare %s %s %s" % (c_name, type(obj), obj)

    def annotatehelper(func, *argtypes):
        graph = db.translator.rtyper.annotate_helper(func, argtypes)
        fptr = rtyper.getcallable(graph)
        c = inputconst(lltype.typeOf(fptr), fptr)
        db.prepare_arg_value(c)
        decls.append(("ll_" + func.func_name, graph))
        return graph.name

    return decls

def get_c_cpath():
    from pypy.translator.c import genc
    return os.path.dirname(genc.__file__)

def get_llvm_cpath():
    return os.path.join(os.path.dirname(__file__), "module")

def get_incdirs():

    import distutils.sysconfig
    includes = (distutils.sysconfig.EXEC_PREFIX + "/include", 
                distutils.sysconfig.EXEC_PREFIX + "/include/gc",
                distutils.sysconfig.get_python_inc(),
                get_c_cpath(),
                get_llvm_cpath())

    includestr = ""
    for ii in includes:
        includestr += "-I %s " % ii
    return includestr

def generate_llfile(db, extern_decls, entrynode, c_includes, c_sources, standalone, default_cconv):
    ccode = []
    function_names = []
        
    def predeclarefn(c_name, llname):
        function_names.append(llname)
        assert llname[0] == "@"
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
            pass

        elif type(c_name) is str and type(obj) is int:
            ccode.append("#define\t%s\t%d\n" % (c_name, obj))

        else:
            assert False, "unhandled extern_decls %s %s %s" % (c_name, type(obj), obj)


    # include this early to get constants and macros for any further includes
    ccode.append('#include <Python.h>\n')

    # ask gcpolicy for any code needed
    ccode.append('%s\n' % db.gcpolicy.genextern_code())

    for c_include in c_includes:
        ccode.append('#include <%s>\n' % c_include)
        
    for c_source in c_sources:
        ccode.append('\n')
        for l in c_source:
            ccode.append(l + '\n') 
    ccode.append('\n')

    # append our source file
    ccode.append(open(get_module_file('genexterns.c')).read())
    llcode = get_ll("".join(ccode), function_names, default_cconv)
    return llcode
