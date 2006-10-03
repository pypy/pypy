CONST_NAMESPACE = 'pypy.runtime'
CONST_CLASSNAME = 'Constants'
CONST_CLASS = '%s.%s' % (CONST_NAMESPACE, CONST_CLASSNAME)

DEBUG_CONST_INIT = False
DEBUG_CONST_INIT_VERBOSE = False
MAX_CONST_PER_STEP = 100
SERIALIZE = False

class BaseConstGenerator:
    def __init__(self, ilasm):
        self.ilasm = ilasm
    
    def begin_class(self):
        self.ilasm.begin_namespace(CONST_NAMESPACE)
        self.ilasm.begin_class(CONST_CLASSNAME, beforefieldinit=True)

    def end_class(self):
        self.ilasm.end_class()
        self.ilasm.end_namespace()

    def declare_const(self, const):
        self.ilasm.field(const.name, const.get_type(), static=True)

class FieldConstGenerator(BaseConstGenerator):
    def _new_step(self):
        if self.step > 0:
            self._end_step() # close the previous step
        self._declare_step()  # open the next step
        self.step += 1
        
    def _end_step(self):
        if self.step > 0:
            self._close_step()

    def _declare_step(self):
        raise NotImplementedError

    def _close_step(self):
        raise NotImplementedError


class StaticFieldConstGenerator(FieldConstGenerator):

    def _declare_step(self):
        self.ilasm.begin_function('step%d' % self.step, [], 'void', False, 'static')

    def _close_step(self):
        self.ilasm.ret()
        self.ilasm.end_function()

    def generate_consts(self, const_list):
        # this point we have collected all constant we
        # need. Instantiate&initialize them.
        self.step = 0
        ilasm = self.ilasm
        for i, const in enumerate(const_list):
            if i % MAX_CONST_PER_STEP == 0:
                self._new_step()
            type_ = const.get_type()
            const.instantiate(ilasm)
            ilasm.store_static_constant(type_, CONST_NAMESPACE, CONST_CLASSNAME, const.name)

        for i, const in enumerate(const_list):
            if i % MAX_CONST_PER_STEP == 0:
                self._new_step()
            ilasm.stderr('CONST: initializing #%d' % i, DEBUG_CONST_INIT_VERBOSE)
            type_ = const.get_type()
            ilasm.load_static_constant(type_, CONST_NAMESPACE, CONST_CLASSNAME, const.name)
            const.init(ilasm)
        self._end_step() # close the pending step

        ilasm.begin_function('.cctor', [], 'void', False, 'static',
            'specialname', 'rtspecialname', 'default')
        ilasm.stderr('CONST: initialization starts', DEBUG_CONST_INIT)
        for i in range(self.step):
            ilasm.stderr('CONST: step %d of %d' % (i, self.step), DEBUG_CONST_INIT)
            step_name = 'step%d' % i
            ilasm.call('void %s::%s()' % (CONST_CLASS, step_name))
        ilasm.stderr('CONST: initialization completed', DEBUG_CONST_INIT)
        ilasm.ret()
        ilasm.end_function()

    def load_const(cls, ilasm, const):
        full_name = '%s::%s' % (CONST_CLASS, const.name)
        ilasm.opcode('ldsfld %s %s' % (const.get_type(), full_name))
    load_const = classmethod(load_const)


class InstanceFieldConstGenerator(FieldConstGenerator):
    
    def declare_const(self, const):
        self.ilasm.field(const.name, const.get_type(), static=False)
    
    def _declare_step(self):
        self.ilasm.begin_function('step%d' % self.step, [], 'void', False)

    def _close_step(self):
        self.ilasm.ret()
        self.ilasm.end_function()

    def generate_consts(self, const_list):
        # this point we have collected all constant we
        # need. Instantiate&initialize them.
        self.step = 0
        ilasm = self.ilasm
        for i, const in enumerate(const_list):
            if i % MAX_CONST_PER_STEP == 0:
                self._new_step()
            ilasm.opcode('ldarg.0')
            const.instantiate(ilasm)
            ilasm.set_field((const.get_type(), CONST_CLASS, const.name))

        for i, const in enumerate(const_list):
            if i % MAX_CONST_PER_STEP == 0:
                self._new_step()
            ilasm.stderr('CONST: initializing #%d' % i, DEBUG_CONST_INIT_VERBOSE)
            ilasm.opcode('ldarg.0')
            ilasm.get_field((const.get_type(), CONST_CLASS, const.name))
            const.init(ilasm)
        self._end_step() # close the pending step

        ilasm.begin_function('.ctor', [], 'void', False, 'specialname', 'rtspecialname', 'instance')
        ilasm.opcode('ldarg.0')
        ilasm.call('instance void object::.ctor()')

        ilasm.opcode('ldarg.0')
        ilasm.opcode('stsfld class %s %s::Singleton' % (CONST_CLASS, CONST_CLASS))
        
        for i in range(self.step):
            step_name = 'step%d' % i
            ilasm.opcode('ldarg.0')
            ilasm.call('instance void %s::%s()' % (CONST_CLASS, step_name))
        ilasm.ret()
        ilasm.end_function()

        # declare&init the Singleton containing the constants
        self.ilasm.field('Singleton', 'class %s' % CONST_CLASS, static=True)
        self.ilasm.begin_function('.cctor', [], 'void', False, 'static', 'specialname', 'rtspecialname', 'default')
        if SERIALIZE:
            self._serialize_ctor()
        else:
            self._plain_ctor()
        self.ilasm.end_function()

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

    def load_const(cls, ilasm, const):
        ilasm.opcode('ldsfld class %s %s::Singleton' % (CONST_CLASS, CONST_CLASS))
        ilasm.opcode('ldfld %s %s::%s' % (const.get_type(), CONST_CLASS, const.name))
    load_const = classmethod(load_const)


class LazyConstGenerator(StaticFieldConstGenerator):
    def generate_consts(self, const_list):
        ilasm = self.ilasm
        for const in const_list:
            getter_name = 'get_%s' % const.name
            type_ = const.get_type()
            ilasm.begin_function(getter_name, [], type_, False, 'static')
            ilasm.load_static_constant(type_, CONST_NAMESPACE, CONST_CLASS, const.name)
            # if it's already initialized, just return it
            ilasm.opcode('dup')
            ilasm.opcode('brfalse', 'initialize')
            ilasm.opcode('ret')
            # else, initialize!
            ilasm.label('initialize')
            ilasm.opcode('pop') # discard the null value we know is on the stack
            const.instantiate(ilasm)
            ilasm.opcode('dup') # two dups because const.init pops the value at the end
            ilasm.opcode('dup')
            ilasm.store_static_constant(type_, CONST_NAMESPACE, CONST_CLASS, const.name)
            const.init(ilasm)
            ilasm.opcode('ret')
            ilasm.end_function()

    def load_const(cls, ilasm, const):
        getter_name = '%s::%s' % (CONST_CLASS, 'get_%s' % const.name)
        ilasm.call('%s %s()' % (const.get_type(), getter_name))
    load_const = classmethod(load_const)
