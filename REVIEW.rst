REVIEW
======

* Why is width == 1 in W_VoidBox.descr_{get,set}item? That doesn't seem right.
* expose endianess on dtypes
* RecordType.str_format should use Builder
* IntP and UIntP aren't the right size, they should be the same size of rffi.VOIDP, not as Signed/Unsigned
* Instead of setup() can we please have get_alignment on the Type class.
* Need more tests for nested record types, I'm pretty sure they're broken.
* kill all the trailing whitespace ;)
* Fix failing tests.
