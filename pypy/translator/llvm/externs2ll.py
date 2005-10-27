import os
import sys
import types
import urllib

from pypy.rpython.rmodel import inputconst, getfunctionptr
from pypy.rpython.lltypesystem import lltype
from pypy.translator.llvm.codewriter import DEFAULT_CCONV

from pypy.tool.udir import udir


def get_ll(ccode, function_names):
    filename = str(udir.join("ccode.c"))
    f = open(filename, "w")
    f.write(ccode)
    f.close()

    llvm_gcc = os.popen('which llvm-gcc 2>&1').read()
    if llvm_gcc and not llvm_gcc.startswith('which'):   #local llvm CFE available
        #log('using local llvm-gcc')
        plain = filename[:-2]
        os.system("llvm-gcc -S %s.c -o %s.ll 2>&1" % (plain, plain))
        llcode = open(plain + '.ll').read()
    else:   #as fallback use remove CFE. XXX local and remote should be similar machines!
        #log('falling back on remote llvm-gcc')
        request = urllib.urlencode({'ccode':ccode}) # goto codespeak and compile our c code
        llcode = urllib.urlopen('http://codespeak.net/pypy/llvm-gcc.cgi', request).read()

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
        if line[-1:] == '{':
           returntype, s = line.split(' ', 1)
           funcname  , s = s.split('(', 1)
           funcnames[funcname] = True
           if line.find("internal") == -1:
                #internal = ''
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
    impl += """;functions that should return a bool according to
    ; pypy/rpython/extfunctable.py  , but C doesn't have bools!

internal fastcc bool %LL_os_isatty(int %fd) {
    %t = call fastcc int %LL_os_isatty(int %fd)
    %b = cast int %t to bool
    ret bool %b
}
internal fastcc bool %LL_stack_too_big() {
    %t = call fastcc int %LL_stack_too_big()
    %b = cast int %t to bool
    ret bool %b
}
    """
    return decl, impl


def post_setup_externs(db):
    rtyper = db.translator.rtyper
    from pypy.translator.c.extfunc import predeclare_all

    # hacks to make predeclare_all work
    db.standalone = True
    db.externalfuncs = {}
    decls = list(predeclare_all(db, rtyper))

    for c_name, obj in decls:
        if isinstance(obj, lltype.LowLevelType):
            db.prepare_type(obj)
        elif isinstance(obj, types.FunctionType):
            funcptr = getfunctionptr(db.translator, obj)
            c = inputconst(lltype.typeOf(funcptr), funcptr)
            db.prepare_arg_value(c)
        elif isinstance(lltype.typeOf(obj), lltype.Ptr):
            db.prepare_constant(lltype.typeOf(obj), obj)
        else:
            assert False, "unhandled predeclare %s %s %s" % (c_name, type(obj), obj)

    return decls


def path_join(root_path, *paths):
    path = root_path
    for p in paths:
        path = os.path.join(path, p)
    return path

def generate_llfile(db, extern_decls, support_functions, debug=False):
    ccode = []
    function_names = []

    def predeclarefn(c_name, llname):
        function_names.append(llname)
        assert llname[0] == "%"
        llname = llname[1:]
        assert '\n' not in llname
        ccode.append('#define\t%s\t%s\n' % (c_name, llname))

    for c_name, obj in extern_decls:
        if isinstance(obj, lltype.LowLevelType):
            s = "#define %s struct %s\n%s;\n" % (c_name, c_name, c_name)
            ccode.append(s)
        elif isinstance(obj, types.FunctionType):
            funcptr = getfunctionptr(db.translator, obj)
            c = inputconst(lltype.typeOf(funcptr), funcptr)
            predeclarefn(c_name, db.repr_arg(c))
        elif isinstance(lltype.typeOf(obj), lltype.Ptr):
            if isinstance(lltype.typeOf(obj._obj), lltype.FuncType):
                predeclarefn(c_name, db.repr_name(obj._obj))

    include_files = []
    add = include_files.append 
    add(path_join(os.path.dirname(__file__), "module", "genexterns.c"))

    from pypy.translator.c import extfunc
    src_path = path_join(os.path.dirname(extfunc.__file__), "src")

    for f in ["ll_os", "ll_math", "ll_time", "ll_strtod", "stack"]:
        add(path_join(src_path, f + ".h"))

    for f in include_files:
        s = open(f).read()
        if f.find('genexterns.c') > 0:
            if sys.platform == 'darwin':
                python_h = '"/System/Library/Frameworks/Python.framework/Versions/2.3/include/python2.3/Python.h"'
            else:
                python_h = '<python2.3/Python.h>'
            s = s.replace('__PYTHON_H__', python_h)

        elif f.find("ll_os") > 0:
            # XXX this is getting a tad ridiculous
            ll_osdefs = open(path_join(src_path, "ll_osdefs.h")).read()
            s = s.replace('#include "ll_osdefs.h"', ll_osdefs)
            
        ccode.append(s)
    ccode = "".join(ccode)

    return get_ll(ccode, function_names + support_functions)
