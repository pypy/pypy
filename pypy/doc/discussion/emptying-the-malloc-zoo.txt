.. coding: utf-8

Emptying the malloc zoo
=======================

Around the end-of-the-EU-project time there were two major areas of
obscurity in the memory management area:

 1. The confusing set of operations that the low-level backend are
    expected to implement.

 2. The related, but slightly different, confusion of the various
    "flavours" of malloc: what's the difference between
    lltype.malloc(T, flavour='raw') and llmemory.raw_malloc(sizeof(T))?

At the post-ep2007 sprint, Samuele and Michael attacked the first
problem a bit: making the Boehm GC transformer only require three
simple operations of the backend.  This could be extending still
further by having the gc transformer use rffi to insert calls to the
relevant Boehm functions^Wmacros, and then the backend wouldn't need
to know anything about Boehm at all (but... LLVM).

A potential next step is to work out what we want the "llpython"
interface to memory management to be.

There are various use cases:

**lltype.malloc(T) – T is a fixed-size GC container**

  This is the default case.  Non-pointers inside the allocated memory
  will not be zeroed.  The object will be managed by the GC, no
  deallocation required.

**lltype.malloc(T, zero=True) – T is a GC container**

  As above, but all fields will be cleared.

**lltype.malloc(U, raw=True) – U is not a GC container**

  Blah.
