===================================================
(Semi)-transparent distribution of RPython programs
===================================================

Some (rough) ideas how I see distribution
-----------------------------------------

The main point about it, is to behave very much like JIT - not
to perform distribution on Python source code level, but instead
perform distribution of RPython source, and eventually perform
distribution of interpreter at the end.

This attempt gives same advantages as off-line JIT (any RPython based
interpreter, etc.) and gives nice field to play with different
distribution heuristics. This also makes eventually nice possibility 
of integrating JIT with distribution, thus allowing distribution
heuristics to have more information that they might have otherwise and
as well with specializing different nodes in performing different tasks.

Flow graph level
----------------

Probably the best place to perform distribution attempt is to insert
special graph distributing operations into low-level graphs (either lltype
or ootype based), which will allow distribution heuristic to decide
on entrypoint to block/graph/some other structure??? what variables/functions
are accessed inside some part and if it's worth transferring it over wire.

Backend level
-------------

Backends will need explicit support for distribution of any kind. Basically
it should be possible for backend to remotely call block/graph/structure
in any manner (it should strongly depend on backend possibilities).
