===============================================================================
PyPy With LLVM Targeting Backend for High Performant JIT Code Generation
===============================================================================

This repo contains the programming work I have done for my MSc Computer Science dissertation project. The project aims at building a backend in PyPy capable of generating LLVM IR that can then, hopefully, be compiled into much higher performing code than the existing native backends PyPy offers. This comes at the expense of greater JIT overhead, and so will ideally act as a second layer of optimisation for long running programs, like scientific or server code. 

The project will try to address the question of what type of optimisations offered by LLVM synergise best in the context of compiling multiple traces of a long running program together (ie a trace tree) and identify which have the highest reward to overhead ratios, constructing a pipeline of optimisation passes best suited to this context. The project will also discuss how best to handle tracing JIT specific features in a last layer of optimisation, like guard handling and bridge compilation, to minimise runtime overhead without harming performance. 

Ideally the research will be able to aid authors of tracing JITs to construct highly refined last layers of optimisation, with or without LLVM.

All code for the LLVM backend can be found at 'rpython/jit/backend/llvm/'

For information on PyPy specifically, see https://www.pypy.org/
