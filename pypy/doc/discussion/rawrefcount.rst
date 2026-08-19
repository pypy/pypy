======================
Rawrefcount and the GC
======================


GC Interface
------------

"PyObject" is a raw structure with at least two words, ob_refcnt and
ob_pypy_link.  The ob_refcnt is the reference counter as used on
CPython.  If the PyObject structure is linked to a live PyPy object,
its current address is stored in ob_pypy_link and ob_refcnt is bumped
by either the constant REFCNT_FROM_PYPY, or the constant
REFCNT_FROM_PYPY_LIGHT (== REFCNT_FROM_PYPY + SOME_HUGE_VALUE)
(to mean "light finalizer").

Object layout: the ob_pypy_link prefix (abi3)
---------------------------------------------

ob_pypy_link is *not* part of the object's visible header.  The visible
PyObject header is exactly CPython's -- {ob_refcnt, ob_type} -- so that a
CPython abi3 (limited-API) wheel, which inlines Py_TYPE/Py_SIZE and reads
those fields at fixed offsets, sees the layout it expects.  ob_pypy_link
instead lives in a hidden prefix word immediately *before* ob_refcnt, at
offset -sizeof(Py_ssize_t).  This is the same trick CPython uses for
PyGC_Head: extensions never see the prefix; tp_basicsize starts at
ob_refcnt.

Every heap PyObject allocation reserves the prefix and hands out a pointer
past it; the free path (PyObject_GC_Del / the default tp_free) releases it.
The prefix is reached only by PyPy-internal code, never by extensions.  The
same offset logic is (currently) duplicated in a few places -- to be unified
later:

- pypy/module/cpyext/pyobject.py     -- pyobj_raw_alloc/free, pyobj_get/set_link
- pypy/module/cpyext/src/object.c    -- _PyPy_LINK / _PyPy_LINK_PREFIX
- rpython/memory/gc/incminimark.py   -- PYOBJ_HDR / _pyobj (translated GC)
- rpython/rlib/rawrefcount.py        -- _ob_link_get/set/_ob_free (untranslated)

Immortal static objects are exempt (no prefix)
----------------------------------------------

The prebuilt, immortal, *exported* static objects -- the whole
pypy_static_pyobjs[] set: the singletons (None/True/False/NotImplemented/
Ellipsis), the built-in type objects (PyList_Type, ...), and the exception
classes (PyExc_*) -- are emitted as *bare* PyObject/PyTypeObject storage with
NO prefix.  Two reasons: (1) abi3 wheels reference these as plain exported
data symbols (e.g. Py_None == &_Py_NoneStruct) and expect CPython's bare
layout with no prefix; and (2) they are immutable identity anchors that never
feed data back to their PyPy object and never die, so they do not need the
mutable rawrefcount link at all.  They are mapped w_obj <-> pyobj through a
constant identity table built once at startup (keyed on pypy_static_pyobjs[]),
consulted by from_ref; the GC/rawrefcount never touch them, so their missing
prefix is never read.  Only dynamically allocated instances (a live list, a
live exception whose message can change, ...) carry the prefix and the link.

Design refinement (WIP): the refcnt tag as the "has prefix" discriminator
-------------------------------------------------------------------------

WORK IN PROGRESS.  This section describes the scheme we are moving to so that
foreign (C-allocated) PyObjects work correctly under the prefix layout.  It
supersedes parts of the older text below; the two will be reconciled once the
implementation lands.

The problem.  A C extension may allocate a bare PyObject itself -- e.g.
``calloc(1, sizeof(PyObject))`` followed by ``_Py_NewReference`` -- which is
legal CPython usage (CPython has no back-link, so nothing is written outside the
object).  Such a *foreign* object has NO prefix.  If PyPy writes ob_pypy_link at
offset -sizeof(Py_ssize_t) on it (in _Py_NewReference, _Py_Dealloc, or when
realizing/linking it), it corrupts the heap word before the allocation.

So at every point that would touch the prefix, PyPy must know whether a given
PyObject has one.  This cannot be told from the pointer, and at the first
crossing an owned-but-unlinked object (tp_alloc'd, has prefix, its w_obj created
lazily on the first from_ref) and a foreign object (calloc'd, no prefix) both
sit at a small refcnt.  The discriminator is the reference-count range::

    REFCNT_FROM_PYPY <= ob_refcnt   <=>   "this PyObject has a prefix"

To make that hold from birth (not only once linked), REFCNT_FROM_PYPY becomes a
permanent "has prefix" tag applied by the prefix-reserving allocators:

- every prefix allocation (_generic_alloc, the RPython allocate path) sets
  ob_refcnt = REFCNT_FROM_PYPY + <initial C refs> at allocation time;
- create_link / track_reference then only writes the prefix link; it no longer
  bumps ob_refcnt (the tag is already there);
- the w_obj presence lives entirely in the prefix value: ob_pypy_link == 0 means
  "no w_obj" (either pre-link setup or post-clear teardown), non-zero means
  linked;
- the tag is never subtracted while the object lives -- it just vanishes with
  the freed block at deallocation.

Foreign objects never get the tag, so ob_refcnt < REFCNT_FROM_PYPY for them, and
PyPy never reads or writes their (non-existent) prefix.  No side table / foreign
map is needed for the discrimination.

Two-condition deallocation.  Because the tag is permanent, "no references left"
is no longer "ob_refcnt == 0".  An object is dead, and its deallocator must run,
when::

    ob_refcnt == 0                                            # foreign (untagged)
    OR (ob_refcnt == REFCNT_FROM_PYPY and ob_pypy_link == 0)  # owned, no C refs, no w_obj

The prefix (ob_pypy_link) is only read when ob_refcnt == REFCNT_FROM_PYPY, which
a foreign object (starting small, needing ~2**60 increfs to reach it) never
hits -- so the check never touches a missing prefix.  The condition is reached
from two directions, both triggering the same deallocation:

- Py_DECREF drops the last C reference: an owned object falls to
  REFCNT_FROM_PYPY (with ob_pypy_link already 0 if it was never linked, e.g. a
  tp_alloc'd object discarded on a C error path); a foreign object falls to 0.
- the w_obj dies: rawrefcount clears the prefix (ob_pypy_link = 0) and, if
  ob_refcnt == REFCNT_FROM_PYPY (no C refs), deallocates.

Once deallocation has started ob_refcnt is irrelevant: _Py_Dealloc marks the
object deallocating (writing the prefix -- safe, it is owned) and calls
tp_dealloc, then the block is freed.  _Py_Dealloc, from_ref and the
realize/link path all use the same ``ob_refcnt >= REFCNT_FROM_PYPY`` test to
decide whether the object has a prefix.

All Py_DECREF goes through our function.  The two-condition logic (and the
REFCNT_FROM_PYPY constant) must NOT leak into the public headers.  CPython 3.12
makes this possible: under Py_LIMITED_API >= 0x030c0000, Include/object.h
implements Py_INCREF/Py_DECREF as *function calls* to _Py_IncRef/_Py_DecRef
(Include/object.h ~lines 624-676) rather than an inline ``--ob_refcnt == 0``
macro, so a prebuilt 3.12 abi3 wheel routes every refcount op through a function
PyPy provides.  We extend this to *all* builds: PyPy's Py_INCREF/Py_DECREF always
call _Py_IncRef/_Py_DecRef, even in the non-limited (full API) case, instead of
inlining ob_refcnt.  This keeps REFCNT_FROM_PYPY and the prefix entirely inside
cpyext and out of every extension's compiled code, at the cost of a function
call per refcount op; _Py_IncRef/_Py_DecRef implement the two-condition
deallocation above.

LIGHT finalizers (REFCNT_FROM_PYPY_LIGHT) are, in current pypy3, never created
(only rawrefcount's own unit tests add them), so this refinement ignores them; a
single tag region suffices.

Immortality is orthogonal to the tag
------------------------------------

CPython 3.12 marks an object immortal in the *low bits* of ob_refcnt: the
immortal value is ``_Py_IMMORTAL_REFCNT`` (``UINT_MAX`` on 64-bit,
``UINT_MAX >> 2`` on 32-bit), and on 64-bit the check ``_Py_IsImmortal`` is
"bit 31 set" (``(int32_t)ob_refcnt < 0``), deliberately tolerant of stale
extensions drifting the exact value.  For abi3 compatibility PyPy keeps these
*values* bit-for-bit identical to CPython, and places the REFCNT_FROM_PYPY
"has prefix" tag in bits *above* the immortal field, so the two properties
compose without interfering:

===============================  ====================================  =======  =====================
state                            ob_refcnt                             prefix?  w_obj lookup
===============================  ====================================  =======  =====================
owned, mortal                    ``FROM_PYPY + n``                     yes      prefix link
owned, immortal                  ``FROM_PYPY + _Py_IMMORTAL_REFCNT``   yes      prefix link
prefix-less immortal (static)   ``_Py_IMMORTAL_REFCNT``               no       State.static_py2w
foreign, mortal                  small ``n``                           no       realize a shadow
===============================  ====================================  =======  =====================

Consequences:

- Py_INCREF/Py_DECREF (header fast path via ``_Py_IsImmortal``), _Py_IncRef/
  _Py_DecRef, and the interp-level incref/decref all no-op on immortals, so an
  immortal refcnt never drifts and the bit patterns above are stable.
- An immortalized *owned* object (e.g. a heaptype promoted at runtime) keeps
  its prefix and link: it still passes ``>= REFCNT_FROM_PYPY``, so from_ref
  finds it through the prefix unchanged, and the two-condition dead test
  (``== REFCNT_FROM_PYPY``) can never fire on it.  Immortalizing an owned
  object must *add* the immortal value to the tag, never overwrite it.
- The out-of-band table (State.static_py2w/static_w2py) is only needed for
  immortals that physically cannot have a prefix: our bare
  pypy_static_pyobjs[] structs and extension-declared static (non-heaptype)
  type objects, whose storage sits in a C ``.data`` section.
- from_ref checks the immortal bit and the table first; a table miss (an
  immortal object we did not register, e.g. immortalized by an extension)
  falls through to foreign-style shadow realization.

On 32-bit the immortal field is 30 bits, which leaves only bit 30 above it:
REFCNT_FROM_PYPY moves to ``0x40000000`` and REFCNT_FROM_PYPY_LIGHT is
squeezed to ``0x70000000`` (harmless: the LIGHT region is never created, see
above).  An owned immortal is then ``0x7FFFFFFF``; since the tagged value no
longer *equals* ``_Py_IMMORTAL_REFCNT``, the 32-bit check is mask-equality
``(rc & _Py_IMMORTAL_REFCNT) == _Py_IMMORTAL_REFCNT`` instead of CPython's
plain equality -- identical behaviour for untagged (foreign) refcounts.
The canonical constants and ``refcnt_is_immortal()`` live in
rpython/rlib/rawrefcount.py; pypy/module/cpyext/src/object.c and
pypy/module/cpyext/include/object.h carry the C copies and MUST match.

Most PyPy objects exist outside cpyext, and conversely in cpyext it is
possible that a lot of PyObjects exist without being seen by the rest
of PyPy.  At the interface, however, we can "link" a PyPy object and a
PyObject.  There are two kinds of link:

rawrefcount.create_link_pypy(p, ob)

    Makes a link between an existing object gcref 'p' and a newly
    allocated PyObject structure 'ob'.  ob->ob_refcnt must be
    initialized to either REFCNT_FROM_PYPY, or
    REFCNT_FROM_PYPY_LIGHT.  (The second case is an optimization:
    when the GC finds the PyPy object and PyObject no longer
    referenced, it can just free() the PyObject.)

rawrefcount.create_link_pyobj(p, ob)

    Makes a link from an existing PyObject structure 'ob' to a newly
    allocated W_CPyExtPlaceHolderObject 'p'.  You must also add
    REFCNT_FROM_PYPY to ob->ob_refcnt.  For cases where the PyObject
    contains all the data, and the PyPy object is just a proxy.  The
    W_CPyExtPlaceHolderObject should have only a field that contains
    the address of the PyObject, but that's outside the scope of the
    GC.

rawrefcount.from_obj(p)

    If there is a link from object 'p' made with create_link_pypy(),
    returns the corresponding 'ob'.  Otherwise, returns NULL.

rawrefcount.to_obj(Class, ob)

    Returns ob->ob_pypy_link, cast to an instance of 'Class'.


Collection logic
----------------

Objects existing purely on the C side have ob->ob_pypy_link == 0;
these are purely reference counted.  On the other hand, if
ob->ob_pypy_link != 0, then ob->ob_refcnt is at least REFCNT_FROM_PYPY
and the object is part of a "link".

The idea is that links whose 'p' is not reachable from other PyPy
objects *and* whose 'ob->ob_refcnt' is REFCNT_FROM_PYPY or
REFCNT_FROM_PYPY_LIGHT are the ones who die.  But it is more messy
because PyObjects still (usually) need to have a tp_dealloc called,
and this cannot occur immediately (and can do random things like
accessing other references this object points to, or resurrecting the
object).

Let P = list of links created with rawrefcount.create_link_pypy()
and O = list of links created with rawrefcount.create_link_pyobj().
The PyPy objects in the list O are all W_CPyExtPlaceHolderObject: all
the data is in the PyObjects, and all outsite references (if any) are
in C, as ``PyObject *`` fields.

So, during the collection we do this about P links:

.. code-block:: python

    for (p, ob) in P:
        if ob->ob_refcnt != REFCNT_FROM_PYPY
               and ob->ob_refcnt != REFCNT_FROM_PYPY_LIGHT:
            mark 'p' as surviving, as well as all its dependencies

At the end of the collection, the P and O links are both handled like
this:

.. code-block:: python

    for (p, ob) in P + O:
        if p is not surviving:    # even if 'ob' might be surviving
            unlink p and ob
            if ob->ob_refcnt == REFCNT_FROM_PYPY_LIGHT:
                free(ob)
            elif ob->ob_refcnt > REFCNT_FROM_PYPY_LIGHT:
                ob->ob_refcnt -= REFCNT_FROM_PYPY_LIGHT
            else:
                ob->ob_refcnt -= REFCNT_FROM_PYPY
                if ob->ob_refcnt == 0:
                    invoke _Py_Dealloc(ob) later, outside the GC


GC Implementation
-----------------

We need two copies of both the P list and O list, for young or old
objects.  All four lists can be regular AddressLists of 'ob' objects.

We also need an AddressDict mapping 'p' to 'ob' for all links in the P
list, and update it when PyPy objects move.


Further notes
-------------

XXX
XXX the rest is the ideal world, but as a first step, we'll look
XXX for the minimal tweaks needed to adapt the existing cpyext
XXX

For objects that are opaque in CPython, like <dict>, we always create
a PyPy object, and then when needed we make an empty PyObject and
attach it with create_link_pypy()/REFCNT_FROM_PYPY_LIGHT.

For <int> and <float> objects, the corresponding PyObjects contain a
"long" or "double" field too.  We link them with create_link_pypy()
and we can use REFCNT_FROM_PYPY_LIGHT too: 'tp_dealloc' doesn't
need to be called, and instead just calling free() is fine.

For <type> objects, we need both a PyPy and a PyObject side.  These
are made with create_link_pypy()/REFCNT_FROM_PYPY.

For custom PyXxxObjects allocated from the C extension module, we
need create_link_pyobj().

For <str> or <unicode> objects coming from PyPy, we use
create_link_pypy()/REFCNT_FROM_PYPY_LIGHT with a PyObject
preallocated with the size of the string.  We copy the string
lazily into that area if PyString_AS_STRING() is called.

For <str>, <unicode>, <tuple> or <list> objects in the C extension
module, we first allocate it as only a PyObject, which supports
mutation of the data from C, like CPython.  When it is exported to
PyPy we could make a W_CPyExtPlaceHolderObject with
create_link_pyobj().

For <tuple> objects coming from PyPy, if they are not specialized,
then the PyPy side holds a regular reference to the items.  Then we
can allocate a PyTupleObject and store in it borrowed PyObject
pointers to the items.  Such a case is created with
create_link_pypy()/REFCNT_FROM_PYPY_LIGHT.  If it is specialized,
then it doesn't work because the items are created just-in-time on the
PyPy side.  In this case, the PyTupleObject needs to hold real
references to the PyObject items, and we use create_link_pypy()/
REFCNT_FROM_PYPY.  In all cases, we have a C array of PyObjects
that we can directly return from PySequence_Fast_ITEMS, PyTuple_ITEMS,
PyTuple_GetItem, and so on.

For <list> objects coming from PyPy, we can use a cpyext list
strategy.  The list turns into a PyListObject, as if it had been
allocated from C in the first place.  The special strategy can hold
(only) a direct reference to the PyListObject, and we can use either
create_link_pyobj() or create_link_pypy() (to be decided).
PySequence_Fast_ITEMS then works for lists too, and PyList_GetItem
can return a borrowed reference, and so on.
