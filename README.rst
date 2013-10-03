==============================================
Unipycation: A Language Composition Experiment
==============================================

Unipycation is an experimental composition of a Python interpreter (PyPy
http://pypy.org/) and a Prolog interpreter (Pyrolog by Carl Friedrich
Bolz https://bitbucket.org/cfbolz/pyrolog). The languages are composed
using RPython, meaning that the entire composition is meta-traced.

The goal of the project is to identify the challenges associated with composing 
programming languages whose paradigms differ vastly and to evaluate RPython as
a language composition platform.

Building
========

Check out pyrolog somewhere::

    $ hg clone https://bitbucket.org/cfbolz/pyrolog-unipycation

Add pyrolog to the PYTHONPATH::

    $ export PYTHONPATH=/path/to/pyrolog/checkout

Get the unipycation sources::

    $ hg clone https://bitbucket.org/vext01/pypy

Switch into the unipycation branch::

    $ hg update -C unipycation

And begin translation::

    $ rpython/bin/rpython -Ojit pypy/goal/targetpypystandalone.py --withmod-unipycation

On a 64-bit architecture this process will consume about 8GB of memory at peak.

The resulting pypy-c binary is the composed Python/Prolog compiler.

Using Unipycation
=================

For the moment, the languages are composed without any adjustments to
syntax. In other words, communication between Python and Prolog is in
the form of an API. Better syntactic composition will come later.

The interface is described in a paper which will (hopefully) appear in
VMIL'13. Until then, the source code is the documentation. A good place to
start is the unit tests in ``pypy/module/unipycation/test/``.

Authors
=======

Unipycation is authored by Edd Barrett and Carl Friedrich Bolz.
