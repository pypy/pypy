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

class CLIConstantGenerator(BaseConstantGenerator):
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
        if isinstance(value, ootype._view) and isinstance(value._inst, ootype._record):
            self.db.cts.lltype_to_cts(value._inst._TYPE) # record the type of the record
            return self.record_const(value._inst)
        else:
            return BaseConstantGenerator._create_complex_const(self, value)

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
                TYPE = self.value._INSTANCE
                classname = self.db.class_or_record_name(TYPE)
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
        signature = self.cts.static_meth_to_signature(self.value)
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
    
