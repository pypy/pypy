import weakref
from pypy.lang.smalltalk import model, constants, error
from pypy.tool.pairtype import extendabletype

class AbstractShadow(object):
    """A shadow is an optional extra bit of information that
    can be attached at run-time to any Smalltalk object.
    """
    def __init__(self, space, w_self):
        self.space = space
        self._w_self = w_self
    def fetch(self, n0):
        return self.w_self()._fetch(n0)
    def store(self, n0, w_value):
        return self.w_self()._store(n0, w_value)
    def size(self):
        return self.w_self()._size()
    def w_self(self):
        return self._w_self
    def getname(self):
        return repr(self)
    def attach_shadow(self): pass
    def detach_shadow(self): pass
    def sync_shadow(self): pass
   
class AbstractCachingShadow(AbstractShadow):
    def __init__(self, space, w_self):
        AbstractShadow.__init__(self, space, w_self)
        self.invalid = True
        self.invalidate_shadow()

    def detach_shadow(self):
        self.invalidate_shadow()

    def invalidate_shadow(self):
        """This should get called whenever the base Smalltalk
        object changes."""
        if not self.invalid:
            self.invalid = True

    def attach_shadow(self):
        self.update_shadow()

    def sync_shadow(self):
        if self.invalid:
            self.update_shadow()

    def update_shadow(self):
        self.w_self().store_shadow(self)
        self.invalid = False
        self.sync_cache()

    def sync_cache(self):
        raise NotImplementedError()

    def store(self, n0, w_value):
        self.invalidate_shadow()
        AbstractShadow.store(self, n0, w_value)

# ____________________________________________________________ 

POINTERS = 0
BYTES = 1
WORDS = 2
WEAK_POINTERS = 3
COMPILED_METHOD = 4


class MethodNotFound(error.SmalltalkException):
    pass

class ClassShadowError(error.SmalltalkException):
    pass

class ClassShadow(AbstractCachingShadow):
    """A shadow for Smalltalk objects that are classes
    (i.e. used as the class of another Smalltalk object).
    """
    name = None
    def __init__(self, space, w_self):
        self.name = ""
        AbstractCachingShadow.__init__(self, space, w_self)
    def invalidate_shadow(self):
        AbstractCachingShadow.invalidate_shadow(self)
        self.w_methoddict = None
        self.w_superclass = None

    def getname(self):
        return "%s class" % (self.name or '?',)

    def sync_cache(self):
        "Update the ClassShadow with data from the w_self class."

        w_self = self.w_self()
        # read and painfully decode the format
        classformat = self.space.unwrap_int(
            w_self._fetch(constants.CLASS_FORMAT_INDEX))
        # The classformat in Squeak, as an integer value, is:
        #    <2 bits=instSize//64><5 bits=cClass><4 bits=instSpec>
        #                                    <6 bits=instSize\\64><1 bit=0>
        # In Slang the value is read directly as a boxed integer, so that
        # the code gets a "pointer" whose bits are set as above, but
        # shifted one bit to the left and with the lowest bit set to 1.

        # compute the instance size (really the size, not the number of bytes)
        instsize_lo = (classformat >> 1) & 0x3F
        instsize_hi = (classformat >> (9 + 1)) & 0xC0
        self.instance_size = (instsize_lo | instsize_hi) - 1  # subtract hdr
        # decode the instSpec
        format = (classformat >> 7) & 15
        self.instance_varsized = format >= 2
        if format < 4:
            self.instance_kind = POINTERS
        elif format == 4:
            self.instance_kind = WEAK_POINTERS
        elif format == 6:
            self.instance_kind = WORDS
            if self.instance_size != 0:
                raise ClassShadowError("can't have both words and a non-zero "
                                       "base instance size")
        elif 8 <= format <= 11:
            self.instance_kind = BYTES
            if self.instance_size != 0:
                raise ClassShadowError("can't have both bytes and a non-zero "
                                       "base instance size")
        elif 12 <= format <= 15:
            self.instance_kind = COMPILED_METHOD
        else:
            raise ClassShadowError("unknown format %d" % (format,))

        self.guess_class_name()

        # read the methoddict
        w_methoddict = w_self._fetch(constants.CLASS_METHODDICT_INDEX)
        assert isinstance(w_methoddict, model.W_PointersObject)
        self.w_methoddict = w_methoddict

        w_superclass = w_self._fetch(constants.CLASS_SUPERCLASS_INDEX)
        if w_superclass.is_same_object(self.space.w_nil):
            self.w_superclass = None
        else:
            assert isinstance(w_superclass, model.W_PointersObject)
            self.w_superclass = w_superclass

    def guess_class_name(self):
        w_self = self.w_self()
        w_name = None

        # read the name
        if w_self.size() > constants.CLASS_NAME_INDEX:
            w_name = w_self._fetch(constants.CLASS_NAME_INDEX)
        else:
            # Some heuristic to find the classname
            # Only used for debugging
            # XXX This is highly experimental XXX
            # if the name-pos of class is not bytesobject,
            # we are probably holding a metaclass instead of a class.
            # metaclasses hold a pointer to the real class in the last
            # slot. This is pos 6 in mini.image and higher in squeak3.9
            w_realclass = w_self._fetch(w_self.size() - 1)
            assert isinstance(w_realclass, model.W_PointersObject)
            if w_realclass.size() > constants.CLASS_NAME_INDEX:
                # TODO ADD TEST WHICH GOES OVER THIS PART
                w_name = w_realclass._fetch(constants.CLASS_NAME_INDEX)

        if isinstance(w_name, model.W_BytesObject):
            self.name = w_name.as_string()

    def new(self, extrasize=0):
        w_cls = self.w_self()
        if self.instance_kind == POINTERS:
            w_new = model.W_PointersObject(w_cls, self.instance_size+extrasize)
        elif self.instance_kind == WORDS:
            w_new = model.W_WordsObject(w_cls, extrasize)
        elif self.instance_kind == BYTES:
            w_new = model.W_BytesObject(w_cls, extrasize)
        elif self.instance_kind == COMPILED_METHOD:
            w_new = model.W_CompiledMethod(extrasize)
        else:
            raise NotImplementedError(self.instance_kind)
        return w_new

    def s_methoddict(self):
        return self.w_methoddict.as_methoddict_get_shadow(self.space)

    def s_superclass(self):
        if self.w_superclass is None:
            return None
        return self.w_superclass.as_class_get_shadow(self.space)

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
            classshadow = classshadow.s_superclass()
        else:
            return False

    # _______________________________________________________________
    # Methods for querying the format word, taken from the blue book:

    def __repr__(self):
        return "<ClassShadow %s>" % (self.name or '?',)

    def lookup(self, selector):
        look_in_shadow = self
        while look_in_shadow is not None:
            try:
                w_method = look_in_shadow.s_methoddict().methoddict[selector]
                return w_method
            except KeyError, e:
                look_in_shadow = look_in_shadow.s_superclass()
        raise MethodNotFound(self, selector)

    def initialize_methoddict(self):
        "NOT_RPYTHON"     # this is only for testing.
        if self.w_methoddict is None:
            self.w_methoddict = model.W_PointersObject(None, 2)
            self.w_methoddict._store(1, model.W_PointersObject(None, 0))
            self.s_methoddict().invalid = False

    def installmethod(self, selector, method):
        "NOT_RPYTHON"     # this is only for testing.
        self.initialize_methoddict()
        self.s_methoddict().methoddict[selector] = method
        if isinstance(method, model.W_CompiledMethod):
            method.w_compiledin = self.w_self()

class MethodDictionaryShadow(AbstractCachingShadow):

    def invalidate_shadow(self):
        AbstractCachingShadow.invalidate_shadow(self)
        self.methoddict = None

    def sync_cache(self):
        w_values = self.w_self()._fetch(constants.METHODDICT_VALUES_INDEX)
        assert isinstance(w_values, model.W_PointersObject)
        s_values = w_values.get_shadow(self.space)
        # XXX Should add!
        # s_values.notifyinvalid(self)
        size = self.w_self().size() - constants.METHODDICT_NAMES_INDEX
        self.methoddict = {}
        for i in range(size):
            w_selector = self.w_self()._fetch(constants.METHODDICT_NAMES_INDEX+i)
            if not w_selector.is_same_object(self.space.w_nil):
                if not isinstance(w_selector, model.W_BytesObject):
                    raise ClassShadowError("bogus selector in method dict")
                selector = w_selector.as_string()
                w_compiledmethod = w_values._fetch(i)
                if not isinstance(w_compiledmethod, model.W_CompiledMethod):
                    raise ClassShadowError("the methoddict must contain "
                                           "CompiledMethods only for now")
                self.methoddict[selector] = w_compiledmethod


class AbstractRedirectingShadow(AbstractShadow):
    def __init__(self, space, w_self):
        AbstractShadow.__init__(self, space, w_self)
        self._w_self_size = self.w_self().size()
    def fetch(self, n0):
        raise NotImplementedError()
    def store(self, n0, w_value):
        raise NotImplementedError()
    def size(self):
        return self._w_self_size

    def attach_shadow(self):
        AbstractShadow.attach_shadow(self)
        for i in range(self._w_self_size):
            self.copy_from_w_self(i)
        self.w_self()._vars = None

    def detach_shadow(self):
        self.w_self()._vars = [self.space.w_nil] * self._w_self_size
        for i in range(self._w_self_size):
            self.copy_to_w_self(i)

    def copy_from_w_self(self, n0):
        self.store(n0, self.w_self()._fetch(n0))
    def copy_to_w_self(self, n0):
        self.w_self()._store(n0, self.fetch(n0))
 
class ContextPartShadow(AbstractRedirectingShadow):

    __metaclass__ = extendabletype

    def __init__(self, space, w_self):
        self._w_sender = space.w_nil
        self._stack = []
        self.currentBytecode = -1
        AbstractRedirectingShadow.__init__(self, space, w_self)

    @staticmethod
    def is_block_context(w_pointers, space):
        method_or_argc = w_pointers.fetch(space, constants.MTHDCTX_METHOD)
        return method_or_argc.getclass(space).is_same_object(
            space.w_SmallInteger)

    def fetch(self, n0):
        if n0 == constants.CTXPART_SENDER_INDEX:
            return self.w_sender()
        if n0 == constants.CTXPART_PC_INDEX:
            return self.wrap_pc()
        if n0 == constants.CTXPART_STACKP_INDEX:
            return self.wrap_stackpointer()
        if self.stackstart() <= n0 < self.external_stackpointer():
            return self._stack[n0-self.stackstart()]
        if self.external_stackpointer() <= n0 < self.stackend():
            return self.space.w_nil
        else:
            # XXX later should store tail out of known context part as well
            raise error.WrapperException("Index in context out of bounds")

    def store(self, n0, w_value):
        if n0 == constants.CTXPART_SENDER_INDEX:
            return self.store_w_sender(w_value)
        if n0 == constants.CTXPART_PC_INDEX:
            return self.store_unwrap_pc(w_value)
        if n0 == constants.CTXPART_STACKP_INDEX:
            return self.unwrap_store_stackpointer(w_value)
        if self.stackstart() <= n0 < self.external_stackpointer():
            self._stack[n0 - self.stackstart()] = w_value
            return
        if self.external_stackpointer() <= n0 < self.stackend():
            return
        else:
            # XXX later should store tail out of known context part as well
            raise error.WrapperException("Index in context out of bounds")

    def unwrap_store_stackpointer(self, w_sp1):
        # the stackpointer in the W_PointersObject starts counting at the
        # tempframe start
        # Stackpointer from smalltalk world == stacksize in python world
        self.store_stackpointer(self.space.unwrap_int(w_sp1) -
                                self.tempsize())

    def store_stackpointer(self, size):
        if size < len(self._stack):
            # TODO Warn back to user
            assert size >= 0
            self._stack = self._stack[:size]
        else:
            add = [self.space.w_nil] * (size - len(self._stack))
            self._stack.extend(add)

    def wrap_stackpointer(self):
        return self.space.wrap_int(len(self._stack) + 
                                self.tempsize())

    def external_stackpointer(self):
        return len(self._stack) + self.stackstart()

    def w_home(self):
        raise NotImplementedError()

    def s_home(self):
        return self.w_home().as_methodcontext_get_shadow(self.space)
    
    def stackstart(self):
        raise NotImplementedError()

    def stackpointer_offset(self):
        raise NotImplementedError()

    def w_receiver(self):
        " Return self of the method, or the method that contains the block "
        return self.s_home().w_receiver()

    def store_w_sender(self, w_sender):
        assert isinstance(w_sender, model.W_PointersObject)
        self._w_sender = w_sender

    def w_sender(self):
        return self._w_sender

    def s_sender(self):
        w_sender = self.w_sender()
        if w_sender.is_same_object(self.space.w_nil):
            return None
        else:
            return w_sender.as_context_get_shadow(self.space)

    def store_unwrap_pc(self, w_pc):
        if w_pc.is_same_object(self.space.w_nil):
            return
        pc = self.space.unwrap_int(w_pc)
        pc -= self.w_method().bytecodeoffset()
        pc -= 1
        self.store_pc(pc)

    def wrap_pc(self):
        pc = self.pc()
        pc += 1
        pc += self.w_method().bytecodeoffset()
        return self.space.wrap_int(pc)

    def pc(self):
        return self._pc

    def store_pc(self, newpc):
        self._pc = newpc

    def stackpointer_offset(self):
        raise NotImplementedError()

    # ______________________________________________________________________
    # Method that contains the bytecode for this method/block context

    def w_method(self):
        return self.s_home().w_method()

    def getbytecode(self):
        assert self._pc >= 0
        bytecode = self.w_method().bytes[self._pc]
        currentBytecode = ord(bytecode)
        self._pc += 1
        return currentBytecode

    def getNextBytecode(self):
        self.currentBytecode = self.getbytecode()
        return self.currentBytecode

    # ______________________________________________________________________
    # Temporary Variables
    #
    # Are always fetched relative to the home method context.
    
    def gettemp(self, index):
        return self.s_home().gettemp(index)

    def settemp(self, index, w_value):
        self.s_home().settemp(index, w_value)

    # ______________________________________________________________________
    # Stack Manipulation
    def pop(self):
        return self._stack.pop()

    def push(self, w_v):
        self._stack.append(w_v)

    def push_all(self, lst):
        self._stack.extend(lst)

    def top(self):
        return self.peek(0)
        
    def peek(self, idx):
        return self._stack[-(idx + 1)]

    def pop_n(self, n):
        assert n >= 0
        start = len(self._stack) - n
        assert start >= 0          # XXX what if this fails?
        del self._stack[start:]

    def stack(self):
        return self._stack

    def pop_and_return_n(self, n):
        assert n >= 0
        start = len(self._stack) - n
        assert start >= 0          # XXX what if this fails?
        res = self._stack[start:]
        del self._stack[start:]
        return res

    def stackend(self):
        # XXX this is incorrect when there is subclassing
        return self._w_self_size

    def tempsize(self):
        raise NotImplementedError()

class BlockContextShadow(ContextPartShadow):

    @staticmethod
    def make_context(space, w_home, w_sender, argcnt, initialip):
        # create and attach a shadow manually, to not have to carefully put things
        # into the right places in the W_PointersObject
        # XXX could hack some more to never have to create the _vars of w_result
        contextsize = w_home.as_methodcontext_get_shadow(space).myblocksize()
        w_result = model.W_PointersObject(space.w_BlockContext, contextsize)
        s_result = BlockContextShadow(space, w_result)
        w_result.store_shadow(s_result)
        s_result.store_expected_argument_count(argcnt)
        s_result.store_initialip(initialip)
        s_result.store_w_home(w_home)
        s_result.store_pc(initialip)
        return w_result

    def fetch(self, n0):
        if n0 == constants.BLKCTX_HOME_INDEX:
            return self.w_home()
        if n0 == constants.BLKCTX_INITIAL_IP_INDEX:
            return self.wrap_initialip()
        if n0 == constants.BLKCTX_BLOCK_ARGUMENT_COUNT_INDEX:
            return self.wrap_eargc()
        else:
            return ContextPartShadow.fetch(self, n0)

    def store(self, n0, w_value):
        if n0 == constants.BLKCTX_HOME_INDEX:
            return self.store_w_home(w_value)
        if n0 == constants.BLKCTX_INITIAL_IP_INDEX:
            return self.unwrap_store_initialip(w_value)
        if n0 == constants.BLKCTX_BLOCK_ARGUMENT_COUNT_INDEX:
            return self.unwrap_store_eargc(w_value)
        else:
            return ContextPartShadow.store(self, n0, w_value)

    def attach_shadow(self):
        # Make sure the home context is updated first
        self.copy_from_w_self(constants.BLKCTX_HOME_INDEX)
        ContextPartShadow.attach_shadow(self)

    def unwrap_store_initialip(self, w_value):
        initialip = self.space.unwrap_int(w_value)
        initialip -= 1 + self.w_method().getliteralsize()
        self.store_initialip(initialip)

    def wrap_initialip(self):
        initialip = self.initialip()
        initialip += 1 + self.w_method().getliteralsize()
        return self.space.wrap_int(initialip)

    def unwrap_store_eargc(self, w_value):
        self.store_expected_argument_count(self.space.unwrap_int(w_value))
    
    def wrap_eargc(self):
        return self.space.wrap_int(self.expected_argument_count())

    def expected_argument_count(self):
        return self._eargc

    def store_expected_argument_count(self, argc):
        self._eargc = argc

    def initialip(self):
        return self._initialip
        
    def store_initialip(self, initialip):
        self._initialip = initialip
        
    def store_w_home(self, w_home):
        assert isinstance(w_home, model.W_PointersObject)
        self._w_home = w_home

    def w_home(self):
        return self._w_home

    def reset_stack(self):
        self._stack = []

    def stackstart(self):
        return constants.BLKCTX_STACK_START

    def stackpointer_offset(self):
        return constants.BLKCTX_STACK_START

    def tempsize(self):
        # A blockcontext doesn't have any temps
        return 0

class MethodContextShadow(ContextPartShadow):
    def __init__(self, space, w_self):
        self.w_receiver_map = space.w_nil
        self._w_receiver = None
        ContextPartShadow.__init__(self, space, w_self)

    @staticmethod
    def make_context(space, w_method, w_receiver,
                     arguments, w_sender=None):
        # From blue book: normal mc have place for 12 temps+maxstack
        # mc for methods with islarge flag turned on 32
        size = 12 + w_method.islarge * 20 + w_method.argsize
        w_result = space.w_MethodContext.as_class_get_shadow(space).new(size)
        assert isinstance(w_result, model.W_PointersObject)
        # create and attach a shadow manually, to not have to carefully put things
        # into the right places in the W_PointersObject
        # XXX could hack some more to never have to create the _vars of w_result
        s_result = MethodContextShadow(space, w_result)
        w_result.store_shadow(s_result)
        s_result.store_w_method(w_method)
        if w_sender:
            s_result.store_w_sender(w_sender)
        s_result.store_w_receiver(w_receiver)
        s_result.store_pc(0)
        s_result._temps = [space.w_nil] * w_method.tempsize
        for i in range(len(arguments)):
            s_result.settemp(i, arguments[i])
        return w_result

    def fetch(self, n0):
        if n0 == constants.MTHDCTX_METHOD:
            return self.w_method()
        if n0 == constants.MTHDCTX_RECEIVER_MAP:
            return self.w_receiver_map
        if n0 == constants.MTHDCTX_RECEIVER:
            return self.w_receiver()
        if (0 <= n0-constants.MTHDCTX_TEMP_FRAME_START <
                 self.tempsize()):
            return self.gettemp(n0-constants.MTHDCTX_TEMP_FRAME_START)
        else:
            return ContextPartShadow.fetch(self, n0)

    def store(self, n0, w_value):
        if n0 == constants.MTHDCTX_METHOD:
            return self.store_w_method(w_value)
        if n0 == constants.MTHDCTX_RECEIVER_MAP:
            self.w_receiver_map = w_value
            return
        if n0 == constants.MTHDCTX_RECEIVER:
            self.store_w_receiver(w_value)
            return
        if (0 <= n0-constants.MTHDCTX_TEMP_FRAME_START <
                 self.tempsize()):
            return self.settemp(n0-constants.MTHDCTX_TEMP_FRAME_START,
                                w_value)
        else:
            return ContextPartShadow.store(self, n0, w_value)
    
    def attach_shadow(self):
        # Make sure the method is updated first
        self.copy_from_w_self(constants.MTHDCTX_METHOD)
        # And that there is space for the temps
        self._temps = [self.space.w_nil] * self.tempsize()
        ContextPartShadow.attach_shadow(self)

    def tempsize(self):
        return self.w_method().tempsize

    def w_method(self):
        return self._w_method

    def store_w_method(self, w_method):
        assert isinstance(w_method, model.W_CompiledMethod)
        self._w_method = w_method

    def w_receiver(self):
        return self._w_receiver

    def store_w_receiver(self, w_receiver):
        self._w_receiver = w_receiver

    def gettemp(self, index0):
        return self._temps[index0]

    def settemp(self, index0, w_value):
        self._temps[index0] = w_value

    def w_home(self):
        return self.w_self()

    def s_home(self):
        return self

    def stackpointer_offset(self):
        return constants.MTHDCTX_TEMP_FRAME_START

    def stackstart(self):
        return (constants.MTHDCTX_TEMP_FRAME_START +
                self.tempsize())

    def myblocksize(self):
        return self.size() - self.tempsize()
