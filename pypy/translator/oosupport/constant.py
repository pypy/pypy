"""
___________________________________________________________________________
Constants

Complex code for representing constants.  For each complex constant,
we create an object and record it in the database.  These objects
contain the knowledge about how to access the value of the constant,
as well as the how to initialize it.  The constants are initialized in
two phases so that interdependencies do not prevent a problem.

The initialization process works in two phases:

1. create_pointer(): this creates uninitialized pointers, so that
   circular references can be handled.

2. initialize_data(): initializes everything else.  The constants are
   first sorted by PRIORITY so that CustomDicts are initialized last.

These two methods will be invoked by the ConstantGenerator's gen_constants()
routine.

A backend will typically create its own version of each kind of Const class,
adding at minimum a push() and store() method.  A custom variant of
BaseConstantGenerator is also needed.  These classes can also be chosen
by the genoo.py subclass of the backend
"""

from pypy.rpython.ootypesystem import ootype
import operator

MAX_CONST_PER_STEP = 100

PRIMITIVE_TYPES = set([ootype.Void, ootype.Bool, ootype.Char, ootype.UniChar,
                       ootype.Float, ootype.Signed, ootype.Unsigned,
                       ootype.String, ootype.Unicode, ootype.SignedLongLong,
                       ootype.UnsignedLongLong])

def is_primitive(TYPE):
    return TYPE in PRIMITIVE_TYPES

def push_constant(db, TYPE, value, gen):
    """ General method that pushes the value of the specified constant
    onto the stack.  Use this when you want to load a constant value.
    May or may not create an abstract constant object.
    
    db --- a Database
    TYPE --- the ootype of the constant
    value --- the ootype instance (ootype._list, int, etc)
    gen --- a metavm.Generator
    """

    constgen = db.constant_generator
    
    if is_primitive(TYPE):
        return constgen.push_primitive_constant(gen, TYPE, value)

    const = constgen.record_const(value)
    if const.is_inline():
        const.push_inline(gen, TYPE)
    else:
        constgen.push_constant(gen, const)
        if TYPE is not const.OOTYPE():
            constgen.downcast_constant(gen, value, TYPE)

# ______________________________________________________________________
# Constant generator
#
# The back-end can specify which constant generator to use by setting
# genoo.ConstantGenerator to the appropriate class.  The
# ConstantGenerator handles invoking the constant's initialization
# routines, as well as loading and storing them.
#
# For the most part, no code needs to interact with the constant
# generator --- the rest of the code base should always invoke
# push_constant(), which may delegate to the constant generator if
# needed.

class BaseConstantGenerator(object):

    def __init__(self, db):
        self.db = db
        self.genoo = db.genoo
        self.cache = {}

    # _________________________________________________________________
    # Constant Operations
    #
    # Methods for loading and storing the value of constants.  Clearly,
    # storing the value of a constant is only done internally.  These
    # must be overloaded by the specific backend.  Note that there
    # are some more specific variants below that do not have to be overloaded
    # but may be.

    def push_constant(self, gen, const):
        """
        gen --- a generator
        const --- an AbstractConst object

        Loads the constant onto the stack.  Can be invoked at any time.
        """        
        raise NotImplementedError

    def _store_constant(self, gen, const):
        """
        gen --- a generator
        const --- an AbstractConst object

        stores the constant from the stack
        """
        raise NotImplementedError

    # _________________________________________________________________
    # Optional Constant Operations
    #
    # These allow various hooks at convenient times.  All of them are
    # already implemented and you don't need to overload them.

    def push_primitive_constant(self, gen, TYPE, value):
        """ Invoked when an attempt is made to push a primitive
        constant.  Normally just passes the call onto the code
        generator. """
        gen.push_primitive_constant(TYPE, value)

    def downcast_constant(self, gen, const, EXPECTED_TYPE):
        """ Invoked when the expected type of a const does not match
        const.OOTYPE().  The constant has been pushed.  Normally just
        invokes gen.downcast.  When it finishes, constant should still
        be on the stack. """
        gen.downcast(EXPECTED_TYPE)
    
    def _init_constant(self, const):
        """
        const --- a freshly created AbstractConst object

        Gives the generator a chance to set any fields it wants on the
        constant just after the object is first created.  Not invoked
        while generating constant initialization code, but before.
        """
        pass
    
    def _push_constant_during_init(self, gen, const):
        """
        gen --- a generator
        const --- an AbstractConst object

        Just like push_constant, but only invoked during
        initialization.  By default simply invokes push_constant().
        """        
        return self.push_constant(gen, const)

    def _pre_store_constant(self, gen, const):
        """
        gen --- a generator
        const --- an AbstractConst object

        invoked before the constant's create_pointer() routine is
        called, to prepare the stack in any way needed.  Typically
        does nothing, but sometimes pushes the 'this' pointer if the
        constant will be stored in the field of a singleton object.
        """
        pass

    def _get_key_for_const(self, value):
        return value
    
    # _________________________________________________________________
    # Constant Object Creation
    #
    # Code that deals with creating AbstractConst objects and recording
    # them.  You should not need to change anything here.
    
    def record_const(self, value):
        """ Returns an object representing the constant, remembering
        also any details needed to initialize the constant.  value
        should be an ootype constant value.  Not generally called
        directly, but it can be if desired. """
        assert not is_primitive(value)
        if value in self.cache:
            return self.cache[value]
        const = self._create_complex_const(value)
        key = self._get_key_for_const(value)
        self.cache[key] = const
        self._init_constant(const)
        const.record_dependencies()
        return const

    def _create_complex_const(self, value):

        """ A helper method which creates a Constant wrapper object for
        the given value.  Uses the types defined in the sub-class. """
        
        # Determine if the static type differs from the dynamic type.
        if isinstance(value, ootype._view):
            static_type = value._TYPE
            value = value._inst
        else:
            static_type = None

        # Find the appropriate kind of Const object.
        genoo = self.genoo
        uniq = self.db.unique()
        if isinstance(value, ootype._instance):
            return genoo.InstanceConst(self.db, value, static_type, uniq)
        elif isinstance(value, ootype._record):
            return genoo.RecordConst(self.db, value, uniq)
        elif isinstance(value, ootype._class):
            return genoo.ClassConst(self.db, value, uniq)
        elif isinstance(value, ootype._list):
            return genoo.ListConst(self.db, value, uniq)
        elif isinstance(value, ootype._array):
            return genoo.ArrayConst(self.db, value, uniq)
        elif isinstance(value, ootype._static_meth):
            return genoo.StaticMethodConst(self.db, value, uniq)
        elif isinstance(value, ootype._custom_dict):
            return genoo.CustomDictConst(self.db, value, uniq)
        elif isinstance(value, ootype._dict):
            return genoo.DictConst(self.db, value, uniq)
        elif isinstance(value, ootype._weak_reference):
            return genoo.WeakRefConst(self.db, value, uniq)
        elif value is ootype.null(value._TYPE):
            # for NULL values, we can just use "NULL" const.  This is
            # a fallback since we sometimes have constants of
            # unhandled types which are equal to NULL.
            return genoo.NullConst(self.db, value, uniq)
        else:
            assert False, 'Unknown constant: %s' % value        

    # _________________________________________________________________
    # Constant Generation
    #
    # You will not generally need to overload any of the functions
    # in this section.

    def gen_constants(self, ilasm):

        # Sort constants by priority.  Don't bother with inline
        # constants.
        all_constants = [c for c in self.cache.values() if not c.is_inline()]
        all_constants.sort(key=lambda c: (c.PRIORITY, c.count))

        # Counters to track how many steps we have emitted so far, etc.
        # See _consider_step() for more information.
        self._step_counter = 0
        self._all_counter = 0

        # Now, emit the initialization code:
        gen = self._begin_gen_constants(ilasm, all_constants)
        for const in all_constants:
            self._declare_const(gen, const)
        self._create_pointers(gen, all_constants)
        self._initialize_data(gen, all_constants)
        self._end_step(gen)
        self._end_gen_constants(gen, self._step_counter)

    def _create_pointers(self, gen, all_constants):
        """ Iterates through each constant, creating the pointer for it
        and storing it. """
        gen.add_section("Create Pointer Phase")
        for const in all_constants:
            gen.add_comment("Constant: %s" % const.name)
            self._pre_store_constant(gen, const)
            self._consider_step(gen)
            const.create_pointer(gen)
            self._store_constant(gen, const)

    def _initialize_data(self, gen, all_constants):
        """ Iterates through each constant, initializing its data. """
        gen.add_section("Initialize Data Phase")
        for const in all_constants:
            self._consider_step(gen)
            gen.add_comment("Constant: %s" % const.name)
            self._push_constant_during_init(gen, const)
            self.current_const = const
            if not const.initialize_data(self, gen):
                gen.pop(const.OOTYPE())

    def _consider_step(self, gen):
        """ Considers whether to start a new step at this point.  We
        start a new step every so often to ensure the initialization
        functions don't get too large and upset mono or the JVM or
        what have you. """
        if self._all_counter % MAX_CONST_PER_STEP == 0:
            self._new_step(gen)
        self._all_counter += 1

    def _consider_split_current_function(self, gen):
        """
        Called during constant initialization; if the backend thinks
        the current function is too large, it can close it and open a
        new one, pushing again the constant on the stack. The default
        implementatio does nothing.
        """
        pass

    def _new_step(self, gen):
        self._end_step(gen)
        self._declare_step(gen, self._step_counter) # open the next step

    def _end_step(self, gen):
        """ Ends the current step if one has begun. """
        if self._all_counter != 0:
            self._close_step(gen, self._step_counter) # close previous step
            self._step_counter += 1

    # _________________________________________________________________
    # Abstract functions you must overload

    def _begin_gen_constants(self, ilasm, all_constants):
        """ Invoked with the assembler and sorted list of constants
        before anything else.  Expected to return a generator that will
        be passed around after that (the parameter named 'gen'). """
        raise NotImplementedError

    def _declare_const(self, gen, const):
        """ Invoked once for each constant before any steps are created. """
        raise NotImplementedError        

    def _declare_step(self, gen, stepnum):
        """ Invoked to begin step #stepnum.  stepnum starts with 0 (!)
        and proceeds monotonically. If _declare_step() is invoked,
        there will always be a corresponding call to _close_step(). """
        raise NotImplementedError     
    
    def _close_step(self, gen, stepnum):
        """ Invoked to end step #stepnum.  Never invoked without a
        corresponding call from _declare_step() first. """
        raise NotImplementedError        
    
    def _end_gen_constants(self, gen, numsteps):
        """ Invoked as the very last thing.  numsteps is the total number
        of steps that were created. """
        raise NotImplementedError        

# ______________________________________________________________________
# Constant base class

class AbstractConst(object):
    PRIORITY = 0

    def __init__(self, db, value, count):
        self.db = db
        self.cts = db.genoo.TypeSystem(db)
        self.value = value
        self.count = count

    # ____________________________________________________________
    # Hashing, equality comparison, and repr()
    #
    # Overloaded so that two AbstactConst objects representing
    # the same OOValue are equal.  Provide a sensible repr()
    
    def __hash__(self):
        return hash(self.value)

    def __eq__(self, other):
        return self.value == other.value

    def __ne__(self, other):
        return not self == other

    def __repr__(self):
        return '<Const %s %s>' % (self.name, self.value)

    # ____________________________________________________________
    # Simple query routines

    def OOTYPE(self):
        return self.value._TYPE
    
    def get_name(self):
        pass

    def is_null(self):
        return self.value is ootype.null(self.value._TYPE)

    def is_inline(self):
        """
        Inline constants are not stored as static fields in the
        Constant class, but they are newly created on the stack every
        time they are used. Classes overriding is_inline should
        override push_inline too.  By default only NULL constants are
        inlined.
        """
        return self.is_null()

    def push_inline(self, gen, EXPECTED_TYPE):
        """
        Invoked by push_constant() when is_inline() returns true.
        By default, just pushes NULL as only NULL constants are inlined.
        If you overload this, overload is_inline() too.
        """
        assert self.is_inline() and self.is_null()
        return gen.push_null(EXPECTED_TYPE)        

    # ____________________________________________________________
    # Initializing the constant

    def record_dependencies(self):
        """
        Ensures that all dependent objects are added to the database,
        and any classes that are used are loaded.  Called when the
        constant object is created.
        """
        raise NotImplementedError
    
    def create_pointer(self, gen):
        """
        Creates the pointer representing this object, but does not
        initialize its fields.  First phase of initialization.
        """
        assert not self.is_null()
        gen.new(self.value._TYPE)

    def initialize_data(self, constgen, gen):
        """
        Initializes the internal data.  Begins with a pointer to
        the constant on the stack.  Normally returns something
        false (like, say, None) --- but returns True if it consumes
        the pointer from the stack in the process; otherwise, a pop
        is automatically inserted afterwards.
        """
        raise NotImplementedError

    # ____________________________________________________________
    # Internal helpers
    
    def _record_const_if_complex(self, TYPE, value):
        if not is_primitive(TYPE):
            self.db.constant_generator.record_const(value)


# ______________________________________________________________________
# Null Values
#
# NULL constants of types for which we have no better class use this
# class.  For example, dict item iterators and the like.
    
class NullConst(AbstractConst):
    def __init__(self, db, value, count):
        AbstractConst.__init__(self, db, value, count)
        self.name = 'NULL__%d' % count
        assert self.is_null() and self.is_inline()

    def record_dependencies(self):
        return
    
# ______________________________________________________________________
# Records
    
class RecordConst(AbstractConst):
    def __init__(self, db, record, count):
        AbstractConst.__init__(self, db, record, count)
        self.name = 'RECORD__%d' % count

    def record_dependencies(self):
        if self.value is ootype.null(self.value._TYPE):
            return
        for f_name, (FIELD_TYPE, f_default) in self.value._TYPE._fields.iteritems():
            value = self.value._items[f_name]            
            self._record_const_if_complex(FIELD_TYPE, value)

    def initialize_data(self, constgen, gen):
        assert not self.is_null()
        SELFTYPE = self.value._TYPE
        for f_name, (FIELD_TYPE, f_default) in self.value._TYPE._fields.iteritems():
            if FIELD_TYPE is not ootype.Void:
                gen.dup(SELFTYPE)
                value = self.value._items[f_name]
                push_constant(self.db, FIELD_TYPE, value, gen)
                gen.set_field(SELFTYPE, f_name)

# ______________________________________________________________________
# Instances
    
class InstanceConst(AbstractConst):
    def __init__(self, db, obj, static_type, count):
        AbstractConst.__init__(self, db, obj, count)
        if static_type is None:
            self.static_type = obj._TYPE
        else:
            self.static_type = static_type
            db.genoo.TypeSystem(db).lltype_to_cts(
                obj._TYPE) # force scheduling of obj's class
        class_name = db.class_name(obj._TYPE).replace('.', '_')
        self.name = '%s__%d' % (class_name, count)

    def record_dependencies(self):
        if not self.value:
            return

        INSTANCE = self.value._TYPE
        while INSTANCE is not None:
            for name, (TYPE, default) in INSTANCE._fields.iteritems():
                if TYPE is ootype.Void:
                    continue
                type_ = self.cts.lltype_to_cts(TYPE) # record type
                value = getattr(self.value, name) # record value
                self._record_const_if_complex(TYPE, value)
            INSTANCE = INSTANCE._superclass

    def is_null(self):
        return not self.value

    def _sorted_const_list(self):
        # XXX, horrible hack: first collect all consts, then render
        # CustomDicts at last because their ll_set could need other
        # fields already initialized. We should really think a more
        # general way to handle such things.
        const_list = []
        INSTANCE = self.value._TYPE
        while INSTANCE is not None:
            for name, (TYPE, default) in INSTANCE._fields.iteritems():
                if TYPE is ootype.Void:
                    continue
                value = getattr(self.value, name)
                const_list.append((TYPE, INSTANCE, name, value))
            INSTANCE = INSTANCE._superclass

        def mycmp(x, y):
            if isinstance(x[0], ootype.CustomDict) and not isinstance(y[0], ootype.CustomDict):
                return 1 # a CustomDict is always greater than non-CustomDicts
            elif isinstance(y[0], ootype.CustomDict) and not isinstance(x[0], ootype.CustomDict):
                return -1 # a non-CustomDict is always less than CustomDicts
            else:
                return cmp(x, y)
        const_list.sort(mycmp)

        return const_list

    def initialize_data(self, constgen, gen):
        assert not self.is_null()

        # Get a list of all the constants we'll need to initialize.
        # I am not clear on why this needs to be sorted, actually,
        # but we sort it.
        const_list = self._sorted_const_list()
        
        # Push ourself on the stack, and cast to our actual type if it
        # is not the same as our static type
        SELFTYPE = self.value._TYPE
        if SELFTYPE is not self.static_type:
            gen.downcast(SELFTYPE)

        # Store each of our fields in the sorted order
        for FIELD_TYPE, INSTANCE, name, value in const_list:
            constgen._consider_split_current_function(gen)
            gen.dup(SELFTYPE)
            push_constant(self.db, FIELD_TYPE, value, gen)
            gen.set_field(INSTANCE, name)

# ______________________________________________________________________
# Class constants

class ClassConst(AbstractConst):
    def __init__(self, db, class_, count):
        AbstractConst.__init__(self, db, class_, count)
        self.name = 'CLASS__%d' % count

    def record_dependencies(self):
        INSTANCE = self.value._INSTANCE
        if INSTANCE is not None:
            self.cts.lltype_to_cts(INSTANCE) # force scheduling class generation

    def is_null(self):
        return self.value._INSTANCE is None

    def create_pointer(self, gen):
        assert not self.is_null()
        INSTANCE = self.value._INSTANCE
        gen.getclassobject(INSTANCE)

    def initialize_data(self, constgen, gen):
        pass

# ______________________________________________________________________
# List constants

class ListConst(AbstractConst):
    def __init__(self, db, list, count):
        AbstractConst.__init__(self, db, list, count)
        self.name = 'LIST__%d' % count

    def record_dependencies(self):
        if not self.value:
            return
        for item in self.value._list:
            self._record_const_if_complex(self.value._TYPE.ITEM, item)

    def create_pointer(self, gen):
        assert not self.is_null()
        SELFTYPE = self.value._TYPE

        # XXX --- should we add something special to the generator for
        # this?  I want it to look exactly like it would in normal
        # opcodes...but of course under current system I can't know
        # what normal opcodes would look like as they fall under the
        # perview of each backend rather than oosupport
        
        # Create the list
        gen.new(SELFTYPE)
        
        # And then resize it to the correct size
        gen.dup(SELFTYPE)
        push_constant(self.db, ootype.Signed, len(self.value._list), gen)
        gen.call_method(SELFTYPE, '_ll_resize')

    def _do_not_initialize(self):
        """ Returns True if the list should not be initialized; this
        can be overloaded by the backend if your conditions are wider.
        The default is not to initialize if the list is a list of
        Void. """
        return self.value._TYPE.ITEM is ootype.Void

    def initialize_data(self, constgen, gen):
        assert not self.is_null()
        SELFTYPE = self.value._TYPE
        ITEM = self.value._TYPE.ITEM

        # check for special cases and avoid initialization
        if self._do_not_initialize():
            return

        # set each item in the list using the OOTYPE methods
        for idx, item in enumerate(self.value._list):
            constgen._consider_split_current_function(gen)
            gen.dup(SELFTYPE)
            push_constant(self.db, ootype.Signed, idx, gen)
            push_constant(self.db, ITEM, item, gen)
            gen.prepare_generic_argument(ITEM)
            gen.call_method(SELFTYPE, 'll_setitem_fast')

# ______________________________________________________________________
# Array constants

class ArrayConst(AbstractConst):
    def __init__(self, db, list, count):
        AbstractConst.__init__(self, db, list, count)
        self.name = 'ARRAY__%d' % count

    def record_dependencies(self):
        if not self.value:
            return
        for item in self.value._array:
            self._record_const_if_complex(self.value._TYPE.ITEM, item)

    def create_pointer(self, gen):
        from pypy.objspace.flow.model import Constant
        assert not self.is_null()
        SELFTYPE = self.value._TYPE

        # Create the array
        length = Constant(len(self.value._array), ootype.Signed)
        gen.oonewarray(SELFTYPE, length)
        
    def _do_not_initialize(self):
        """ Returns True if the array should not be initialized; this
        can be overloaded by the backend if your conditions are wider.
        The default is not to initialize if the array is a array of
        Void. """
        return self.value._TYPE.ITEM is ootype.Void

    def initialize_data(self, constgen, gen):
        assert not self.is_null()
        SELFTYPE = self.value._TYPE
        ITEM = self.value._TYPE.ITEM

        # check for special cases and avoid initialization
        if self._do_not_initialize():
            return

        # set each item in the list using the OOTYPE methods
        for idx, item in enumerate(self.value._array):
            constgen._consider_split_current_function(gen)
            gen.dup(SELFTYPE)
            push_constant(self.db, ootype.Signed, idx, gen)
            push_constant(self.db, ITEM, item, gen)
            self._setitem(SELFTYPE, gen)

    def _setitem(self, SELFTYPE, gen):
        gen.call_method(SELFTYPE, 'll_setitem_fast')

# ______________________________________________________________________
# Dictionary constants

class DictConst(AbstractConst):
    PRIORITY = 90

    def __init__(self, db, dict, count):
        AbstractConst.__init__(self, db, dict, count)
        self.name = 'DICT__%d' % count

    def record_dependencies(self):
        if not self.value:
            return
        
        for key, value in self.value._dict.iteritems():
            self._record_const_if_complex(self.value._TYPE._KEYTYPE, key)
            self._record_const_if_complex(self.value._TYPE._VALUETYPE, value)

    def initialize_data(self, constgen, gen):
        assert not self.is_null()
        SELFTYPE = self.value._TYPE
        KEYTYPE = self.value._TYPE._KEYTYPE
        VALUETYPE = self.value._TYPE._VALUETYPE

        gen.add_comment('Initializing dictionary constant')

        if KEYTYPE is ootype.Void:
            assert VALUETYPE is ootype.Void
            return

        for key, value in self.value._dict.iteritems():
            constgen._consider_split_current_function(gen)
            gen.dup(SELFTYPE)
            gen.add_comment('  key=%r value=%r' % (key,value))
            push_constant(self.db, KEYTYPE, key, gen)
            gen.prepare_generic_argument(KEYTYPE)
            push_constant(self.db, VALUETYPE, value, gen)
            gen.prepare_generic_argument(VALUETYPE)
            gen.call_method(SELFTYPE, 'll_set')

class CustomDictConst(DictConst):
    PRIORITY = 100

# ______________________________________________________________________
# Static method constants

class StaticMethodConst(AbstractConst):
    def __init__(self, db, sm, count):
        AbstractConst.__init__(self, db, sm, count)
        self.name = 'DELEGATE__%d' % count

    def record_dependencies(self):
        if self.value is ootype.null(self.value._TYPE):
            return
        self.db.pending_function(self.value.graph)
        self.delegate_type = self.db.record_delegate(self.value._TYPE)

    def initialize_data(self, constgen, gen):
        raise NotImplementedError

# ______________________________________________________________________
# Weak Reference constants

class WeakRefConst(AbstractConst):
    def __init__(self, db, wref, count):
        if wref:
            value = wref.ll_deref()
        else:
            value = None
        AbstractConst.__init__(self, db, value, count)
        self.name = 'WEAKREF__%d' % count

    def OOTYPE(self):
        # Not sure what goes here...?
        return None
    
    def is_null(self):
        return self.value is None

    def record_dependencies(self):
        if self.value is not None:
            self.db.constant_generator.record_const(self.value)
