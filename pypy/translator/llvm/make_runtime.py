"""
This file produces the .ll files with the implementations of lists and the
implementations of simple space operations (like add, mul, sub, div for float,
bool, int).
"""

import autopath

import os
from pypy.tool.udir import udir
from py.process import cmdexec 
from py import path 

def get_llvm_code(cfile):
    include_dir = autopath.this_dir
    print "include_dir", include_dir
    cfile = include_dir + "/" + cfile
    print cfile 
    bytecode = udir.join("temp.bc")
    lastdir = path.local()
    ops = ["llvm-gcc -enable-correct-eh-support-O3 -c %s -o %s" % \
           (cfile, bytecode), "llvm-dis %s -f" % bytecode]
    for op in ops:
        print op
        cmdexec(op)
    f = udir.join("temp.ll").open("r")
    return f.read()

def remove_comments(code):
    ret = []
    for line in code.split("\n"):
        line = line.split(";")
        ret.append(line[0].rstrip())
    return "\n".join(ret)

def add_std(code):
    with_std = []
    functions = []
    for line in code.split("\n"):
        if "{" in line and "(" in line and ")" in line:
            s1 = line.split("(")
            s2 = s1[0].split("%")
            functions.append(s2[-1])
            s2[-1] = "std." + s2[-1]
            s2 = "%".join(s2)
            s1[0] = s2
            with_std.append("(".join(s1))
        else:
            with_std.append(line)
    ret = []
    for line in with_std:
        if "call" in line:
            for f in functions:
                if f in line:
                    line = line.replace(f, "std." + f)
                    ret.append(line)
                    break
            else:
                ret.append(line)
        else:
            ret.append(line)
    return "\n".join(ret)

def remove_alternatives(code):
    for i in range(1, 10):
        code = code.replace("_ALTERNATIVE%i" % i, "")
    return code

def create_exceptions(code):
    code = code.replace("%LAST_EXCEPTION_TYPE", "%std.last_exception.type")
    code = code.replace("%INDEX_ERROR", "%glb.class.IndexError.object")
    return code

def remove_exception(code):
    code = code.replace("_EXCEPTION", ".exc")
    return code

def remove_header(code):
    code = code.split("implementation")
    return code[1]

def internal_functions(code):
    ret = []
    for line in code.split("\n"):
        if "{" in line and "(" in line and ")" in line:
            ret.append("internal " + line)
        else:
            ret.append(line)
    return "\n".join(ret)

def create_unwind(code):
    ret = []
    remove = False
    for line in code.split("\n"):
        if "call" in line and "%unwind(" in line:
            ret.append("\tunwind")
            remove = True
        elif "declare" in line and "unwind" in line:
            pass
        elif remove:
            if not line.startswith("\t") and ":" in line:
                remove = False
                ret.append(line)
        else:
            ret.append(line)
    return "\n".join(ret)

def remove_structs(code):
    code = code.replace("struct.class", "std.class")
    return code

def cleanup_code(code):
    code = remove_comments(code)
    code = add_std(code)
    code = remove_header(code)
    code = internal_functions(code)
    code = remove_alternatives(code)
    code = create_exceptions(code)
    code = remove_exception(code)
    code = remove_structs(code)
    code = create_unwind(code)
    return code

def make_list_template():
    code = get_llvm_code("list.c")
    code = cleanup_code(code)
    code = code.replace("%struct.list", "%(name)s")
    code = code.replace("%struct.item*", "%(item)s")
    f = open(autopath.this_dir + "/list_template.ll", "w")
    print (autopath.this_dir + "/list_template.ll")
    f.write(code)
    f.close()

def make_int_list():
    code = get_llvm_code("intlist.c")
    code = cleanup_code(code)
    code = code.replace("struct.list_int", "std.list.int")
    f = open(autopath.this_dir + "/int_list.ll", "w")
    print (autopath.this_dir + "/int_list.ll")
    f.write(code)
    f.close()

MAP_ARITHM_OPS = [("add",              ("add", None,     None)),
                  ("inplace_add",      ("add", None,     None)),
                  ("sub",              ("sub", None,     None)),
                  ("inplace_sub",      ("sub", None,     None)),
                  ("mul",              ("mul", None,     None)),
                  ("inplace_mul",      ("mul", None,     None)),
                  ("div",              ("div", None,     None)),
                  ("inplace_div",      ("div", None,     None)),
                  ("floordiv",         ("div", "int",    None)),
                  ("inplace_floordiv", ("div", "int",    None)),
                  ("truediv",          ("div", "double", "double")),
                  ("inplace_truediv",  ("div", "double", "double")),
                  ("mod",              ("rem", None,     None)),
                  ("inplace_mod",      ("rem", None,     None))
                  ]

MAP_LOGICAL_OPS = [("and_",             ("and", None,     None)),
                   ("inplace_and",      ("and", None,     None)),
                   ("or_",              ("or",  None,     None)),
                   ("inplace_or",       ("or",  None,     None)),
                   ("xor",              ("xor", None,     None)),
                   ("inplace_xor",      ("xor", None,     None))
                   ]

MAP_COMPAR_OPS = [("is_", "seteq"),
                  ("eq", "seteq"),
                  ("lt", "setlt"),
                  ("le", "setle"),
                  ("ge", "setge"),
                  ("gt", "setgt")]

types = ((0, "double"), (1, "uint"), (2, "int"), (3, "bool"))

def make_binary_ops():
    code = ["implementation\n"]
    def normalize_type(t1, t, var):
        if t1 != t:
            code.append("\t%%%s = cast %s %%%s to %s\n" % (var, t1, var, t))
    for type1 in types:
        for type2 in types:
            #Arithmetic operators
            for op, (llvmop, calctype, rettype) in MAP_ARITHM_OPS:
                if calctype is None:
                    calctype = min(type1, type2)[1]
                if rettype is None:
                    rettype = min(type1, type2)[1]
                if calctype == "bool":
                    calctype = rettype = "int"
                code.append("internal %s %%std.%s(%s %%a, %s %%b) {\n" %
                            (rettype, op, type1[1], type2[1]))
                normalize_type(type1[1], calctype, "a")
                normalize_type(type2[1], calctype, "b")
                code.append("\t%%r = %s %s %%a, %%b\n" %
                            (llvmop, calctype))
                normalize_type(calctype, rettype, "r")
                code.append("\tret %s %%r\n}\n\n" % rettype)
            calctype = min(type1, type2)[1]
            #Comparison operators
            for op, llvmop in MAP_COMPAR_OPS:
                code.append("internal bool %%std.%s(%s %%a, %s %%b) {\n" %
                            (op, type1[1], type2[1]))
                normalize_type(type1[1], calctype, "a")
                normalize_type(type2[1], calctype, "b")
                code.append("\t%%r = %s %s %%a, %%b\n" %
                            (llvmop, calctype))
                code.append("\tret bool %r\n}\n\n")
            code.append("internal bool %%std.neq(%s %%a, %s %%b) {\n" %
                            (type1[1], type2[1]))
            normalize_type(type1[1], calctype, "a")
            normalize_type(type2[1], calctype, "b")
            code.append("\t%%r = %s %s %%a, %%b\n" %
                        (llvmop, calctype))
            code.append("\t%r1 = xor bool %r, true\n\tret bool %r1\n}\n\n")
    #Logical operators
    for type1 in types[1:]:
        for type2 in types[1:]:
            for op, (llvmop, calctype, rettype) in MAP_LOGICAL_OPS:
                if calctype is None:
                    calctype = min(type1, type2)[1]
                if rettype is None:
                    rettype = min(type1, type2)[1]
                code.append("internal %s %%std.%s(%s %%a, %s %%b) {\n" %
                            (rettype, op, type1[1], type2[1]))
                normalize_type(type1[1], calctype, "a")
                normalize_type(type2[1], calctype, "b")
                code.append("\t%%r = %s %s %%a, %%b\n" %
                            (llvmop, calctype))
                normalize_type(calctype, rettype, "r")
                code.append("\tret %s %%r\n}\n\n" % rettype)
    #Shift
    for type1 in types[1:-1]:
        for type2 in types[1:-1]:
            for op, llvmop in (("lshift", "shl"), ("rshift", "shr")):
                code.append("internal %s %%std.%s(%s %%a, %s %%b) {\n" %
                            (type1[1], op, type1[1], type2[1]))
                code.append("\t%%b = cast %s %%b to ubyte\n" % type2[1])
                code.append("\t%%r = %s %s %%a, ubyte %%b\n" %
                            (llvmop, type1[1]))
                code.append("\tret %s %%r\n}\n\n" % type1[1])
    return code

def make_unary_ops():
    code = []
    def normalize_type(t1, t, var):
        if t1 != t:
            code.append("\t%%%s = cast %s %%%s to %s\n" % (var, t1, var, t))
    for type1 in types:
        #"casts" int, bool
        for type2 in ("int", "bool"):
            code.append("internal %s %%std.%s(%s %%a) {\n" %
                        (type2, type2, type1[1]))
            code.append("\t%%r = cast %s %%a to %s\n" % (type1[1], type2))
            code.append("\tret %s %%r\n}\n\n" % type2)
        #is_true
        code.append("internal bool %%std.is_true(%s %%a) {\n" % type1[1])
        code.append("\t%%r = cast %s %%a to bool\n" % type1[1])
        code.append("\tret bool %r\n}\n\n")
    return code
            
                
def make_operations():
    code = make_binary_ops()
    code += make_unary_ops()
    f = open(autopath.this_dir + "/operations.ll", "w")
    f.write("".join(code))
    f.close()

if __name__ == '__main__':
    make_operations()
    make_list_template()
    make_int_list()

