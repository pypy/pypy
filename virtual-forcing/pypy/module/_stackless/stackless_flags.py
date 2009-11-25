"""
basic definitions for tasklet flags.
For simplicity and compatibility,
they are defined the same for coroutines,
even if they are not used.

taken from tasklet_structs.h
----------------------------

/***************************************************************************

    Tasklet Flag Definition
    -----------------------

    blocked:        The tasklet is either waiting in a channel for
                    writing (1) or reading (-1) or not blocked (0).
                    Maintained by the channel logic. Do not change.

    atomic:         If true, schedulers will never switch. Driven by
                    the code object or dynamically, see below.

    ignore_nesting: Allows auto-scheduling, even if nesting_level
                    is not zero.

    autoschedule:   The tasklet likes to be auto-scheduled. User driven.

    block_trap:     Debugging aid. Whenever the tasklet would be
                    blocked by a channel, an exception is raised.

    is_zombie:      This tasklet is almost dead, its deallocation has
                    started. The tasklet *must* die at some time, or the
                    process can never end.

    pending_irq:    If set, an interrupt was issued during an atomic
                    operation, and should be handled when possible.


    Policy for atomic/autoschedule and switching:
    ---------------------------------------------
    A tasklet switch can always be done explicitly by calling schedule().
    Atomic and schedule are concerned with automatic features.

    atomic  autoschedule

        1       any     Neither a scheduler nor a watchdog will
                        try to switch this tasklet.

        0       0       The tasklet can be stopped on desire, or it
                        can be killed by an exception.

        0       1       Like above, plus auto-scheduling is enabled.

    Default settings:
    -----------------
    All flags are zero by default.

 ***************************************************************************/

typedef struct _tasklet_flags {
        int blocked: 2;
        unsigned int atomic: 1;
        unsigned int ignore_nesting: 1;
        unsigned int autoschedule: 1;
        unsigned int block_trap: 1;
        unsigned int is_zombie: 1;
        unsigned int pending_irq: 1;
} PyTaskletFlagStruc;
"""

from pypy.rlib.rarithmetic import LONG_BIT, intmask

class BitSetDef(object):
    __slots__ = "_names __dict__ _attrname".split()

    def __init__(self, _attrname):
        self._names = []
        self._attrname = _attrname
        
    def __setattr__(self, key, value):
        if key not in self.__slots__:
            assert key not in self.__dict__
            self._names.append(key)
        object.__setattr__(self, key, value)

    def __iter__(self):
        return self._enum_objects()
    
    def _enum_objects(self):
        for name in self._names:
            yield name, getattr(self, name)

# negative values are user-writable
flags = BitSetDef("flags")
flags.blocked           =   2, """writing (1) or reading (-1) or not blocked (0)"""
flags.atomic            =  -1, """If true, schedulers will never switch"""
flags.ignore_nesting    =  -1, """allow auto-scheduling in nested interpreters"""
flags.autoschedule      =  -1, """enable auto-scheduling"""
flags.block_trap        =  -1, """raise an exception instead of blocking"""
flags.is_zombie         =   1, """__del__ is in progress"""
flags.pending_irq       =   1, """an interrupt occured while being atomic"""

def make_get_bits(name, bits, shift):
    """ return a bool for single bits, signed int otherwise """
    signmask = 1 << (bits - 1 + shift)
    lshift = bits + shift
    rshift = bits
    if bits == 1:
        return "bool(%s & 0x%x)" % (name, signmask)
    else:
        return "intmask(%s << (LONG_BIT-%d)) >> (LONG_BIT-%d)" % (name, lshift, rshift)

def make_set_bits(name, bits, shift):
    datamask = int('1' * bits, 2)
    clearmask = datamask << shift
    return "%s & ~0x%x | (value & 0x%x) << %d" % (name, clearmask, datamask, shift)

def gen_code():
    from cStringIO import StringIO
    f = StringIO()
    print >> f, "class StacklessFlags(object):"
    print >> f, "    _mixin_ = True"
    shift = 0
    field = "self.%s" % flags._attrname
    for name, (bits, doc) in flags:
        write, bits = bits < 0, abs(bits)
        print >> f
        print >> f, '    def get_%s(self):' % name
        print >> f, '        """%s"""' % doc
        print >> f, '        return %s' % make_get_bits(field, bits, shift)
        print >> f, '    def set_%s(self, value):' % name
        print >> f, '        """%s"""' % doc
        print >> f, '        %s = %s' % (field, make_set_bits(field, bits, shift))
        print >> f, '    set_%s._public = %s' % (name, write)
        shift += bits
    return f.getvalue()

# BEGIN generated code
class StacklessFlags(object):
    _mixin_ = True

    def get_blocked(self):
        """writing (1) or reading (-1) or not blocked (0)"""
        return intmask(self.flags << (LONG_BIT-2)) >> (LONG_BIT-2)
    def set_blocked(self, value):
        """writing (1) or reading (-1) or not blocked (0)"""
        self.flags = self.flags & ~0x3 | (value & 0x3) << 0
    set_blocked._public = False

    def get_atomic(self):
        """If true, schedulers will never switch"""
        return bool(self.flags & 0x4)
    def set_atomic(self, value):
        """If true, schedulers will never switch"""
        self.flags = self.flags & ~0x4 | (value & 0x1) << 2
    set_atomic._public = True

    def get_ignore_nesting(self):
        """allow auto-scheduling in nested interpreters"""
        return bool(self.flags & 0x8)
    def set_ignore_nesting(self, value):
        """allow auto-scheduling in nested interpreters"""
        self.flags = self.flags & ~0x8 | (value & 0x1) << 3
    set_ignore_nesting._public = True

    def get_autoschedule(self):
        """enable auto-scheduling"""
        return bool(self.flags & 0x10)
    def set_autoschedule(self, value):
        """enable auto-scheduling"""
        self.flags = self.flags & ~0x10 | (value & 0x1) << 4
    set_autoschedule._public = True

    def get_block_trap(self):
        """raise an exception instead of blocking"""
        return bool(self.flags & 0x20)
    def set_block_trap(self, value):
        """raise an exception instead of blocking"""
        self.flags = self.flags & ~0x20 | (value & 0x1) << 5
    set_block_trap._public = True

    def get_is_zombie(self):
        """__del__ is in progress"""
        return bool(self.flags & 0x40)
    def set_is_zombie(self, value):
        """__del__ is in progress"""
        self.flags = self.flags & ~0x40 | (value & 0x1) << 6
    set_is_zombie._public = False

    def get_pending_irq(self):
        """an interrupt occured while being atomic"""
        return bool(self.flags & 0x80)
    def set_pending_irq(self, value):
        """an interrupt occured while being atomic"""
        self.flags = self.flags & ~0x80 | (value & 0x1) << 7
    set_pending_irq._public = False

# END generated code

if __name__ == '__main__':
    # paste this into the file
    print gen_code()
