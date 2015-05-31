Making a PyPy Release
=====================

Overview
--------

As a meta rule setting up issues in the tracker for items here may help not
forgetting things. A set of todo files may also work.

Check and prioritize all issues for the release, postpone some if necessary,
create new  issues also as necessary. An important thing is to get
the documentation into an up-to-date state!


Release Steps
-------------

* At code freeze make a release branch using release-x.x.x in mercurial
  and add a release-specific tag
* Bump the
  pypy version number in module/sys/version.py and in
  module/cpyext/include/patchlevel.h and . The branch
  will capture the revision number of this change for the release.

  Some of the next updates may be done before or after branching; make
  sure things are ported back to the trunk and to the branch as
  necessary.
* update pypy/doc/contributor.rst (and possibly LICENSE)
  pypy/doc/tool/makecontributor.py generates the list of contributors
* rename pypy/doc/whatsnew_head.rst to whatsnew_VERSION.rst
  create a fresh whatsnew_head.rst after the release
  and add the new file to  pypy/doc/index-of-whatsnew.rst
* go to pypy/tool/release and run
  ``force-builds.py <release branch>``
  The following binaries should be built, however, we need more buildbots
 - JIT: windows, linux, os/x, armhf, armel
 - no JIT: windows, linux, os/x
 - sandbox: linux, os/x

* wait for builds to complete, make sure there are no failures
* download the builds, repackage binaries. Tag the release version
  and download and repackage source from bitbucket. You may find it
  convenient to use the ``repackage.sh`` script in pypy/tools to do this. 

  Otherwise repackage and upload source "-src.tar.bz2" to bitbucket
  and to cobra, as some packagers prefer a clearly labeled source package
  ( download e.g.  https://bitbucket.org/pypy/pypy/get/release-2.5.x.tar.bz2,
  unpack, rename the top-level directory to "pypy-2.5.0-src", repack, and upload)

* Upload binaries to https://bitbucket.org/pypy/pypy/downloads

* write release announcement pypy/doc/release-x.y(.z).txt

  The release announcement should contain a direct link to the download page

* Add the new files to  pypy/doc/index-of-{whatsnew,release-notes}.rst

* update pypy.org (under extradoc/pypy.org), rebuild and commit

* post announcement on morepypy.blogspot.com
* send announcements to twitter.com, pypy-dev, python-list,
  python-announce, python-dev ...

* add a tag on the pypy/jitviewer repo that corresponds to pypy release
* add a tag on the codespeed web site that corresponds to pypy release
* update the version number in {rpython,pypy}/doc/conf.py.
* revise versioning at https://readthedocs.org/projects/pypy
