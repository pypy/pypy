import os
import types
import urllib

from pypy.rpython.rmodel import inputconst, getfunctionptr
from pypy.rpython import lltype
from pypy.translator.llvm.codewriter import CodeWriter, \
     DEFAULT_TAIL, DEFAULT_CCONV

from pypy.tool.udir import udir


def get_ll(ccode, function_names):
    
    # goto codespeak and compile our c code
    request = urllib.urlencode({'ccode':ccode})
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
                line = '%s %s' % (DEFAULT_CCONV, line,)
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
    return llcode.split('implementation')


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
    # append local file
    j = os.path.join
    include_files.append(j(j(os.path.dirname(__file__), "module"), "genexterns.c"))

    from pypy.translator.c import extfunc
    for f in ["ll_os", "ll_math", "ll_time", "ll_strtod"]:
        include_files.append(j(j(os.path.dirname(extfunc.__file__), "src"), f + ".h"))

    for f in include_files:
        ccode.append(open(f).read())

    if debug:
        ccode = "".join(ccode)
        filename = udir.join("ccode.c")
        f = open(str(filename), "w")
        f.write(ccode)
        f.close()
    
    return get_ll(ccode, function_names + support_functions)
