Mercurial and Heptapod short tutorial
=====================================

.. comment
  Taken from https://foss.heptapod.net/fluiddyn/fluiddyn/blob/branch/default/doc/mercurial_heptapod.rst
  and modified


`Mercurial <http://mercurial.selenic.com/>`_ is a free, distributed source
control management tool. We use it for PyPy, not only because it is written in
Python, but because its branch model fits our development process better than
Git's branch model.

Mercurial couples very well with the programs `TortoiseHG
<https://tortoisehg.bitbucket.io/>`__ and `Meld <https://meldmerge.org/>`__ (if
you can, just install them, especially Meld).

There are a lot of tutorials and documentations about Mercurial (for example
`the official Mercurial tutorial
<http://mercurial.selenic.com/wiki/Tutorial>`_). This page is meant to show you
what you need to get going with PyPy development.

`Heptapod <https://heptapod.net/>`_ is a friendly fork of GitLab Community
Edition supporting Mercurial.

Installation
------------

With TortoiseHG (simple for Windows)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Download the installer from https://tortoisehg.bitbucket.io/.
(but note you might need the evolve extension)

With conda (cross-platform, recommended for Linux and macOS)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

On Windows, macOS and Linux, one can use ``conda`` (installed with `miniconda
<https://docs.conda.io/en/latest/miniconda.html>`__) to install Mercurial with
few extensions (`hg-evolve <https://pypi.org/project/hg-evolve>`_ and `hg-git
<http://hg-git.github.io/>`_). On Windows, these commands have to be run in the
Anaconda Prompt. First, we need to install `conda-app
<https://pypi.org/project/conda-app>`_ in the base conda environment::

  conda activate base
  python -mpip install conda-app

Then, with the conda-forge channel added (``conda config --add channels
conda-forge``), one just needs to run::

  conda-app install mercurial

**Open a new terminal** and the Mercurial command ``hg`` should be available.

.. note ::

  If you don't use TortoiseHG, you should really install the visual diff and
  merge tool `Meld <https://meldmerge.org/>`__!

Set-up Mercurial
----------------

You need to create a file ``~/.hgrc``. For a good starting point, you can use
the command::

  hg config --edit

An example of configuration file::

  [ui]
  username=myusername <email@adress.org>
  editor=emacs -nw
  tweakdefaults = True

  [extensions]
  hgext.extdiff =
  # only to use Mercurial with GitHub and Gitlab
  hggit =
  # more advanced extensions (really useful for PyPy dev)
  churn =
  shelve =
  rebase =
  absorb =
  evolve =
  topic =

  [extdiff]
  cmd.meld =

The line starting with hggit is optional and enables the extension `hg-git
<http://hg-git.github.io/>`_. This extension is useful to work on projects
using Git, for example hosted on Github and Gitlab.

The extensions churn, shelve, rebase, absorb, evolve and topic are very useful
for more advanced users. Note that `evolve
<https://www.mercurial-scm.org/doc/evolution/>`_ and `topic`_
comes from the package `hg-evolve <https://pypi.org/project/hg-evolve>`_.

.. note ::

  For occasional contribution to PyPy, the evolve and topic extensions have to
  be installed and activated since we use topic_ branches for short-term
  development

Get help
--------

To get help on Mercurial, one can start with::

  hg help

or for a specific command (here ``clone``)::

  hg help clone

Simple workflow
---------------

To make a copy of an existing repository::

  hg clone https://foss.heptapod.net/pypy/pypy

To get a summary of the working directory state::

  hg summary

or just ``hg sum``.

Before you begin work, open a new topic branch::

  hg topic my_branch

To show changed files in the working directory::

  hg status

or just ``hg st``.

If you add new files or if you deleted files::

  hg add name_of_the_file

  hg remove name_of_the_file

Each time you do some consistent changes::

  hg commit -m "A message explaining the commit"

After a commit command ``hg st`` to check that you did
what you wanted to do. If you are unhappy with the commit, you can amend it
with another commit with::

  hg commit --amend

To push the state of your working repository to your repository on the web::

  hg push

The inverse command (pull all commits from the remote repository) is::

  hg pull

Get the last version of a code
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

First pull all the changesets from the remote repository::

  hg pull

Then update the code to the tip::

  hg update

or just ``hg up``. You can also directly do::

  hg pull -u

Read the history
^^^^^^^^^^^^^^^^

You can get a list of the changesets with::

  hg log --graph

or just ``hg log -G``. With the ``--graph`` or ``-G`` option, the revisions are
shown as an ASCII art.

Update the code to an old revision
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Use ``hg up 220`` to update to the revision 220. We can use a tag, bookmark,
topic name or branch name instead of a number. To get a clean copy, add the
option ``-C`` (beware).


Create a repository from a directory
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Create a new repository in the given directory by doing::

  hg init

Merge-Request based workflow with hg-evolve
-------------------------------------------

We now use a Merge-Request (MR) based workflow 

.. note ::

  GitLab's "merge requests" are equivalent to GitHub's "pull requests".

.. note ::

  In contrast to the standard workflow in Github, Gitlab and Bitbucket, you
  don't need to fork the repository to create Merge Requests.

Instead, you need to become a "developer" of the project. The developers have
the permission to push changesets (i.e. "commits") in a topic in the main
repository (for example https://foss.heptapod.net/pypy/pypy). To
acquire the "developer" role, please send a message in an issue_ or if needed,
create a dedicated issue.

.. _issue: https://foss.heptapod.net/pypy/pypy/issues

`Topics <topic>`_ are used in Mercurial for "lightweight branches" (like Git branches). 
The principle is that you first create a topic (with ``hg topic``). Once a
topic is activated, the changesets created belong to this topic. The new
changesets gathered in a topic can be pushed in the main repository. Even after
having been pushed to the main repository, they stay in the ``draft`` phase
(which means they can be modified, as opposed to ``public`` changesets. Run
``hg help phases`` for more info).

To list the topics::

  hg topic

To activate a topic already created::

  hg up the_name_of_the_topic

To deactivate the topic and come back to the tip of the default branch::

  hg up default

To get the list of the changesets in the active topic (very useful)::

  hg stack

Developers have to create Merge Requests (MR) to get things merged in the
targeted branch (at the time of writing: ``default`` for Python2.7 or RPython
changes, ``py3.6`` for Python 3.6, ``py3.7`` for Python 3.7). Let's present
an example. A developer can do (here, we use ssh but you can also use https)::

  hg clone ssh://hg@foss.heptapod.net/pypy/pypy
  hg up default
  hg topic fix_something
  hg commit -m "Fix a bug related to ..."
  hg push

Mercurial is going to print an URL to create the associated MR. Once created,
the MR should then be reviewed by a contributor with the "maintainer" or higher
role. Only maintainers have the permissions to merge a MR, i.e. to publish
changesets. The maintainer can tell you how to modify your MR and can also
directly modify the changesets of the MR.

We strongly advice to install and activate the `evolve
<https://www.mercurial-scm.org/doc/evolution/>`_, rebase and `absorb
<https://gregoryszorc.com/blog/2018/11/05/absorbing-commit-changes-in-mercurial-4.8/>`_
extensions locally (see the example of ``.hgrc`` above). This gives a very nice
user experience for the MRs, with the ability to modify a MR with ``hg absorb``
and safe history editing.

.. tip ::

  ``hg absorb`` is very useful during code review. Let say that a developer
  submitted a MR containing few commits. As explained in `this blog post
  <https://gregoryszorc.com/blog/2018/11/05/absorbing-commit-changes-in-mercurial-4.8/>`_,
  ``hg absorb`` is a mechanism to automatically and intelligently incorporate
  uncommitted changes into prior commits. Edit the files to take into account
  the remarks of the code review and just run::

    hg absorb
    hg push

  and the MR is updated!

.. tip ::

  If you are asked to "rebase" your MR, it should work with the following commands::

    hg pull
    hg up name_of_my_topic
    hg rebase
    hg push

Working with hggit and Github
-----------------------------

To clone a **git** repository using **hg**::

  hg clone git+ssh://git@github.com/numpy/numpy

or just::

  hg clone https://github.com/numpy/numpy

Git *branches* are represented as Mercurial *bookmarks* so such commands can be
useful::

  hg log --graph

  hg up master

  hg help bookmarks

  # list the bookmarks
  hg bookmarks

  # put the bookmark master where you are
  hg book master

  # deactivate the active bookmark (-i like --inactive)
  hg book -i

.. note ::

  ``bookmarks``, ``bookmark`` and ``book`` correspond to the same
  mercurial command.

.. warning ::

  If a bookmark is active, ``hg pull -u`` or ``hg up`` will move the bookmark
  to the tip of the active branch. You may not want that so it is important to
  always deactivate an unused bookmark with ``hg book -i`` or with ``hg up
  master``.

Do not forget to place the bookmark ``master`` as wanted.

Delete a bookmark in a remote repository (close a remote Git branch)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

With Mercurial, `we can
do <https://stackoverflow.com/questions/6825355/how-do-i-delete-a-remote-bookmark-in-mercurial>`_::

  hg bookmark --delete <bookmark name>
  hg push --bookmark <bookmark name>

Unfortunately, it does not work for a remote Git repository (with hg-git).  We
have to use a Git client, clone the repository with Git and do `something like
<https://stackoverflow.com/a/10999165/1779806>`_::

  # this deletes the branch locally
  git branch --delete <branch name>
  # this deletes the branch in the remote repository
  git push origin --delete <branch name>

.. _topic: https://www.mercurial-scm.org/doc/evolution/tutorials/topic-tutorial.html
