"""
___________________________________________________________________________
CLI Constants

This module extends the oosupport/constant.py to be specific to the
CLI.  Most of the code in this file is in the constant generators, which
determine how constants are stored and loaded (static fields, lazy
initialization, etc), but some constant classes have been overloaded or
extended to allow for special handling.

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
     BaseConstantGenerator, AbstractConst, ArrayConst
from pypy.translator.cli.ilgenerator import CLIBaseGenerator
from pypy.rpython.ootypesystem import ootype
from pypy.translator.cli.comparer import EqualityComparer
from pypy.rpython.lltypesystem import lltype
from pypy.translator.cli.cts import PYPY_DICT_OF_VOID, WEAKREF

CONST_NAMESPACE = 'pypy.runtime'
CONST_CLASSNAME = 'Constants'
CONST_CLASS = '%s.%s' % (CONST_NAMESPACE, CONST_CLASSNAME)

DEBUG_CONST_INIT = False
DEBUG_CONST_INIT_VERBOSE = False
SERIALIZE = False

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
        gen = CLIBaseGenerator(self.db, ilasm)
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

    def downcast_constant(self, gen, const, EXPECTED_TYPE):
        type = self.cts.lltype_to_cts(EXPECTED_TYPE)
        gen.ilasm.opcode('castclass', type)
 
    def _get_key_for_const(self, value):
        if isinstance(value, ootype._view) and isinstance(value._inst, ootype._record):
            return value._inst
        return BaseConstantGenerator._get_key_for_const(self, value)

    def _create_complex_const(self, value):
        from pypy.translator.cli.dotnet import _fieldinfo

        if isinstance(value, _fieldinfo):
            uniq = self.db.unique()
            return CLIFieldInfoConst(self.db, value.llvalue, uniq)
        elif isinstance(value, ootype._view) and isinstance(value._inst, ootype._record):
            self.db.cts.lltype_to_cts(value._inst._TYPE) # record the type of the record
            return self.record_const(value._inst)
        else:
            return BaseConstantGenerator._create_complex_const(self, value)

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
    
    def get_type(self):
        """ Returns the CLI type for this constant's representation """
        return self.cts.lltype_to_cts(self.value._TYPE)
    
    def push_inline(self, gen, TYPE):
        """ Overload the oosupport version so that we use the CLI opcode
        for pushing NULL """
        assert self.is_null()
        gen.ilasm.opcode('ldnull')

class CLIDictMixin(CLIBaseConstMixin):
    def _check_for_void_dict(self, gen):
        KEYTYPE = self.value._TYPE._KEYTYPE
        keytype = self.cts.lltype_to_cts(KEYTYPE)
        keytype_T = self.cts.lltype_to_cts(self.value._TYPE.KEYTYPE_T)
        VALUETYPE = self.value._TYPE._VALUETYPE
        valuetype = self.cts.lltype_to_cts(VALUETYPE)
        valuetype_T = self.cts.lltype_to_cts(self.value._TYPE.VALUETYPE_T)
        if VALUETYPE is ootype.Void:
            gen.add_comment('  CLI Dictionary w/ void value')
            class_name = PYPY_DICT_OF_VOID % keytype
            for key in self.value._dict:
                gen.ilasm.opcode('dup')
                push_constant(self.db, KEYTYPE, key, gen)
                meth = 'void class %s::ll_set(%s)' % (class_name, keytype_T)
                gen.ilasm.call_method(meth, False)
            return True
        return False
    
    def initialize_data(self, constgen, gen):
        # special case: dict of void, ignore the values
        if self._check_for_void_dict(gen):
            return 
        return super(CLIDictMixin, self).initialize_data(constgen, gen)

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
    def create_pointer(self, gen):
        self.db.const_count.inc('Record')
        super(CLIRecordConst, self).create_pointer(gen)

class CLIInstanceConst(CLIBaseConstMixin, InstanceConst):
    def create_pointer(self, gen):
        self.db.const_count.inc('Instance')
        self.db.const_count.inc('Instance', self.OOTYPE())
        super(CLIInstanceConst, self).create_pointer(gen)


class CLIClassConst(CLIBaseConstMixin, ClassConst):
    def is_inline(self):
        return True

    def push_inline(self, gen, EXPECTED_TYPE):
        if not self.is_null():
            if hasattr(self.value, '_FUNC'):
                FUNC = self.value._FUNC
                classname = self.db.record_delegate(FUNC)
            else:
                INSTANCE = self.value._INSTANCE
                classname = self.db.class_name(INSTANCE)
            gen.ilasm.opcode('ldtoken', classname)
            gen.ilasm.call('class [mscorlib]System.Type class [mscorlib]System.Type::GetTypeFromHandle(valuetype [mscorlib]System.RuntimeTypeHandle)')
            return
        super(CLIClassConst, self).push_inline(gen, EXPECTED_TYPE)

class CLIListConst(CLIBaseConstMixin, ListConst):

    def _do_not_initialize(self):
        # Check if it is a list of all zeroes:
        try:
            if self.value._list == [0] * len(self.value._list):
                return True
        except:
            pass
        return super(CLIListConst, self)._do_not_initialize()
    
    def create_pointer(self, gen):
        self.db.const_count.inc('List')
        self.db.const_count.inc('List', self.value._TYPE.ITEM)
        self.db.const_count.inc('List', len(self.value._list))
        super(CLIListConst, self).create_pointer(gen)


class CLIArrayConst(CLIBaseConstMixin, ArrayConst):

    def _do_not_initialize(self):
        # Check if it is an array of all zeroes:
        try:
            if self.value._list == [0] * len(self.value._list):
                return True
        except:
            pass
        return super(CLIArrayConst, self)._do_not_initialize()

    def _setitem(self, SELFTYPE, gen):
        gen.array_setitem(SELFTYPE)


class CLIDictConst(CLIDictMixin, DictConst):
    def create_pointer(self, gen):
        self.db.const_count.inc('Dict')
        self.db.const_count.inc('Dict', self.value._TYPE._KEYTYPE, self.value._TYPE._VALUETYPE)
        super(CLIDictConst, self).create_pointer(gen)        
        
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
        
    def initialize_data(self, constgen, gen):
        return

        
class CLIWeakRefConst(CLIBaseConstMixin, WeakRefConst):
    def create_pointer(self, gen):
        gen.ilasm.new('instance void %s::.ctor()' % self.get_type())
        self.db.const_count.inc('WeakRef')

    def get_type(self, include_class=True):
        return 'class ' + WEAKREF
    
    def initialize_data(self, constgen, gen):
        if self.value is not None:
            push_constant(self.db, self.value._TYPE, self.value, gen)
            gen.ilasm.call_method('void %s::ll_set(object)' % self.get_type(), True)
            return True
    

class CLIFieldInfoConst(AbstractConst):
    def __init__(self, db, llvalue, count):
        AbstractConst.__init__(self, db, llvalue, count)
        self.name = 'FieldInfo__%d' % count
    
    def create_pointer(self, generator):
        constgen = generator.db.constant_generator
        const = constgen.record_const(self.value)
        generator.ilasm.opcode('ldtoken', CONST_CLASS)
        generator.ilasm.call('class [mscorlib]System.Type class [mscorlib]System.Type::GetTypeFromHandle(valuetype [mscorlib]System.RuntimeTypeHandle)')
        generator.ilasm.opcode('ldstr', '"%s"' % const.name)
        generator.ilasm.call_method('class [mscorlib]System.Reflection.FieldInfo class [mscorlib]System.Type::GetField(string)', virtual=True)

    def get_type(self):
        from pypy.translator.cli.cts import CliClassType
        return CliClassType('mscorlib', 'System.Reflection.FieldInfo')

    def initialize_data(self, constgen, gen):
        pass

    def record_dependencies(self):
        self.db.constant_generator.record_const(self.value)
