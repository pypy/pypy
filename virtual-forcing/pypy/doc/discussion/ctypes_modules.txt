what is needed for various ctypes-based modules and how feasible they are
==========================================================================

Quick recap for module evaluation:

1. does the module use callbacks?

2. how sophisticated ctypes usage is (accessing of _objects?)

3. any specific tricks

4. does it have tests?

5. dependencies

6. does it depend on cpython c-api over ctypes?

Pygame
======

1. yes, for various things, but basic functionality can be achieved without

2. probably not

3. not that I know of

4. yes for tests, no for unittests

5. numpy, but can live without, besides only C-level dependencies. On OS/X
   it requires PyObjC.

6. no


PyOpenGL
========

1. yes, for GLX, but not for the core functionality

2. probably not

3. all the code is auto-generated

4. it has example programs, no tests

5. numpy, but can live without it. can use various surfaces (including pygame) to draw on

6. no


Sqlite
======

1. yes, but I think it's not necessary

2. no

3. no

4. yes

5. datetime

6. it passes py_object around in few places, not sure why (probably as an
   opaque argument).
