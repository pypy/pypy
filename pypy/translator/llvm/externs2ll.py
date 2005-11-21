import os
import sys
import types
import urllib

from pypy.rpython.rmodel import inputconst, getfunctionptr
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
    ]

def get_ll(ccode, function_names):
    function_names += support_functions
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
                if funcname != "%main":
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

def generate_llfile(db, extern_decls, entrynode):
    ccode = []
    function_names = []
        
    def predeclarefn(c_name, llname):
        function_names.append(llname)
        assert llname[0] == "%"
        llname = llname[1:]
        assert '\n' not in llname
        ccode.append('#define\t%s\t%s\n' % (c_name, llname))

    # special case name entry_point XXX bit underhand
    for k, v in db.obj2node.items():
        try:
            if isinstance(lltype.typeOf(k), lltype.FuncType):
                if v == entrynode and k._name == "entry_point":
                    predeclarefn("__ENTRY_POINT__", v.get_ref())
                    ccode.append('#define ENTRY_POINT_DEFINED 1\n\n')
                    break
        except TypeError, exc:
            pass

    for c_name, obj in extern_decls:
        if isinstance(obj, lltype.LowLevelType):
            s = "#define %s struct %s\n%s;\n" % (c_name, c_name, c_name)
            ccode.append(s)
        elif isinstance(obj, types.FunctionType):
            funcptr = getfunctionptr(db.translator, obj)
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
    src = open(path_join(os.path.dirname(__file__),
                         "module",
                         "genexterns.c")).read()

    # set python version to include
    if sys.platform == 'darwin':
        python_h = '"/System/Library/Frameworks/Python.framework/Versions/2.3/include/python2.3/Python.h"'
    else:
        python_h = '<python2.3/Python.h>'
    src = src.replace('__PYTHON_H__', python_h)
               
    # add our raising ops
    s = open(path_join(os.path.dirname(__file__),
                       "module",
                       "raisingop.h")).read()
    src = src.replace('__RAISING_OPS__', s)
                    
    
    from pypy.translator.c import extfunc
    src_path = path_join(os.path.dirname(extfunc.__file__), "src")

    include_files = [path_join(src_path, f + ".h") for f in
                        ["thread", "ll_os", "ll_math", "ll_time",
                         "ll_strtod", "ll_thread", "stack"]]
    
    includes = []
    for f in include_files:
        s = open(f).read()

        # XXX this is getting a tad (even more) ridiculous            
        for name in ["ll_osdefs.h", "thread_pthread.h"]:
            include_str = '#include "%s"' % name
            if s.find(include_str) >= 0:
                s2 = open(path_join(src_path, name)).read()
                s = s.replace(include_str, s2)

        includes.append(s)

    src = src.replace('__INCLUDE_FILES__', "".join(includes))
    ccode.append(src)
    ccode = "".join(ccode)
    
    return get_ll(ccode, function_names)
