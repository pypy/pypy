Use "tagged pointers" to represent small enough integer values: Integers that
fit into 31 bits (respective 63 bits on 64 bit machines) are not represented by
boxing them in an instance of ``W_IntObject``. Instead they are represented as a
pointer having the lowest bit set and the rest of the bits used to store the
value of the integer. This gives a small speedup for integer operations as well
as better memory behaviour.
