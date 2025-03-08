PyPy's Release Process
========================

Release Policy
++++++++++++++

We try to create a stable release a few times a year. These are released on
a branch named like release-pypy3.5-v2.x or release-pypy3.5-v4.x, and each
release is tagged, for instance release-pypy3.5-v4.0.1. 

The release version number should be bumped. A micro release increment means
there were no changes that justify rebuilding c-extension wheels, since
the wheels are marked with only major.minor version numbers. It is ofen not
clear what constitutes a "major" release verses a "minor" release, the release
manager can make that call.

After release, inevitably there are bug fixes. It is the responsibility of
the committer who fixes a bug to make sure this fix is on the release branch,
so that we can then create a tagged bug-fix release, which will hopefully
happen more often than stable releases.

How to Create a PyPy Release
++++++++++++++++++++++++++++

As a meta rule setting up issues in the tracker for items here may help not
forgetting things. A set of todo files may also work.

Check and prioritize all issues for the release, postpone some if necessary,
create new  issues also as necessary. An important thing is to get
the documentation into an up-to-date state!


Release Steps
++++++++++++++

Make the release branch
------------------------

This is needed only in case you are doing a new major version; if not, you can
probably reuse the existing release branch.

We want to be able to freely merge default into the branch and vice-versa;
thus we need to do a complicate dance to avoid to patch the version number
when we do a merge::

  $ git checkout release-pypy2.7-v7.x
  $ # edit the version to e.g. 7.0.0-final
  $ git commit -a
  $ git checkout main
  $ # edit the version to 7.1.0-alpha0
  $ git commit -a
  $ git checkout release-pypy2.7-v7.x
  $ git merge main
  $ # clear merge conflicts in a way that keeps 7.0.0-final
  $ git commit -a

Then, we need to do the same for the ``release-pypy3*`` branch(es)

To change the version, you need to edit some files:

  - ``module/sys/version.py``: the ``PYPY_VERSION`` should be something like
    ``(7, 3, 10, "final", 0)`` or ``(7, 3, 9, "candidate", 2)`` for rc2.

  - ``module/cpyext/include/patchlevel.h``:  the ``PYPY_VERSION`` should be
    something like "7.3.10" for the final release or "7.3.10-candidate3" for
    rc3.

  - ``doc/conf.py`` in both ``rpython`` and ``pypy``.

Add tags to the repo. Never change tags once committed: it breaks downstream
packaging workflows.

  - Make sure the version checks pass (they ensure ``version.py`` and
    ``patchlevel.h`` agree)
  - Make sure the tag matches the version in version.py/patchlevel.h. You
    can run the repackage.sh script without pushing the tags after the
    buildbots run.
  - Once the repackage script runs, be sure to push the tags ``git push
    --tags``

Other steps
-----------

* Make sure the RPython builds on the buildbot pass with no failures

* Maybe bump the SOABI number in module/imp/importing. This has many
  implications, so make sure the PyPy community agrees to the change.
  Wheels will use the major.minor release numbers in the name, so bump
  them if there is an incompatible change to cpyext.

* Make sure the binary-testing_ CI is clean, or that the failures are understood.

* Update and write documentation

  * update pypy/doc/contributor.rst (and possibly LICENSE)
    pypy/doc/tool/makecontributor.py generates the list of contributors

  * write release announcement pypy/doc/release-VERSION.rst
    The release announcement should contain a direct link to the download page

  * Add the new files to  pypy/doc/index-of-release-notes.rst

* Build and upload the release tar-balls

  * go to https://buildbot.pypy.org/builders and force builds for the proper
    branches The following JIT binaries should be built: windows-64, linux-32,
    linux-64, macos_x86_64, macos_arm64, aarch64

  * wait for builds to complete, make sure there are no failures

  * send out a mailing list message asking for people to test before uploading
    to prevent having to upload more than once

  * add a tag on the pypy/jitviewer repo that corresponds to pypy release, so
    that the source tarball can be produced in the next steps

  * download the builds, repackage binaries. Tag the release-candidate version
    (it is important to mark this as a candidate since usually at least two
    tries are needed to complete the process) and download and repackage source
    from the buildbot. You may find it convenient to use the ``repackage.sh``
    script in ``pypy/tool/release`` to do this. 

    Also repackage and upload source "-src.tar.bz2"

  * Upload binaries to https://buildbot.pypy.org/mirror. Add the files to
    the ``versions.json`` in ``pypy/tools/release``, upload it, and run the
    ``check_versions.py`` file in that directory. This file is used by various
    downstream tools like "github actions" to find valid pypy downloads. It
    takes an hour for https://downloads.python.org/pypy/ to sync. Note the
    "latest_pypy" attribute: it is per-python-version. So if the new release
    overrides a current latest_pypy (both are 2.7.18, for instance), you must
    find the older version and set its "lastest_pypy" to "false" or
    ``check_versions.py`` (and the various tools) will fail.

* Send out a mailing list message asking for last-minute comments and testing

* RELEASE !  

  * update pypy.org_ with the checksum hashes produced from the
    ``repackage.sh`` script or by hand and the download pages

  * update the release note and the index with the release date

  * post announcement on pypy.org
  * send announcements to twitter.com, pypy-dev, python-list,
    python-announce, python-dev ...

* If all is OK, document the released version and suggest popular tools update
  to support it. Github actions will pick up the versions.json.

  * add a tag on the codespeed web site that corresponds to pypy release
  * revise versioning at https://readthedocs.org/projects/pypy
  * suggest updates to multibuild_ and cibuildwheel_

.. _multibuild: https://github.com/matthew-brett/multibuild
.. _cibuildwheel: https://github.com/joerick/cibuildwheel
.. _binary-testing: https://github.com/pypy/binary-testing/actions
.. _pypy.org: https://github.com/pypy/pypy.org
