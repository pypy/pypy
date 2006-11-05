"""
___________________________________________________________________________
Constants

Complex code for representing constants.  For each complex constant,
we create an object and record it in the database.  These objects
contain the knowledge about how to access the value of the constant,
as well as the how to initialize it.  The constants are initialized in
several phases so that interdependencies do not prevent a problem.

The initialization process works like this:

1. create_pointer(): this creates uninitialized pointers, so that
   circular references can be handled.

2. initialize_opaque(): initializes all objects except for
   CustomDicts.  This basically allows any operation that treats the
   object as an opaque pointer.  Most initializations complete here.

3. initialize_full(): initializes custom dicts: objects are inserted
   into dicts here because their fields have been initialized.  This
   assumes that no custom dicts are inserted into any other custom dicts.

These three methods will be invoked by the database's gen_constants()
routine.
"""

from pypy.rpython.ootypesystem import ootype

PRIMITIVE_TYPES = set([ootype.Void, ootype.Bool, ootype.Char, ootype.UniChar,
                       ootype.Float, ootype.Signed, ootype.Unsigned,
                       ootype.String, ootype.SignedLongLong,
                       ootype.UnsignedLongLong])

def is_primitive(TYPE):
    return TYPE in PRIMITIVE_TYPES

def push_constant(db, TYPE, value, gen):
    """ Class method that pushes the value of the specified
    constant onto the stack.  May or may not create an abstract constant
    object.
    
    db --- a Database
    TYPE --- the ootype of the constant
    value --- the ootype instance
    gen --- a metavm.Generator
    """
    if is_primitive(TYPE):
        return gen.push_primitive_constant(TYPE, value)

    const = db.record_const(value)
    if const.is_null():
        gen.push_null(TYPE)
    else:
        const.push(gen)

# ______________________________________________________________________
# Constant generator

class ConstantGenerator(object):
    pass

# ______________________________________________________________________
# Constant base class

class AbstractConst(object):
    PRIORITY = 0

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
    
    def get_name(self):
        pass

    def get_type(self):
        pass

    def is_null(self):
        return self.value is ootype.null(self.value._TYPE)

    def is_inline(self):
        """
        Inline constants are not stored as static fields in the
        Constant class, but they are newly created on the stack every
        time they are used. Classes overriding is_inline should
        override _load too.
        """
        return self.is_null() # by default only null constants are inlined

    # ____________________________________________________________
    # Loading and storing the constant
    #
    # These method are left here as an example.  They are commented
    # out because they must be implemented by the backend as a mix-in,
    # and this way there is no conflict between the two base classes.

    #def push(self, gen):
    #    """
    #    Pushes the value of this constant onto the stack.
    #    """
    #    raise NotImplementedException

    #def store(self, gen):
    #    """
    #    The value of the constant will be pushed onto the stack;
    #    store places it somewhere so it can later be loaded.
    #    """
    #    raise NotImplementedException

    # ____________________________________________________________
    # Initializing the constant

    def record_dependencies(self):
        """
        Ensures that all dependent objects are added to the database,
        and any classes that are used are loaded.  Called when the
        constant object is created.
        """
        raise NotImplementedException
    
    def create_pointer(self, gen):
        """
        Creates the pointer representing this object, but does not
        initialize its fields.  First phase of initialization.
        """
        raise NotImplementedException

    def initialize_opaque(self, gen):
        """
        Initializes any constants that only use other constants in an
        opaque fashion, without relying on them being fully initialized.
        The big exception are custom dictionaries.
        """
        raise NotImplementedException

    def initialize_full(self, gen):
        """
        Initializes all remaining constants, such as custom dicts,
        that inspect the fields of their arguments.  If it is ever the
        case that such constants try to access one another, we'll need
        to add a dependence graph, but currently the execution order
        of this function between constants is undefined.
        """
        raise NotImplementedException

    # ____________________________________________________________
    # Internal helpers
    
    def _record_const_if_complex(self, TYPE, value):
        if not is_primitive(TYPE):
            self.db.record_const(value)


# ______________________________________________________________________
# Records
    
class RecordConst(AbstractConst):
    def __init__(self, db, record, count):
        self.db = db
        self.cts = db.genoo.TypeSystem(db)
        self.value = record
        self.name = 'RECORD__%d' % count

    def record_dependencies(self):
        if self.value is ootype.null(self.value._TYPE):
            return
        for f_name, (FIELD_TYPE, f_default) in self.value._TYPE._fields.iteritems():
            value = self.value._items[f_name]            
            self._record_const_if_complex(FIELD_TYPE, value)

    def create_pointer(self, gen):
        assert not self.is_null()
        gen.new(self.value._TYPE)
        self.store(gen)

    def initialize_opaque(self, gen):
        assert not self.is_null()
        self.push(gen)
        SELFTYPE = self.value._TYPE
        for f_name, (FIELD_TYPE, f_default) in self.value._TYPE._fields.iteritems():
            if FIELD_TYPE is not ootype.Void:
                gen.dup(SELFTYPE)
                #gen.load(value)
                load(self.db, FIELD_TYPE, value, gen)
                gen.set_field(SELFTYPE, f_name)
        gen.pop(SELFTYPE)

    def initialize_full(self, gen):
        pass

# ______________________________________________________________________
# Instances
    
class InstanceConst(AbstractConst):
    def __init__(self, db, obj, static_type, count):
        self.db = db
        self.value = obj
        self.cts = db.genoo.TypeSystem(db)
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

    def create_pointer(self, gen):
        assert not self.is_null()
        gen.new(self.value._TYPE)
        self.store(gen)

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

    def initialize_opaque(self, gen):
        assert not self.is_null()

        # Get a list of all the constants we'll need to initialize.
        # I am not clear on why this needs to be sorted, actually,
        # but we sort it.
        const_list = self._sorted_const_list()
        
        # Push ourself on the stack, and cast to our actual type if it
        # is not the same as our static type
        SELFTYPE = self.value._TYPE
        self.push(gen)
        if SELFTYPE is not self.static_type:
            gen.downcast(SELFTYPE)

        # Store each of our fields in the sorted order
        for FIELD_TYPE, INSTANCE, name, value in const_list:
            gen.dup(SELFTYPE)
            push_constant(self.db, FIELD_TYPE, value, gen)
            gen.set_field(INSTANCE, name)

        # Pop selves from stack when done.
        gen.pop(SELFTYPE)

    def initialize_full(self, gen):
        pass

# ______________________________________________________________________
# Class constants

class ClassConst(AbstractConst):
    def __init__(self, db, class_, count):
        self.db = db
        self.cts = db.genoo.TypeSystem(db)
        self.value = class_
        self.name = 'CLASS__%d' % count

    def record_dependencies(self):
        INSTANCE = self.value._INSTANCE
        if INSTANCE is not None:
            self.cts.lltype_to_cts(INSTANCE) # force scheduling class generation

    def is_null(self):
        return self.value._INSTANCE is None

    def is_inline(self):
        return True

    def create_pointer(self, gen):
        assert not self.is_null()
        INSTANCE = self.value._INSTANCE
        gen.getclassobject(INSTANCE)
        self.store(gen)

    def initialize_opaque(self, gen):
        pass

    def initialize_full(self, gen):
        pass
