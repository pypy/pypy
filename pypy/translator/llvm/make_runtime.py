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
    ops = ["llvm-gcc -c %s -o %s" % (cfile, bytecode),
           "llvm-dis %s -f" % bytecode]
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
                    continue
        else:
            ret.append(line)
    return "\n".join(ret)

def remove_alternatives(code):
    for i in range(1, 10):
        code = code.replace("_ALTERNATIVE%i" % i, "")
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

def cleanup_code(code):
    code = remove_comments(code)
    code = add_std(code)
    code = remove_header(code)
    code = internal_functions(code)
    code = remove_alternatives(code)
    return code

def make_list_template():
    code = get_llvm_code("list.c")
    code = cleanup_code(code)
    code = code.replace("%struct.list", "%std.list.%(name)s")
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

if __name__ == '__main__':
    make_list_template()
    make_int_list()

