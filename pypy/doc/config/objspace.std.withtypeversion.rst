This (mostly internal) option enables "type versions": Every type object gets an
(only internally visible) version that is updated when the type's dict is
changed. This is e.g. used for invalidating caches. It does not make sense to
enable this option alone.

.. internal
