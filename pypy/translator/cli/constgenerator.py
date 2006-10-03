CONST_NAMESPACE = 'pypy.runtime'
CONST_CLASS = 'Constants'

DEBUG_CONST_INIT = False
DEBUG_CONST_INIT_VERBOSE = False
MAX_CONST_PER_STEP = 100

class StaticFieldConstGenerator:
    def __init__(self, ilasm):
        self.ilasm = ilasm
    
    def begin_class(self):
        self.ilasm.begin_namespace(CONST_NAMESPACE)
        self.ilasm.begin_class(CONST_CLASS, beforefieldinit=True)

    def end_class(self):
        self.ilasm.end_class()
        self.ilasm.end_namespace()

    def declare_const(self, const):
        self.ilasm.field(const.name, const.get_type(), static=True)

    def __new_step(self):
        if self.step > 0:
            self.__end_step() # close the previous step
        # open the new step
        self.ilasm.begin_function('step%d' % self.step, [], 'void', False, 'static')
        self.step += 1

    def __end_step(self):
        if self.step > 0:
            self.ilasm.ret()
            self.ilasm.end_function()

    def generate_consts(self, const_list):
        # this point we have collected all constant we
        # need. Instantiate&initialize them.
        self.step = 0
        ilasm = self.ilasm
        for i, const in enumerate(const_list):
            if i % MAX_CONST_PER_STEP == 0:
                self.__new_step()
            type_ = const.get_type()
            const.instantiate(ilasm)
            ilasm.store_static_constant(type_, CONST_NAMESPACE, CONST_CLASS, const.name)

        for i, const in enumerate(const_list):
            if i % MAX_CONST_PER_STEP == 0:
                self.__new_step()
            ilasm.stderr('CONST: initializing #%d' % i, DEBUG_CONST_INIT_VERBOSE)
            type_ = const.get_type()
            ilasm.load_static_constant(type_, CONST_NAMESPACE, CONST_CLASS, const.name)
            const.init(ilasm)
        self.__end_step() # close the pending step

        ilasm.begin_function('.cctor', [], 'void', False, 'static',
            'specialname', 'rtspecialname', 'default')
        ilasm.stderr('CONST: initialization starts', DEBUG_CONST_INIT)
        for i in range(self.step):
            ilasm.stderr('CONST: step %d of %d' % (i, self.step), DEBUG_CONST_INIT)
            step_name = 'step%d' % i
            ilasm.call('void %s.%s::%s()' % (CONST_NAMESPACE, CONST_CLASS, step_name))
        ilasm.stderr('CONST: initialization completed', DEBUG_CONST_INIT)
        ilasm.ret()
        ilasm.end_function()

    def load_const(cls, ilasm, const):
        full_name = '%s.%s::%s' % (CONST_NAMESPACE, CONST_CLASS, const.name)
        ilasm.opcode('ldsfld %s %s' % (const.get_type(), full_name))
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
        getter_name = '%s.%s::%s' % (CONST_NAMESPACE, CONST_CLASS, 'get_%s' % const.name)
        ilasm.call('%s %s()' % (const.get_type(), getter_name))
    load_const = classmethod(load_const)
