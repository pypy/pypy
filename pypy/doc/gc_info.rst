Garbage collector configuration
===============================

.. _minimark-environment-variables:

Minimark
--------

PyPy's default ``incminimark`` garbage collector is configurable through
several environment variables:

``PYPY_GC_NURSERY``
    The nursery size.
    Defaults to 1/2 of your cache or ``4M``.
    Small values (like 1 or 1KB) are useful for debugging.

``PYPY_GC_NURSERY_DEBUG``
    If set to non-zero, will fill nursery with garbage, to help
    debugging.

``PYPY_GC_INCREMENT_STEP``
    The size of memory marked during the marking step.  Default is size of
    nursery times 2. If you mark it too high your GC is not incremental at
    all.  The minimum is set to size that survives minor collection times
    1.5 so we reclaim anything all the time.

``PYPY_GC_MAJOR_COLLECT``
    Major collection memory factor.
    Default is ``1.82``, which means trigger a major collection when the
    memory consumed equals 1.82 times the memory really used at the end
    of the previous major collection.

``PYPY_GC_GROWTH``
    Major collection threshold's max growth rate.
    Default is ``1.4``.
    Useful to collect more often than normally on sudden memory growth,
    e.g. when there is a temporary peak in memory usage.

``PYPY_GC_MAX``
    The max heap size.
    If coming near this limit, it will first collect more often, then
    raise an RPython MemoryError, and if that is not enough, crash the
    program with a fatal error.
    Try values like ``1.6GB``.

``PYPY_GC_MAX_DELTA``
    The major collection threshold will never be set to more than
    ``PYPY_GC_MAX_DELTA`` the amount really used after a collection.
    Defaults to 1/8th of the total RAM size (which is constrained to be
    at most 2/3/4GB on 32-bit systems).
    Try values like ``200MB``.

``PYPY_GC_MIN``
    Don't collect while the memory size is below this limit.
    Useful to avoid spending all the time in the GC in very small
    programs.
    Defaults to 8 times the nursery.

``PYPY_GC_DEBUG``
    Enable extra checks around collections that are too slow for normal
    use.
    Values are ``0`` (off), ``1`` (on major collections) or ``2`` (also
    on minor collections).

``PYPY_GC_MAX_PINNED``
    The maximal number of pinned objects at any point in time.  Defaults
    to a conservative value depending on nursery size and maximum object
    size inside the nursery.  Useful for debugging by setting it to 0.
