=======================
What's new in PyPy 2.2+
=======================

.. this is a revision shortly after release-2.2.x
.. startrev: 4cd1bc8b3111

.. branch: release-2.2.x

.. branch: numpy-newbyteorder
Clean up numpy types, add newbyteorder functionality

.. branch: windows-packaging
Package tk/tcl runtime with win32

.. branch: armhf-singlefloat
JIT support for singlefloats on ARM using the hardfloat ABI

.. branch: voidtype_strformat
Better support for record numpy arrays

.. branch: osx-eci-frameworks-makefile
OSX: Ensure frameworks end up in Makefile when specified in External compilation info

.. branch: less-stringly-ops
Use subclasses of SpaceOperation instead of SpaceOperator objects.
Random cleanups in flowspace and annotator.

.. branch: ndarray-buffer
adds support for the buffer= argument to the ndarray ctor

.. branch: better_ftime_detect2
On OpenBSD do not pull in libcompat.a as it is about to be removed.
And more generally, if you have gettimeofday(2) you will not need ftime(3).

.. branch: timeb_h
Remove dependency upon <sys/timeb.h> on OpenBSD. This will be disappearing
along with libcompat.a.

.. branch: OlivierBlanvillain/fix-3-broken-links-on-pypy-published-pap-1386250839215
Fix 3 broken links on PyPy published papers in docs.

.. branch: jit-ordereddict

.. branch: refactor-str-types
Remove multimethods on str/unicode/bytearray and make the implementations share code.
