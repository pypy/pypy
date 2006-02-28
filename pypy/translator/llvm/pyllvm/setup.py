from distutils.core import setup
from distutils.extension import Extension
import os
import glob
sources = ['pyllvm.cpp']

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

unused = """
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

extra_objects = ["/usr/local/lib/" + name for name in extra_objects]

libs = ["LLVMTarget"]
#for fn in glob.glob("/usr/local/lib/*.a"):
#    fn = os.path.basename(fn)
#    if 'LLVM' in fn:
#        libs.append(os.path.splitext(fn[len("lib"):])[0])
    
includes = ['/opt/projects/llvm-1.6/build/include']
defs = [('_GNU_SOURCE', None),
        ('__STDC_LIMIT_MACROS', None),
        ]

setup(name             = 'pyllvm',
      version          = '0.0',
      ext_modules = [Extension(name = 'pyllvm',
                               define_macros=defs,
                               sources = sources,
                               include_dirs = includes,
                               libraries = libs,
                               extra_objects = extra_objects)])
