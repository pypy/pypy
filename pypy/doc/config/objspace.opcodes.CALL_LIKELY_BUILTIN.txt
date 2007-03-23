Introduce a new opcode called ``CALL_LIKELY_BUILTIN``. It is used when something
is called, that looks like a builtin function (but could in reality be shadowed
by a name in the module globals). For all module globals dictionaries it is
then tracked which builtin name is shadowed in this module. If the
``CALL_LIKELY_BUILTIN`` opcode is executed, it is checked whether the builtin is
shadowed. If not, the corresponding builtin is called. Otherwise the object that
is shadowing it is called instead. If no shadowing is happening, this saves two
dictionary lookups on calls to builtins.

For more information, see the section in `Standard Interpreter Optimizations`_.

.. _`Standard Interpreter Optimizations`: ../interpreter-optimizations.html#call-likely-builtin
