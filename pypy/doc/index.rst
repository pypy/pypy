
Welcome to PyPy Development
=============================================

The PyPy project aims at producing a flexible and fast Python_
implementation.  The guiding idea is to translate a Python-level
description of the Python language itself to lower level languages.
Rumors have it that the secret goal is being faster-than-C which is
nonsense, isn't it?  `more...`_

.. toctree::
   :maxdepth: 2

   .. STUFF THAT'S BEEN THROUGH 1ST PASS CATEGORIZATION:

   .. The following stuff is high-value and (vaguely) true:
   getting-started.rst
   getting-started-python.rst
   getting-started-dev.rst
   faq.rst
   architecture.rst
   coding-guide.rst
   cleanup-todo.rst
   cpython_differences.rst
   garbage_collection.rst
   interpreter.rst
   objspace.rst

   dev_method.rst
   download.rst
   extending.rst
   windows.rst

   extradoc.rst
     .. ^^ integrate this one level up: dcolish?

   glossary.rst

   contributor.rst

   .. True, high-detail:
   interpreter-optimizations.rst
   configuration.rst
   low-level-encapsulation.rst
   parser.rst
   rlib.rst
   rtyper.rst
   translation.rst
   jit/_ref.rst
   jit/index.rst
   jit/overview.rst
   jit/pyjitpl5.rst

   ctypes-implementation.rst
     .. ^^ needs attention

   how-to-release.rst
     .. ^^ needs attention

   index-report.rst
     .. ^^ of historic interest, and about EU fundraising

   maemo.rst
     .. ^^ obscure corner; not sure of status

   stackless.rst
     .. ^^ it still works; needs JIT integration; hasn't been maintained for years

   .. The following stuff is good material relating to unmaintained areas of the project:
      .. .Net stuff:
   cli-backend.rst
   clr-module.rst
   carbonpython.rst

   .. Release notes:
   release-0.6.rst
   release-0.7.0.rst
   release-0.8.0.rst
   release-0.9.0.rst
   release-0.99.0.rst
   release-1.0.0.rst
   release-1.1.0.rst
   release-1.2.0.rst
   release-1.3.0.rst
   release-1.4.0.rst
   release-1.4.0beta.rst
   release-1.4.1.rst


   .. The following stuff is old (and crufty?), and needs further investigation:
   buildtool.rst
   distribution.rst
   eventhistory.rst
     .. ^^ Incomplete,  superceded elsewhere

   externaltools.rst
     .. ^^ Incomplete and wrong,  superceded elsewhere

   geninterp.rst
     .. ^^ apparently dead

   objspace-proxies.rst

   old_news.rst

   sprint-reports.rst

   project-ideas.rst

   rffi.rst

   sandbox.rst
     .. ^^ it continues to work, but is unmaintained

   statistic/index.rst

   theory.rst
     .. ^^ old ideas; we're not doing it this way any more

   translation-aspects.rst
     .. ^^ old and needs updating

   .. This needs merging somehow:
   docindex.rst

   .. Needs merging/replacing with hg stuff:
   svn-help.rst

   .. The following discussions have not yet been categorized:

   discussion/GC-performance.rst
   discussion/VM-integration.rst
   discussion/chained_getattr.rst
   discussion/cli-optimizations.rst
   discussion/cmd-prompt-translation.rst
   discussion/compiled-swamp.rst
   discussion/ctypes_modules.rst
   discussion/ctypes_todo.rst
   discussion/distribution.rst
   discussion/distribution-implementation.rst
   discussion/distribution-newattempt.rst
   discussion/distribution-roadmap.rst
   discussion/emptying-the-malloc-zoo.rst
   discussion/finalizer-order.rst
   discussion/gc.rst
   discussion/howtoimplementpickling.rst
   discussion/improve-rpython.rst
   discussion/outline-external-ootype.rst
   discussion/oz-thread-api.rst
   discussion/paper-wishlist.rst
   discussion/parsing-ideas.rst
   discussion/pypy_metaclasses_in_cl.rst
   discussion/removing-stable-compiler.rst
   discussion/security-ideas.rst
   discussion/somepbc-refactoring-plan.rst
   discussion/summer-of-pypy-pytest.rst
   discussion/testing-zope.rst
   discussion/thoughts_string_interning.rst
   discussion/translation-swamp.rst
   discussion/use_case_of_logic.rst

   .. STUFF THAT'S DIFFICULT TO CATEGORIZE
   video-index.rst


Getting into PyPy ... 
=============================================

* `Release 1.4`_: the latest official release

* `PyPy Blog`_: news and status info about PyPy 

* `Documentation`_: extensive documentation and papers_ about PyPy.  

* `Getting Started`_: Getting started and playing with PyPy. 

Mailing lists, bug tracker, IRC channel
=============================================

* `Development mailing list`_: development and conceptual
  discussions. 

* `Subversion commit mailing list`_: updates to code and
  documentation. 

* `Development bug/feature tracker`_: filing bugs and feature requests. 

* `Sprint mailing list`_: mailing list for organizing upcoming sprints. 

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
.. _`subversion commit mailing list`: http://codespeak.net/mailman/listinfo/pypy-svn
.. _`development mailing list`: http://codespeak.net/mailman/listinfo/pypy-dev
.. _`FAQ`: faq.html
.. _`Documentation`: docindex.html 
.. _`Getting Started`: getting-started.html
.. _papers: extradoc.html
.. _`Release 1.4`: http://pypy.org/download.html

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
* :ref:`glossary`

