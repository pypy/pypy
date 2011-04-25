.. include:: needswork.rst

.. needs work, it talks about svn. also, it is not really user documentation

Making a PyPy Release
=======================

Overview
---------

As a meta rule setting up issues in the tracker for items here may help not
forgetting things. A set of todo files may also work.

Check and prioritize all issues for the release, postpone some if necessary,
create new  issues also as necessary. A meeting (or meetings) should be
organized to decide what things are priorities, should go in and work for
the release. 

An important thing is to get the documentation into an up-to-date state!

Release Steps
----------------

* at code freeze make a release branch under
  http://codepeak.net/svn/pypy/release/x.y(.z). IMPORTANT: bump the
  pypy version number in module/sys/version.py and in
  module/cpyext/include/patchlevel.h, notice that the branch
  will capture the revision number of this change for the release;
  some of the next updates may be done before or after branching; make
  sure things are ported back to the trunk and to the branch as
  necessary
* update pypy/doc/contributor.txt (and possibly LICENSE)
* update README
* go to pypy/tool/release and run:
  force-builds.py /release/<release branch>
* wait for builds to complete, make sure there are no failures
* run pypy/tool/release/make_release.py, this will build necessary binaries
  and upload them to pypy.org

  Following binaries should be built, however, we need more buildbots:
    JIT: windows, linux, os/x
    no JIT: windows, linux, os/x
    sandbox: linux, os/x
    stackless: windows, linux, os/x

* write release announcement pypy/doc/release-x.y(.z).txt
  the release announcement should contain a direct link to the download page
* update pypy.org (under extradoc/pypy.org), rebuild and commit

* update http://codespeak.net/pypy/trunk:
   code0> + chmod -R yourname:users /www/codespeak.net/htdocs/pypy/trunk
   local> cd ..../pypy/doc && py.test
   local> cd ..../pypy
   local> rsync -az doc codespeak.net:/www/codespeak.net/htdocs/pypy/trunk/pypy/

* post announcement on morepypy.blogspot.com
* send announcements to pypy-dev, python-list,
  python-announce, python-dev ...
