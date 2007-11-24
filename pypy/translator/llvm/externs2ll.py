import os
import sys
import types
import urllib

from pypy.objspace.flow.model import FunctionGraph
from pypy.rpython.rmodel import inputconst
from pypy.rpython.lltypesystem import lltype
from pypy.translator.llvm.buildllvm import llvm_gcc_version
from pypy.tool.udir import udir

support_functions = [
    "@LLVM_RPython_StartupCode",
    ]

def get_module_file(name):
    return os.path.join(get_llvm_cpath(), name)

def get_ll(ccode, function_names, default_cconv, c_include_dirs):
    function_names += support_functions
    filename = str(udir.join("ccode.c"))
    f = open(filename, "w")
    f.write(ccode)
    f.close()

    plain = filename[:-2]
    includes = get_incdirs(c_include_dirs)
    if llvm_gcc_version() < 4.0:
        emit_llvm = ''
    else:
        emit_llvm = '-emit-llvm -O0'
        
    cmd = "llvm-gcc %s %s -S %s.c -o %s.ll 2>&1" % (
        includes, emit_llvm, plain, plain)

    if os.system(cmd) != 0:
        raise Exception("Failed to run '%s'" % cmd)

    llcode = open(plain + '.ll').read()

    # strip lines
    ll_lines = []
    funcnames = dict([(k, True) for k in function_names])

    # strip declares that are in funcnames
    for line in llcode.split('\n'):

        # get rid of any of the structs that llvm-gcc introduces to struct types
        line = line.replace("%struct.", "%")

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

def get_c_cpath():
    from pypy.translator.c import genc
    return os.path.dirname(genc.__file__)

def get_llvm_cpath():
    return os.path.join(os.path.dirname(__file__), "module")

def get_incdirs(c_include_dirs):

    c_include_dirs

    import distutils.sysconfig

    includes = tuple(c_include_dirs) + ("/sw/include",
                distutils.sysconfig.EXEC_PREFIX + "/include", 
                distutils.sysconfig.EXEC_PREFIX + "/include/gc",
                distutils.sysconfig.get_python_inc(),
                get_c_cpath(),
                get_llvm_cpath())

    includestr = ""
    for ii in includes:
        includestr += "-I %s " % ii
    return includestr

def generate_llfile(db, entrynode, c_include_dirs, c_includes, c_sources, standalone, default_cconv):
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

    # ask gcpolicy for any code needed
    ccode.append('%s\n' % db.gcpolicy.genextern_code())

    # ask rffi for includes/source
    for c_include in c_includes:
        ccode.append('#include <%s>\n' % c_include)
        
    for c_source in c_sources:
        ccode.append('\n')
        ccode.append(c_source + '\n') 
    ccode.append('\n')

    # append our source file
    ccode.append(open(get_module_file('genexterns.c')).read())
    llcode = get_ll("".join(ccode), function_names, default_cconv, c_include_dirs)
    return llcode
