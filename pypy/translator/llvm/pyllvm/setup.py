import autopath
import py

from distutils.core import setup
from distutils.extension import Extension

import os
import glob

# XXX make libdir configurable
#libdir = py.path.local("/usr/local/lib/")
libdir = py.path.local(__file__).dirpath().join("libs")

# get all the extra objects llvm needs
extra_objects = """
LLVMX86.o
LLVMSystem.o
LLVMSupport.o
LLVMCore.o
LLVMAsmParser.o
LLVMCodeGen.o
LLVMSelectionDAG.o
LLVMExecutionEngine.o
LLVMJIT.o
LLVMScalarOpts.o
LLVMbzip2.o

LLVMInterpreter.o
LLVMAnalysis.o
LLVMipo.o
LLVMTransformUtils.o
LLVMipa.o
LLVMDataStructure.o
LLVMTransforms.o
LLVMInstrumentation.o
LLVMBCWriter.o
LLVMBCReader.o
""".split()

# globals
name = 'pyllvm'
sources = ['pyllvm.cpp']
libraries = ["LLVMTarget"]
include_dirs = ['/opt/projects/llvm-1.6/build/include']
library_dirs = [str(libdir)]
define_macros = [('_GNU_SOURCE', None), ('__STDC_LIMIT_MACROS', None)]
extra_objects = [str(libdir.join(obj)) for obj in extra_objects]

opts = dict(name=name,
            sources=sources,
            libraries=libraries,
            include_dirs=include_dirs,
            library_dirs=library_dirs,
            define_macros=define_macros,
            extra_objects=extra_objects)

ext_modules = Extension(**opts)

# setup module
setup(name=name, ext_modules=[ext_modules])

# bunch of unused object (at the moment or for x86)
unused_objects = """
LLVMSkeleton.o
LLVMProfilePaths.o
LLVMCBackend.o
LLVMDebugger.o
profile_rt.o
trace.o
gcsemispace.o
LLVMSparcV8.o
LLVMSparcV9.o
LLVMSparcV9InstrSched.o
LLVMSparcV9LiveVar.o
LLVMSparcV9ModuloSched.o
LLVMSparcV9RegAlloc.o
LLVMPowerPC.o
LLVMAlpha.o
LLVMIA64.o
sample.o
stkr_compiler.o
LLVMTarget.o
"""

