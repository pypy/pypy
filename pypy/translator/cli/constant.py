"""
___________________________________________________________________________
CLI Constants

This module extends the oosupport/constant.py to be specific to the
CLI.

Currently, it is not terribly well integrated with the constant
framework.  In particular, each kind of constant overloads the
create_pointer() and initialize_data() methods with some CLI-specific
stuff, rather than implementing the more general generator interface.
This allowed me to cut and paste from the old CLI code, but should
eventually be changed.  I have included some commented routines
showing how the code should eventually look.

The CLI implementation is broken into three sections:

* Constant Generators: different generators implementing different
  techniques for loading constants (Static fields, singleton fields, etc)

* Mixins: mixins are used to add a few CLI-specific methods to each
  constant class.  Basically, any time I wanted to extend a base class
  (such as AbstractConst or DictConst), I created a mixin, and then
  mixed it in to each sub-class of that base-class.

* Subclasses: here are the CLI specific classes.  Eventually, these
  probably wouldn't need to exist at all (the JVM doesn't have any,
  for example), or could simply have empty bodies and exist to
  combine a mixin and the generic base class.  For now, though, they
  contain the create_pointer() and initialize_data() routines.
"""

from pypy.translator.oosupport.constant import \
     push_constant, WeakRefConst, StaticMethodConst, CustomDictConst, \
     ListConst, ClassConst, InstanceConst, RecordConst, DictConst, \
     BaseConstantGenerator
from pypy.translator.cli.support import string_literal
from pypy.rpython.ootypesystem import ootype
from pypy.rlib.objectmodel import CDefinedIntSymbolic
from pypy.translator.cli.comparer import EqualityComparer
from pypy.rpython.lltypesystem import lltype
from pypy.translator.cli.cts import PYPY_DICT_OF_VOID, WEAKREF

CONST_NAMESPACE = 'pypy.runtime'
CONST_CLASSNAME = 'Constants'
CONST_CLASS = '%s.%s' % (CONST_NAMESPACE, CONST_CLASSNAME)

DEBUG_CONST_INIT = False
DEBUG_CONST_INIT_VERBOSE = False
MAX_CONST_PER_STEP = 100
SERIALIZE = False

DEFINED_INT_SYMBOLICS = {'MALLOC_ZERO_FILLED':1}

def isnan(v):
        return v != v*1.0 or (v == 1.0 and v == 2.0)

def isinf(v):
    return v!=0 and (v == v*2)

# ______________________________________________________________________
# MetaVM Generator interface

class CLIGeneratorForConstants(object):

    ''' Very minimal "implementation" of oosupport.metavm.Generator
    interface.  Just what is actually used. '''
    
    def __init__(self, ilasm):
        self.ilasm = ilasm
        
    def add_section(self, text):
        return
    
    def add_comment(self, text):
        return
    
    def pop(self, OOTYPE):
        self.ilasm.pop()

# ______________________________________________________________________
# Constant Generators
#
# Different generators implementing different techniques for loading
# constants (Static fields, singleton fields, etc)

class CLIBaseConstGenerator(BaseConstantGenerator):
    """
    Base of all CLI constant generators.  It implements the oosupport
    constant generator in terms of the CLI interface.
    """

    def __init__(self, db):
        BaseConstantGenerator.__init__(self, db)
        self.cts = db.genoo.TypeSystem(db)

    def _begin_gen_constants(self, ilasm, all_constants):
        self.ilasm = ilasm
        self.begin_class()
        gen = CLIGeneratorForConstants(ilasm)
        return gen

    def _end_gen_constants(self, gen, numsteps):
        assert gen.ilasm is self.ilasm
        self.end_class()

    def begin_class(self):
        self.ilasm.begin_namespace(CONST_NAMESPACE)
        self.ilasm.begin_class(CONST_CLASSNAME, beforefieldinit=True)

    def end_class(self):
        self.ilasm.end_class()
        self.ilasm.end_namespace()

    def _declare_const(self, gen, const):
        self.ilasm.field(const.name, const.get_type(), static=True)

    def push_primitive_constant(self, gen, TYPE, value):
        ilasm = gen.ilasm
        if TYPE is ootype.Void:
            pass
        elif TYPE is ootype.Bool:
            ilasm.opcode('ldc.i4', str(int(value)))
        elif TYPE is ootype.Char or TYPE is ootype.UniChar:
            ilasm.opcode('ldc.i4', ord(value))
        elif TYPE is ootype.Float:
            if isinf(value):
                ilasm.opcode('ldc.r8', '(00 00 00 00 00 00 f0 7f)')
            elif isnan(value):
                ilasm.opcode('ldc.r8', '(00 00 00 00 00 00 f8 ff)')
            else:
                ilasm.opcode('ldc.r8', repr(value))
        elif isinstance(value, CDefinedIntSymbolic):
            ilasm.opcode('ldc.i4', DEFINED_INT_SYMBOLICS[value.expr])
        elif TYPE in (ootype.Signed, ootype.Unsigned):
            ilasm.opcode('ldc.i4', str(value))
        elif TYPE in (ootype.SignedLongLong, ootype.UnsignedLongLong):
            ilasm.opcode('ldc.i8', str(value))
        elif TYPE is ootype.String:
            if value._str is None:
                ilasm.opcode('ldnull')
            else:
                ilasm.opcode("ldstr", string_literal(value._str))
        else:
            assert False, "Unexpected constant type"

    def downcast_constant(self, gen, const, EXPECTED_TYPE):
        type = self.cts.lltype_to_cts(EXPECTED_TYPE)
        gen.ilasm.opcode('castclass', type)

class FieldConstGenerator(CLIBaseConstGenerator):
    pass

class StaticFieldConstGenerator(FieldConstGenerator):

    # _________________________________________________________________
    # OOSupport interface
    
    def push_constant(self, gen, const):
        type_ = const.get_type()
        gen.ilasm.load_static_constant(type_, CONST_NAMESPACE, CONST_CLASSNAME, const.name)
        
    def _push_constant_during_init(self, gen, const):
        full_name = '%s::%s' % (CONST_CLASS, const.name)
        gen.ilasm.opcode('ldsfld %s %s' % (const.get_type(), full_name))

    def _store_constant(self, gen, const):
        type_ = const.get_type()
        gen.ilasm.store_static_constant(type_, CONST_NAMESPACE, CONST_CLASSNAME, const.name)

    # _________________________________________________________________
    # CLI interface

    def _declare_step(self, gen, stepnum):
        gen.ilasm.begin_function(
            'step%d' % stepnum, [], 'void', False, 'static')

    def _close_step(self, gen, stepnum):
        gen.ilasm.ret()
        gen.ilasm.end_function()

    def _end_gen_constants(self, gen, numsteps):

        self.ilasm.begin_function('.cctor', [], 'void', False, 'static',
                                  'specialname', 'rtspecialname', 'default')
        self.ilasm.stderr('CONST: initialization starts', DEBUG_CONST_INIT)
        for i in range(numsteps):
            self.ilasm.stderr('CONST: step %d of %d' % (i, numsteps),
                              DEBUG_CONST_INIT)
            step_name = 'step%d' % i
            self.ilasm.call('void %s::%s()' % (CONST_CLASS, step_name))
        self.ilasm.stderr('CONST: initialization completed', DEBUG_CONST_INIT)
        self.ilasm.ret()
        self.ilasm.end_function()

        super(StaticFieldConstGenerator, self)._end_gen_constants(
            gen, numsteps)

class InstanceFieldConstGenerator(FieldConstGenerator):
    
    # _________________________________________________________________
    # OOSupport interface
    
    def push_constant(self, gen, const):
        # load the singleton instance
        gen.ilasm.opcode('ldsfld class %s %s::Singleton' % (CONST_CLASS, CONST_CLASS))
        gen.ilasm.opcode('ldfld %s %s::%s' % (const.get_type(), CONST_CLASS, const.name))

    def _push_constant_during_init(self, gen, const):
        # during initialization, we load the 'this' pointer from our
        # argument rather than the singleton argument
        gen.ilasm.opcode('ldarg.0')
        gen.ilasm.opcode('ldfld %s %s::%s' % (const.get_type(), CONST_CLASS, const.name))

    def _pre_store_constant(self, gen, const):
        gen.ilasm.opcode('ldarg.0')
        
    def _store_constant(self, gen, const):
        gen.ilasm.set_field((const.get_type(), CONST_CLASS, const.name))

    # _________________________________________________________________
    # CLI interface

    def _declare_const(self, gen, all_constants):
        gen.ilasm.field(const.name, const.get_type(), static=False)
    
    def _declare_step(self, gen, stepnum):
        gen.ilasm.begin_function('step%d' % stepnum, [], 'void', False)

    def _close_step(self, gen, stepnum):
        gen.ilasm.ret()
        gen.ilasm.end_function()

    def _end_gen_constants(self, gen, numsteps):

        ilasm = gen.ilasm

        ilasm.begin_function('.ctor', [], 'void', False, 'specialname', 'rtspecialname', 'instance')
        ilasm.opcode('ldarg.0')
        ilasm.call('instance void object::.ctor()')

        ilasm.opcode('ldarg.0')
        ilasm.opcode('stsfld class %s %s::Singleton' % (CONST_CLASS, CONST_CLASS))
        
        for i in range(numsteps):
            step_name = 'step%d' % i
            ilasm.opcode('ldarg.0')
            ilasm.call('instance void %s::%s()' % (CONST_CLASS, step_name))
        ilasm.ret()
        ilasm.end_function()

        # declare&init the Singleton containing the constants
        ilasm.field('Singleton', 'class %s' % CONST_CLASS, static=True)
        ilasm.begin_function('.cctor', [], 'void', False, 'static', 'specialname', 'rtspecialname', 'default')
        if SERIALIZE:
            self._serialize_ctor()
        else:
            self._plain_ctor()
        ilasm.end_function()

        super(StaticFieldConstGenerator, self)._end_gen_constants(gen, numsteps)

    def _plain_ctor(self):
        self.ilasm.new('instance void class %s::.ctor()' % CONST_CLASS)
        self.ilasm.pop()
        self.ilasm.ret()

    def _serialize_ctor(self):
        self.ilasm.opcode('ldstr "constants.dat"')
        self.ilasm.call('object [pypylib]pypy.runtime.Utils::Deserialize(string)')
        self.ilasm.opcode('dup')
        self.ilasm.opcode('brfalse initialize')
        self.ilasm.stderr('Constants deserialized successfully')        
        self.ilasm.opcode('stsfld class %s %s::Singleton' % (CONST_CLASS, CONST_CLASS))
        self.ilasm.ret()
        self.ilasm.label('initialize')
        self.ilasm.pop()
        self.ilasm.stderr('Cannot deserialize constants... initialize them!')
        self.ilasm.new('instance void class %s::.ctor()' % CONST_CLASS)
        self.ilasm.opcode('ldstr "constants.dat"')
        self.ilasm.call('void [pypylib]pypy.runtime.Utils::Serialize(object, string)')
        self.ilasm.ret()

class LazyConstGenerator(StaticFieldConstGenerator):
    def push_constant(self, ilasm, const):
        getter_name = '%s::%s' % (CONST_CLASS, 'get_%s' % const.name)
        ilasm.call('%s %s()' % (const.get_type(), getter_name))

    def _create_pointers(self, gen, all_constants):
        # overload to do nothing since we handle everything in lazy fashion
        pass

    def _initialize_data(self, gen, all_constants):
        # overload to do nothing since we handle everything in lazy fashion
        pass

    def _declare_const(self, gen, const):
        # Declare the field
        super(LazyConstGenerator, self)._declare_const(gen, const)

        # Create the method for accessing the field
        getter_name = 'get_%s' % const.name
        type_ = const.get_type()
        self.ilasm.begin_function(getter_name, [], type_, False, 'static')
        self.ilasm.load_static_constant(type_, CONST_NAMESPACE, CONST_CLASS, const.name)
        # if it's already initialized, just return it
        self.ilasm.opcode('dup')
        self.ilasm.opcode('brfalse', 'initialize')
        self.ilasm.opcode('ret')
        # else, initialize!
        self.ilasm.label('initialize')
        self.ilasm.opcode('pop') # discard the null value we know is on the stack
        const.instantiate(ilasm)
        self.ilasm.opcode('dup') # two dups because const.init pops the value at the end
        self.ilasm.opcode('dup')
        self.ilasm.store_static_constant(type_, CONST_NAMESPACE, CONST_CLASS, const.name)
        const.init(ilasm)
        self.ilasm.opcode('ret')
        self.ilasm.end_function()

# ______________________________________________________________________
# Mixins
#
# Mixins are used to add a few CLI-specific methods to each constant
# class.  Basically, any time I wanted to extend a base class (such as
# AbstractConst or DictConst), I created a mixin, and then mixed it in
# to each sub-class of that base-class.  Kind of awkward.

class CLIBaseConstMixin(object):
    """ A mix-in with a few extra methods the CLI backend uses """
    
    def get_type(self, include_class=True):
        """ Returns the CLI type for this constant's representation """
        return self.cts.lltype_to_cts(self.value._TYPE, include_class)
    
    def push_inline(self, gen, TYPE):
        """ Overload the oosupport version so that we use the CLI opcode
        for pushing NULL """
        assert self.is_null()
        gen.ilasm.opcode('ldnull')

class CLIDictMixin(CLIBaseConstMixin):
    # Eventually code should look more like this:
    #def _check_for_void_dict(self, gen):
    #    KEYTYPE = self.value._TYPE._KEYTYPE
    #    keytype = self.cts.lltype_to_cts(KEYTYPE)
    #    keytype_T = self.cts.lltype_to_cts(self.value._TYPE.KEYTYPE_T)
    #    VALUETYPE = self.value._TYPE._VALUETYPE
    #    valuetype = self.cts.lltype_to_cts(VALUETYPE)
    #    valuetype_T = self.cts.lltype_to_cts(self.value._TYPE.VALUETYPE_T)
    #    if VALUETYPE is ootype.Void:
    #        class_name = PYPY_DICT_OF_VOID % keytype
    #        for key in self.value._dict:
    #            gen.ilasm.opcode('dup')
    #            push_constant(self.db, KEYTYPE, key, gen)
    #            meth = 'void class %s::ll_set(%s)' % (class_name, keytype_T)
    #            gen.ilasm.call_method(meth, False)
    #        gen.ilasm.opcode('pop')
    #        return True
    #    return False
    #
    #def initialize_data(self, gen):
    #    # special case: dict of void, ignore the values
    #    if _check_for_void_dict(self, gen):
    #        return
    #    return super(CLIDictMixin, self).record_dependencies()

    def initialize_data(self, gen):
        assert not self.is_null()
        class_name = self.get_type(False)
        KEYTYPE = self.value._TYPE._KEYTYPE
        keytype = self.cts.lltype_to_cts(KEYTYPE)
        keytype_T = self.cts.lltype_to_cts(self.value._TYPE.KEYTYPE_T)

        VALUETYPE = self.value._TYPE._VALUETYPE
        valuetype = self.cts.lltype_to_cts(VALUETYPE)
        valuetype_T = self.cts.lltype_to_cts(self.value._TYPE.VALUETYPE_T)

        if KEYTYPE is ootype.Void:
            assert VALUETYPE is ootype.Void
            return

        # special case: dict of void, ignore the values
        if VALUETYPE is ootype.Void:
            class_name = PYPY_DICT_OF_VOID % keytype
            for key in self.value._dict:
                gen.ilasm.opcode('dup')
                push_constant(self.db, KEYTYPE, key, gen)
                meth = 'void class %s::ll_set(%s)' % (class_name, keytype_T)
                gen.ilasm.call_method(meth, False)
            return

        for key, value in self.value._dict.iteritems():
            gen.ilasm.opcode('dup')
            push_constant(self.db, KEYTYPE, key, gen)
            push_constant(self.db, VALUETYPE, value, gen)
            meth = 'void class [pypylib]pypy.runtime.Dict`2<%s, %s>::ll_set(%s, %s)' %\
                   (keytype, valuetype, keytype_T, valuetype_T)
            gen.ilasm.call_method(meth, False)
    

# ______________________________________________________________________
# Constant Classes
#
# Here we overload a few methods, and mix in the base classes above.
# Note that the mix-ins go first so that they overload methods where
# required.
#
# Eventually, these probably wouldn't need to exist at all (the JVM
# doesn't have any, for example), or could simply have empty bodies
# and exist to combine a mixin and the generic base class.  For now,
# though, they contain the create_pointer() and initialize_data()
# routines.  In order to get rid of them, we would need to implement
# the generator interface in the CLI.

class CLIRecordConst(CLIBaseConstMixin, RecordConst):
    # Eventually code should look more like this:
    #def create_pointer(self, gen):
    #    self.db.const_count.inc('Record')
    #    super(CLIRecordConst, self).create_pointer(gen)

    def create_pointer(self, gen):
        assert not self.is_null()
        class_name = self.get_type(False)
        gen.ilasm.new('instance void class %s::.ctor()' % class_name)
        self.db.const_count.inc('Record')

    def initialize_data(self, gen):
        assert not self.is_null()
        class_name = self.get_type(False)        
        for f_name, (FIELD_TYPE, f_default) in self.value._TYPE._fields.iteritems():
            if FIELD_TYPE is not ootype.Void:
                f_type = self.cts.lltype_to_cts(FIELD_TYPE)
                value = self.value._items[f_name]
                gen.ilasm.opcode('dup')
                push_constant(self.db, FIELD_TYPE, value, gen)
                gen.ilasm.set_field((f_type, class_name, f_name))

class CLIInstanceConst(CLIBaseConstMixin, InstanceConst):
    # Eventually code should look more like this:
    #def create_pointer(self, gen):
    #    self.db.const_count.inc('Instance')
    #    self.db.const_count.inc('Instance', INSTANCE)
    #    super(CLIInstanceConst, self).create_pointer(gen)

    def create_pointer(self, gen):
        assert not self.is_null()
        INSTANCE = self.value._TYPE
        gen.ilasm.new('instance void class %s::.ctor()' % self.db.class_name(INSTANCE))
        self.db.const_count.inc('Instance')
        self.db.const_count.inc('Instance', INSTANCE)

    def initialize_data(self, gen):
        assert not self.is_null()
        INSTANCE = self.value._TYPE
        if INSTANCE is not self.static_type:
            gen.ilasm.opcode('castclass', self.cts.lltype_to_cts(INSTANCE, include_class=False))

        # XXX, horrible hack: first collect all consts, then render
        # CustomDicts at last because their ll_set could need other
        # fields already initialized. We should really think a more
        # general way to handle such things.
        const_list = []
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
        
        for TYPE, INSTANCE, name, value in const_list:
            type_ = self.cts.lltype_to_cts(TYPE)
            gen.ilasm.opcode('dup')
            push_constant(self.db, TYPE, value, gen)
            gen.ilasm.opcode('stfld %s %s::%s' % (type_, self.db.class_name(INSTANCE), name))

class CLIClassConst(CLIBaseConstMixin, ClassConst):
    def is_inline(self):
        return True

    def push_inline(self, gen, EXPECTED_TYPE):
        if not self.is_null():
            INSTANCE = self.value._INSTANCE
            gen.ilasm.opcode('ldtoken', self.db.class_name(INSTANCE))
            gen.ilasm.call('class [mscorlib]System.Type class [mscorlib]System.Type::GetTypeFromHandle(valuetype [mscorlib]System.RuntimeTypeHandle)')
            return
        super(CLIClassConst, self).push_inline(gen, EXPECTED_TYPE)
    pass

class CLIListConst(CLIBaseConstMixin, ListConst):

    # Eventually code should look more like this:
    #def _do_not_initialize(self):
    #    # Check if it is a list of all zeroes:
    #    try:
    #        if self.value._list == [0] * len(self.value._list):
    #            return True
    #    except:
    #        pass
    #    return super(CLIListConst, self)._do_not_initialize(self)
    #
    #def create_pointer(self, gen):
    #    self.db.const_count.inc('List')
    #    self.db.const_count.inc('List', self.value._TYPE._ITEMTYPE)
    #    self.db.const_count.inc('List', len(self.value._list))
    #    super(CLIListConst, self).create_pointer(gen)        

    def create_pointer(self, gen):
        assert not self.is_null()
        class_name = self.get_type(False)
        push_constant(self.db, ootype.Signed, len(self.value._list), gen)
        gen.ilasm.new('instance void class %s::.ctor(int32)' % class_name)
        self.db.const_count.inc('List')
        self.db.const_count.inc('List', self.value._TYPE._ITEMTYPE)
        self.db.const_count.inc('List', len(self.value._list))

    def _list_of_zeroes(self):
        try:
            return self.value._list == [0] * len(self.value._list)
        except:
            return False

    def initialize_data(self, gen):
        assert not self.is_null()
        ITEMTYPE = self.value._TYPE._ITEMTYPE
        itemtype = self.cts.lltype_to_cts(ITEMTYPE)
        itemtype_T = self.cts.lltype_to_cts(self.value._TYPE.ITEMTYPE_T)

        # special case: List(Void); only resize it, don't care of the contents
        # special case: list of zeroes, don't need to initialize every item
        if ITEMTYPE is ootype.Void or self._list_of_zeroes():
            push_constant(self.db, ootype.Signed, len(self.value._list), gen)            
            meth = 'void class %s::_ll_resize(int32)' % self.get_type(False) #PYPY_LIST_OF_VOID
            gen.ilasm.call_method(meth, False)
            return True
        
        for item in self.value._list:
            gen.ilasm.opcode('dup')
            push_constant(self.db, ITEMTYPE, item, gen)
            meth = 'void class [pypylib]pypy.runtime.List`1<%s>::Add(%s)' % (itemtype, itemtype_T)
            gen.ilasm.call_method(meth, False)

class CLIDictConst(CLIDictMixin, DictConst):

    # Eventually code should look more like this:
    #def create_pointer(self, gen):
    #    self.db.const_count.inc('Dict')
    #    self.db.const_count.inc('Dict', self.value._TYPE._KEYTYPE, self.value._TYPE._VALUETYPE)
    #    super(CLIDictConst, self).create_pointer(gen)        
        
    def create_pointer(self, gen):
        assert not self.is_null()
        class_name = self.get_type(False)
        gen.ilasm.new('instance void class %s::.ctor()' % class_name)
        self.db.const_count.inc('Dict')
        self.db.const_count.inc('Dict', self.value._TYPE._KEYTYPE, self.value._TYPE._VALUETYPE)
        
class CLICustomDictConst(CLIDictMixin, CustomDictConst):
    def record_dependencies(self):
        if not self.value:
            return
        eq = self.value._dict.key_eq
        hash = self.value._dict.key_hash
        self.comparer = EqualityComparer(self.db, self.value._TYPE._KEYTYPE, eq, hash)
        self.db.pending_node(self.comparer)
        super(CLICustomDictConst, self).record_dependencies()

    def create_pointer(self, gen):
        assert not self.is_null()
        gen.ilasm.new(self.comparer.get_ctor())
        class_name = self.get_type()
        gen.ilasm.new('instance void %s::.ctor(class '
                      '[mscorlib]System.Collections.Generic.IEqualityComparer`1<!0>)'
                  % class_name)
        self.db.const_count.inc('CustomDict')
        self.db.const_count.inc('CustomDict', self.value._TYPE._KEYTYPE, self.value._TYPE._VALUETYPE)

class CLIStaticMethodConst(CLIBaseConstMixin, StaticMethodConst):
    def create_pointer(self, gen):
        assert not self.is_null()
        signature = self.cts.graph_to_signature(self.value.graph)
        gen.ilasm.opcode('ldnull')
        gen.ilasm.opcode('ldftn', signature)
        gen.ilasm.new('instance void class %s::.ctor(object, native int)' % self.delegate_type)
        self.db.const_count.inc('StaticMethod')
        
    def initialize_data(self, gen):
        return

        
class CLIWeakRefConst(CLIBaseConstMixin, WeakRefConst):
    def create_pointer(self, gen):
        gen.ilasm.opcode('ldnull')
        gen.ilasm.new('instance void %s::.ctor(object)' % self.get_type())
        self.db.const_count.inc('WeakRef')

    def get_type(self, include_class=True):
        return 'class ' + WEAKREF
    
    def initialize_data(self, gen):
        if self.value is not None:
            push_constant(self.db, self.value._TYPE, self.value, gen)
            gen.ilasm.call_method(
                'void %s::set_Target(object)' % self.get_type(), True)
            return True
    
