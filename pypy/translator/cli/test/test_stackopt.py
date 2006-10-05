from pypy.translator.cli.stackopt import StackOptMixin

class FakeGenerator(object):
    def __init__(self, *args):
        self.lines = ['']
        self.opcodes = []

    def opcode(self, opcode, *args):
        self.opcodes.append((opcode, args))
        self.lines[-1] += '%s %s' % (opcode, ' '.join(args))
        self.lines.append('')

    def write(self, s, index=0):
        self.lines[-1] += s

    def writeline(self, s=''):
        self.lines[-1] += s
        self.lines.append('')

    def get_string(self):
        return '\n'.join(self.lines[:-1])

class TestStackOpt(StackOptMixin, FakeGenerator):
    pass

def test_code_generation():
    ilasm = TestStackOpt()
    ilasm.write('.method public static void foo()')
    ilasm.writeline(' {')
    ilasm.opcode('ldc.i4.0')
    ilasm.opcode('pop')
    ilasm.opcode('ret')
    ilasm.writeline('}')
    ilasm.flush()
    s = ilasm.get_string()
    assert s.strip() == """
.method public static void foo() {
ldc.i4.0 
pop 
ret 
}
""".strip()    

def test_opcodes():
    ilasm = TestStackOpt()
    ilasm.opcode('ldloc', 'x')
    ilasm.opcode('ldloc', 'y')
    ilasm.flush()
    assert ilasm.opcodes == [('ldloc', ('x',)), ('ldloc', ('y',))]

def test_renaming():
    ilasm = TestStackOpt()
    ilasm.opcode('ldloc', 'x')
    ilasm.opcode('stloc', 'x0')
    ilasm.opcode('ldloc', 'x0')
    ilasm.flush()
    assert ilasm.opcodes[0] == ('ldloc', ('x',))

def test_renaming_arg():
    ilasm = TestStackOpt()
    ilasm.opcode('ldarg', 'x')
    ilasm.opcode('stloc', 'x0')
    ilasm.opcode('ldloc', 'x0')
    ilasm.flush()
    assert ilasm.opcodes[0] == ('ldarg', ('x',))

def test_renaming_twice():
    ilasm = TestStackOpt()
    ilasm.opcode('ldarg', 'x')
    ilasm.opcode('stloc', 'x0')
    ilasm.opcode('ldloc', 'x0')
    ilasm.opcode('stloc', 'x1')
    ilasm.opcode('ldloc', 'x1')
    ilasm.flush()
    assert ilasm.opcodes[0] == ('ldarg', ('x',))

def test_not_renaming():
    ilasm = TestStackOpt()
    ilasm.opcode('ldloc', 'x')
    ilasm.opcode('stloc', 'x0')
    ilasm.opcode('ldc.i4.0')
    ilasm.opcode('stloc', 'x0')
    ilasm.opcode('nop')
    ilasm.opcode('ldloc', 'x0')
    ilasm.flush()
    assert ilasm.opcodes[-1] == ('ldloc', ('x0',))

def test_remove_tmp():
    ilasm = TestStackOpt()
    ilasm.opcode('stloc', 'x')
    ilasm.opcode('ldloc', 'x')
    ilasm.flush()
    assert not ilasm.opcodes

def test_dont_remove_tmp():
    ilasm = TestStackOpt()
    ilasm.opcode('stloc', 'x')
    ilasm.opcode('ldloc', 'x')
    ilasm.opcode('ldloc', 'x')
    ilasm.flush()
    assert ilasm.opcodes[0] == ('stloc', ('x',))

def test_ldarg0():
    ilasm = TestStackOpt()
    ilasm.opcode('ldarg.0')
    ilasm.opcode('stloc', 'x')
    ilasm.opcode('ldloc', 'x')
    ilasm.flush()
    assert ilasm.opcodes == [('ldarg.0', ())]

