Choose the Garbage Collector used by the translated program:

  - "ref": reference counting. Takes very long to translate and the result is
    slow.

  - "marksweep": naive mark & sweep.

  - "semispace": a copying semi-space GC.

  - "generation": a generational GC using the semi-space GC for the
    older generation.

  - "boehm": use the Boehm conservative GC.
