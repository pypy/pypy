#
#   Pyrex - Darwin system interface
#

verbose = 0

import os
from Pyrex.Utils import replace_suffix
from Pyrex.Compiler.Errors import PyrexError

py_include_dirs = [
    "/Library/Frameworks/Python.framework/Headers"
]

compiler = "gcc"
compiler_options = \
    "-g -c -fno-strict-aliasing -Wno-long-double -no-cpp-precomp " \
    "-mno-fused-madd -fno-common -dynamic" \
    .split()

linker = "gcc"
linker_options = \
    "-Wl,-F.,-w -bundle -framework Python" \
    .split()

class CCompilerError(PyrexError):
    pass

def c_compile(c_file, verbose_flag = 0):
    #  Compile the given C source file to produce
    #  an object file. Returns the pathname of the
    #  resulting file.
    c_file = os.path.join(os.getcwd(), c_file)
    o_file = replace_suffix(c_file, ".o")
    include_options = []
    for dir in py_include_dirs:
        include_options.append("-I%s" % dir)
    args = [compiler] + compiler_options + include_options + [c_file, "-o", o_file]
    if verbose_flag or verbose:
        print " ".join(args)
    status = os.spawnvp(os.P_WAIT, compiler, args)
    if status <> 0:
        raise CCompilerError("C compiler returned status %s" % status)
    return o_file

def c_link(obj_file, verbose_flag = 0):
    return c_link_list([obj_file], verbose_flag)

def c_link_list(obj_files, verbose_flag = 0):
    #  Link the given object files into a dynamically
    #  loadable extension file. Returns the pathname
    #  of the resulting file.
    out_file = replace_suffix(obj_files[0], ".so")
    args = [linker] + linker_options + obj_files + ["-o", out_file]
    if verbose_flag or verbose:
        print " ".join(args)
    status = os.spawnvp(os.P_WAIT, linker, args)
    if status <> 0:
        raise CCompilerError("Linker returned status %s" % status)
    return out_file
