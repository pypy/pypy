from distutils.core import setup
from distutils.extension import Extension
from os import popen

#Create llvm c api library by running "python setup.py build_ext -i" here

cxxflags = popen('llvm-config --cxxflags').readline().split()
ldflags  = popen('llvm-config --ldflags').readline().split()
libs     = popen('llvm-config --libs all').readline().split()

opts = dict(name='libllvmjit',
            sources=['lib/libllvmjit.cpp'],
            libraries=[],
            include_dirs =["include"] + [f[2:] for f in cxxflags if f.startswith('-I')],
            library_dirs =[f[2:] for f in ldflags  if f.startswith('-L')],
            define_macros=[(f[2:], None) for f in cxxflags if f.startswith('-D')],
            extra_objects=libs)

ext_modules = Extension(**opts)

setup(name=opts['name'], ext_modules=[ext_modules])
