import sys
from rpython.rlib.objectmodel import specialize
from rpython.rlib.rstring import StringBuilder
from rpython.rlib import rgc

MAX_CODES = 8000

# ____________________________________________________________


class VMProf(object):

    def __init__(self):
        "NOT_RPYTHON: use get_vmprof()"
        self._code_classes = set()
        self._gather_all_code_objs = lambda: None
        self._cleanup_()

    def _cleanup_(self):
        self._current_codes = None
        if sys.maxint == 2147483647:
            self._code_unique_id = 0 # XXX this is wrong, it won't work on 32bit
        else:
            self._code_unique_id = 0x7000000000000000

    @specialize.argtype(1)
    def register_code(self, code, name):
        """Register the code object.  Call when a new code object is made.
        """
        if code._vmprof_unique_id != 0:
            return
        uid = self._code_unique_id + 4    # so we have two bits to mark stuff
        code._vmprof_unique_id = uid
        self._code_unique_id = uid
        #
        b = self._current_codes
        if b is None:
            b = self._current_codes = StringBuilder()
        b.append('\x02')
        write_long_to_string_builder(uid, b)
        write_long_to_string_builder(len(name), b)
        b.append(name)
        if b.getlength() >= MAX_CODES:
            self._flush_codes()

    def register_code_object_class(self, CodeClass, full_name_func):
        """NOT_RPYTHON
        Register statically the class 'CodeClass' as containing user
        code objects.

        full_name_func() is a function called at runtime with an
        instance of CodeClass and it should return a string.  This
        is the string stored in the vmprof file identifying the code
        object.  It can be directly an unbound method of CodeClass.

        Instances of the CodeClass will have a new attribute called
        '_vmprof_unique_id', but that's managed internally.
        """
        if CodeClass in self._code_classes:
            return
        CodeClass._vmprof_unique_id = 0     # default value: "unknown"
        self._code_classes.add(CodeClass)
        #
        def try_cast_to_pycode(gcref):
            return rgc.try_cast_gcref_to_instance(CodeClass, gcref)
        #
        def gather_all_code_objs():
            all_code_objs = rgc.do_get_objects(try_cast_to_pycode)
            for code in all_code_objs:
                self.register_code(code, full_name_func(code))
            prev()
        # make a chained list of the gather() functions for all
        # the types of code objects
        prev = self._gather_all_code_objs
        self._gather_all_code_objs = gather_all_code_objs


def write_long_to_string_builder(l, b):
    b.append(chr(l & 0xff))
    b.append(chr((l >> 8) & 0xff))
    b.append(chr((l >> 16) & 0xff))
    b.append(chr((l >> 24) & 0xff))
    if sys.maxint > 2147483647:
        b.append(chr((l >> 32) & 0xff))
        b.append(chr((l >> 40) & 0xff))
        b.append(chr((l >> 48) & 0xff))
        b.append(chr((l >> 56) & 0xff))


@specialize.memo()
def get_vmprof():
    return VMProf()
