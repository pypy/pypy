
Welcome to PyPy Development
=============================================

The PyPy project aims at producing a flexible and fast Python_
implementation.  The guiding idea is to translate a Python-level
description of the Python language itself to lower level languages.
Rumors have it that the secret goal is being faster-than-C which is
nonsense, isn't it?  `more...`_

Getting into PyPy ... 
=============================================

* `Release 1.4`_: the latest official release

* `PyPy Blog`_: news and status info about PyPy 

* `Documentation`_: extensive documentation about PyPy.  

* `Getting Started`_: Getting started and playing with PyPy. 

* `Papers`_: Academic papers, talks, and related projects

* `Videos`_: Videos of PyPy talks and presentations

* `speed.pypy.org`_: Daily benchmarks of how fast PyPy is


Mailing lists, bug tracker, IRC channel
=============================================

* `Development mailing list`_: development and conceptual
  discussions. 

* `Mercurial commit mailing list`_: updates to code and
  documentation. 

* `Sprint mailing list`_: mailing list for organizing upcoming sprints. 

* `Development bug/feature tracker`_: filing bugs and feature requests. 

* **IRC channel #pypy on freenode**: Many of the core developers are hanging out 
  at #pypy on irc.freenode.net.  You are welcome to join and ask questions
  (if they are not already developed in the FAQ_).
  You can find logs of the channel here_.

.. XXX play1? 

Meeting PyPy developers
=======================

The PyPy developers are organizing sprints and presenting results at
conferences all year round. They will be happy to meet in person with
anyone interested in the project.  Watch out for sprint announcements
on the `development mailing list`_.

.. _Python: http://docs.python.org/index.html
.. _`more...`: architecture.html#mission-statement 
.. _`PyPy blog`: http://morepypy.blogspot.com/
.. _`development bug/feature tracker`: https://codespeak.net/issue/pypy-dev/ 
.. _here: http://tismerysoft.de/pypy/irc-logs/pypy
.. _`sprint mailing list`: http://codespeak.net/mailman/listinfo/pypy-sprint 
.. _`Mercurial commit mailing list`: http://codespeak.net/mailman/listinfo/pypy-svn
.. _`development mailing list`: http://codespeak.net/mailman/listinfo/pypy-dev
.. _`FAQ`: faq.html
.. _`Documentation`: docindex.html 
.. _`Getting Started`: getting-started.html
.. _`Papers`: extradoc.html
.. _`Videos`: video-index.html
.. _`Release 1.4`: http://pypy.org/download.html
.. _`speed.pypy.org`: http://speed.pypy.org

Detailed Documentation
======================

.. The following documentation is important and reasonably up-to-date:

.. extradoc: should this be integrated one level up: dcolish?


.. toctree::
   :maxdepth: 1

   getting-started.rst
   getting-started-python.rst
   getting-started-dev.rst
   windows.rst
   faq.rst
   architecture.rst
   coding-guide.rst
   cpython_differences.rst
   garbage_collection.rst
   interpreter.rst
   objspace.rst
   __pypy__-module.rst
   objspace-proxies.rst

   dev_method.rst
   extending.rst

   extradoc.rst
   video-index.rst

   glossary.rst

   contributor.rst

   interpreter-optimizations.rst
   configuration.rst
   parser.rst
   rlib.rst
   rtyper.rst
   rffi.rst
   
   translation.rst
   jit/index.rst
   jit/overview.rst
   jit/pyjitpl5.rst

   index-of-release-notes.rst

   ctypes-implementation.rst

   how-to-release.rst

   index-report.rst

   stackless.rst
   sandbox.rst

   discussions.rst

   cleanup.rst

   sprint-reports.rst

   eventhistory.rst
   statistic/index.rst

Indices and tables
==================

* :ref:`genindex`
* :ref:`search`
* :ref:`glossary`

