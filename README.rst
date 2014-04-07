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

Bootstrap
=========

Run the setup script:

    $ python2.7 bootstrap.py all

You will need hg, git and the python modules 'sh' and 'vcstools'.

If you have PyPy installed, you can bootstrap unipycation faster by setting
the environment variable `TRANSLATE_WITH` to your PyPy binary.

On a 64-bit architecture the translation process will consume about 8GB of
memory at peak. The resulting pypy-c binary is the composed Python/Prolog
compiler.

If you are looking to bootstrap the other unipycation VMs too, then use the
universal bootstrapper, as found here:
https://bitbucket.org/softdevteam/unipycation-shared

Running
=======

First source `env.sh`:

    $ . ./env.sh

Then you can simply run `unipycation`.

Using Unipycation
=================

For the moment, the languages are composed without any adjustments to
syntax. In other words, communication between Python and Prolog is in
the form of an API. Better syntactic composition will come later.

The interface is described in the paper `Unipycation: A Case Study in
Cross-Language Tracing
<http://soft-dev.org/pubs/pdf/barrett_bolz_tratt__unipycation_a_study_in_cross_language_tracing.pdf>`_
which appeared in VMIL'13.

The interface is subject to change.

Unit Tests
==========

Unit tests are run as per the normal PyPy procedure. Please refer to
the PyPy docs.

Authors
=======

Unipycation is authored by Edd Barrett and Carl Friedrich Bolz.
