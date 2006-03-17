import autopath
import py
import sys
from distutils.core import setup
from distutils.extension import Extension

prefix = py.path.local.sysfind("llvm-as").dirpath('..').realpath()
incdir = prefix.join('include')
libdir = prefix.join('lib')

# get all the libraries llvm needs
platform2backend = {'darwin':'PowerPC', 'linux2':'X86'}
llvm_libs = [platform2backend[sys.platform]] + """
Core AsmParser CodeGen SelectionDAG ExecutionEngine
JIT bzip2 Interpreter DataStructure BCWriter BCReader Target Instrumentation
ipo ipa Transforms System ScalarOpts Analysis TransformUtils Support""".split()

# figure out if they are a dynamic library or not
extra_llvm_libs, extra_llvm_dynlibs = [], []
for o in llvm_libs:
    if libdir.join("LLVM%s.o" % o).check():
        extra_llvm_libs.append(libdir.join("LLVM%s.o" % o).strpath)
    else:
        extra_llvm_dynlibs.append("LLVM%s" % o)

# globals
name = 'pyllvm'
sources = ['pyllvm.cpp']
include_dirs = [incdir.strpath]
library_dirs = [libdir.strpath]
define_macros = [('__STDC_LIMIT_MACROS', None)] #, ('_GNU_SOURCE', None)

opts = dict(name=name,
            sources=sources,
            libraries=extra_llvm_dynlibs,
            include_dirs=include_dirs,
            library_dirs=library_dirs,
            define_macros=define_macros,
            extra_objects=extra_llvm_libs)

ext_modules = Extension(**opts)

# setup module
setup(name=name, ext_modules=[ext_modules])
