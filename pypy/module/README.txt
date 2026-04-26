This directory contains PyPy's builtin module implementation
that requires access to the interpreter level.  See here
for more information: 

    https://doc.pypy.org/coding-guide.html#modules-in-pypy

ATTENTION: don't put any '.py' files directly into pypy/module 
because you can easily get import mixups on e.g. "import sys" 
then (Python tries relative imports first). 
