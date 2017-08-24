PyPy's Release Process
========================

Release Policy
++++++++++++++

We try to create a stable release a few times a year. These are released on
a branch named like release-pypy3.5-v2.x or release-pypy3.5-v4.x, and each
release is tagged, for instance release-pypy3.5-v4.0.1. 

After release, inevitably there are bug fixes. It is the responsibility of
the commiter who fixes a bug to make sure this fix is on the release branch,
so that we can then create a tagged bug-fix release, which will hopefully
happen more often than stable releases.

How to Create a PyPy Release
++++++++++++++++++++++++++++

Overview
--------

As a meta rule setting up issues in the tracker for items here may help not
forgetting things. A set of todo files may also work.

Check and prioritize all issues for the release, postpone some if necessary,
create new  issues also as necessary. An important thing is to get
the documentation into an up-to-date state!


Release Steps
-------------

* If needed, make a release branch
* Bump the
  pypy version number in module/sys/version.py and in
  module/cpyext/include/patchlevel.h and in doc/conf.py. The branch
  will capture the revision number of this change for the release.

  Some of the next updates may be done before or after branching; make
  sure things are ported back to the trunk and to the branch as
  necessary.

* Maybe bump the SOABI number in module/imp/importing. This has many
  implications, so make sure the PyPy community agrees to the change.

* Update and write documentation

  * update pypy/doc/contributor.rst (and possibly LICENSE)
    pypy/doc/tool/makecontributor.py generates the list of contributors

  * rename pypy/doc/whatsnew_head.rst to whatsnew_VERSION.rst
    create a fresh whatsnew_head.rst after the release
    and add the new file to  pypy/doc/index-of-whatsnew.rst

  * write release announcement pypy/doc/release-VERSION.rst
    The release announcement should contain a direct link to the download page

  * Add the new files to  pypy/doc/index-of-{whatsnew,release-notes}.rst

* Build and upload the release tar-balls

  * go to pypy/tool/release and run
    ``force-builds.py <release branch>``
    The following JIT binaries should be built, however, we need more buildbots
    windows, linux-32, linux-64, osx64, armhf-raring, armhf-raspberrian, armel,
    freebsd64 

  * wait for builds to complete, make sure there are no failures

  * send out a mailing list message asking for people to test before uploading
    to prevent having to upload more than once

  * add a tag on the pypy/jitviewer repo that corresponds to pypy release, so
    that the source tarball can be produced in the next steps

  * download the builds, repackage binaries. Tag the release version
    and download and repackage source from bitbucket. You may find it
    convenient to use the ``repackage.sh`` script in pypy/tool/release to do this. 

    Otherwise repackage and upload source "-src.tar.bz2" to bitbucket
    and to cobra, as some packagers prefer a clearly labeled source package
    ( download e.g.  https://bitbucket.org/pypy/pypy/get/release-2.5.x.tar.bz2,
    unpack, rename the top-level directory to "pypy-2.5.0-src", repack, and upload)

  * Upload binaries to https://bitbucket.org/pypy/pypy/downloads

* Send out a mailing list message asking for last-minute comments and testing

* RELEASE !  

  * update pypy.org (under extradoc/pypy.org), rebuild and commit, using the
    hashes produced from the ``repackage.sh`` script or by hand

  * post announcement on morepypy.blogspot.com
  * send announcements to twitter.com, pypy-dev, python-list,
    python-announce, python-dev ...

* If all is OK, document the released version

  * add a tag on the codespeed web site that corresponds to pypy release
  * revise versioning at https://readthedocs.org/projects/pypy
