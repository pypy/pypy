==================
Backends for cppyy
==================

The cppyy module needs a backend to provide the C++ reflection information on
which the Python bindings are build.
The backend is called through a C-API, which can be found in the PyPy sources
in: `pypy/module/cppyy/include/capi.h`_.
There are two kinds of API calls: querying about reflection information, which
are used during the creation of Python-side constructs, and making the actual
calls into C++.
The objects passed around are all opaque: cppyy does not make any assumptions
about them, other than that the opaque handles can be copied.
Their definition, however, appears in two places: in the C code (in capi.h),
and on the RPython side (in `capi_types.py`_), so if they are changed, they
need to be changed on both sides.

.. _`pypy/module/cppyy/include/capi.h`: https://bitbucket.org/pypy/pypy/src/default/pypy/module/cppyy/include/capi.h
.. _`capi_types.py`: https://bitbucket.org/pypy/pypy/src/default/pypy/module/cppyy/capi/capi_types.py

There are two places where selections in the RPython code affect the choice
(and use) of the backend.
The first is in `pypy/module/cppyy/capi/__init__.py`_::

    # choose C-API access method:
    from pypy.module.cppyy.capi.loadable_capi import *
    #from pypy.module.cppyy.capi.builtin_capi import *

The default is the loadable C-API.
Comment it and uncomment the builtin C-API line, to use the builtin version.

.. _`pypy/module/cppyy/capi/__init__.py`:  https://bitbucket.org/pypy/pypy/src/default/pypy/module/cppyy/capi/__init__.py

Next, if the builtin C-API is chosen, the specific backend needs to be set as
well (default is Reflex).
This second choice is in `pypy/module/cppyy/capi/builtin_capi.py`_::

    import reflex_capi as backend
    #import cint_capi as backend

After those choices have been made, built pypy-c as usual.

.. _`pypy/module/cppyy/capi/builtin_capi.py`:  https://bitbucket.org/pypy/pypy/src/default/pypy/module/cppyy/capi/builtin_capi.py

When building pypy-c from source, keep the following in mind.
If the loadable_capi is chosen, no further prerequisites are needed.
However, for the build of the builtin_capi to succeed, the ``ROOTSYS``
environment variable must point to the location of your ROOT (or standalone
Reflex in the case of the Reflex backend) installation, or the ``root-config``
utility must be accessible through ``$PATH`` (e.g. by adding ``$ROOTSYS/bin``
to ``PATH``).
In case of the former, include files are expected under ``$ROOTSYS/include``
and libraries under ``$ROOTSYS/lib``.
