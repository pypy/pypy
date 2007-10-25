import weakref
from pypy.lang.smalltalk import model, constants

class AbstractShadow(object):
    """A shadow is an optional extra bit of information that
    can be attached at run-time to any Smalltalk object.
    """
    def invalidate(self):
        """XXX This should get called whenever the base Smalltalk
        object changes."""

# ____________________________________________________________ 

POINTERS = 0
BYTES = 1
WORDS = 2
WEAK_POINTERS = 3
COMPILED_METHOD = 4

class ClassShadowError(Exception):
    pass

def unwrap_int(w_value):
    if isinstance(w_value, model.W_SmallInteger):
        return w_value.value
    raise ClassShadowError("expected a W_SmallInteger, got %s" % (w_value,))


class ClassShadow(AbstractShadow):
    """A shadow for Smalltalk objects that are classes
    (i.e. used as the class of another Smalltalk object).
    """
    def __init__(self, w_self):
        self.w_self = w_self
        self.invalidate()

    def invalidate(self):
        self.methoddict = {}
        self.s_superclass = None     # the ClassShadow of the super class
        self.s_metaclass = None      # the ClassShadow of the meta class
        self.name = '?' # take care when initing this, metaclasses do not have a name!
        self.invalid = True

    def check_for_updates(self):
        if self.invalid:
            self.update_shadow()

    def update_shadow(self):
        "Update the ClassShadow with data from the w_self class."
        w_self = self.w_self
        # read and painfully decode the format
        classformat = unwrap_int(w_self.fetch(constants.CLASS_FORMAT_INDEX))
        # The classformat in Squeak, as an integer value, is:
        #    <2 bits=instSize//64><5 bits=cClass><4 bits=instSpec>
        #                                    <6 bits=instSize\\64><1 bit=0>
        # In Slang the value is read directly as a boxed integer, so that
        # the code gets a "pointer" whose bits are set as above, but
        # shifted one bit to the left and with the lowest bit set to 1.

        # compute the instance size (really the size, not the number of bytes)
        instsize_lo = (classformat >> 1) & 0x3F
        instsize_hi = (classformat >> (9 + 1)) & 0xC0
        self.instance_size = instsize_lo | instsize_hi
        # decode the instSpec
        format = (classformat >> 7) & 15
        self.instance_varsized = format >= 2
        if format < 4:
            self.instance_kind = POINTERS
        elif format == 4:
            self.instance_kind = WEAK_POINTERS
        elif format == 6:
            self.instance_kind = WORDS
            if self.instance_kind != 0:
                raise ClassShadowError("can't have both words and a non-zero "
                                       "base instance size")
        elif 8 <= format <= 11:
            self.instance_kind = BYTES
            if self.instance_kind != 0:
                raise ClassShadowError("can't have both bytes and a non-zero "
                                       "base instance size")
        elif 12 <= format <= 15:
            self.instance_kind = COMPILED_METHOD
        else:
            raise ClassShadowError("unknown format %d" % (format,))
        # XXX read s_superclass
        # XXX read s_metaclass
        # XXX read the methoddict
        self.invalid = False
        if self.s_superclass is not None:
            self.s_superclass.check_for_updates()
        if self.s_metaclass is not None:
            self.s_metaclass.check_for_updates()

    def new(self, extrasize=0):
        w_cls = self.w_self
        if self.instance_kind == POINTERS:
            return model.W_PointersObject(w_cls, self.instance_size+extrasize)
        elif self.instance_kind == WORDS:
            return model.W_WordsObject(w_cls, extrasize)
        elif self.instance_kind == BYTES:
            return model.W_BytesObject(w_cls, extrasize)
        else:
            raise NotImplementedError(self.instance_kind)

    # _______________________________________________________________
    # Methods for querying the format word, taken from the blue book:
    #
    # included so that we can reproduce code from the reference impl
    # more easily

    def ispointers(self):
        " True if instances of this class have data stored as pointers "
        XXX   # what about weak pointers?
        return self.format == POINTERS

    def iswords(self):
        " True if instances of this class have data stored as numerical words "
        XXX   # what about weak pointers?
        return self.format in (POINTERS, WORDS)

    def isbytes(self):
        " True if instances of this class have data stored as numerical bytes "
        return self.format == BYTES

    def isvariable(self):
        " True if instances of this class have indexed inst variables "
        return self.instance_varsized

    def instsize(self):
        " Number of named instance variables for each instance of this class "
        return self.instance_size

    def inherits_from(self, s_superclass):
        classshadow = self
        while classshadow is not None:
            if classshadow is s_superclass:
                return True
            classshadow = classshadow.s_superclass
        else:
            return False

    # _______________________________________________________________
    # Methods for querying the format word, taken from the blue book:

    def __repr__(self):
        return "<ClassShadow %s>" % (self.name,)

    def lookup(self, selector):
        if selector in self.methoddict:
            return self.methoddict[selector]
        elif self.s_superclass != None:
            return self.s_superclass.lookup(selector)
        else:
            return None

    def installmethod(self, selector, method):
        "NOT_RPYTHON"     # this is only for testing.
        assert isinstance(method, model.W_CompiledMethod)
        self.methoddict[selector] = method
        method.w_compiledin = self.w_self
