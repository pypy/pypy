class CodeGenerator(object):
    def __init__(self, out, indentstep = 4, startblock = '{', endblock = '}'):
        self._out = out
        self._indent = 0
        self._bol = True # begin of line
        self._indentstep = indentstep
        self._startblock = startblock
        self._endblock = endblock

    def write(self, s, indent = None):
        if indent is None:
            indent = self._indent
        
        if self._bol:
            self._out.write(' ' * indent)

        self._out.write(s)
        self._bol = (s and s[-1] == '\n')

    def writeline(self, s=''):
        self.write(s)
        self.write('\n')

    def openblock(self):
        self.writeline(self._startblock)
        self._indent += self._indentstep

    def closeblock(self):
        self._indent -= self._indentstep
        self.writeline(self._endblock)


class IlasmGenerator(object):
    """
    Generate IL code by writing to a file and compiling it with ilasm
    """
    def __init__(self, outfile, name):
        self.out = outfile
        self.code = CodeGenerator(self.out)
        self.code.writeline('.assembly extern mscorlib {}')
        self.code.writeline('.assembly %s {}' % name)

    def close(self):
        self.out.close()

    def begin_function(self, name, args, returntype, is_entry_point = False):
        # TODO: .maxstack

        arglist = ', '.join(['%s %s' % arg for arg in args])

        self.code.writeline('.method static public %s %s(%s) il managed' % (returntype, name, arglist))
        self.code.openblock()
        if is_entry_point:
            self.code.writeline('.entrypoint')

    def end_function(self):
        self.code.closeblock()

    def locals(self, vars):
        varlist = ', '.join(['%s %s' % var for var in vars])        
        self.code.write('.locals init (')
        self.code.write(varlist)
        self.code.writeline(')')

    def label(self, lbl):
        self.code.writeline()
        self.code.write(lbl + ':', indent=0)
        self.code.writeline()

    def branch(self, lbl):
        self.code.writeline('br ' + lbl)

    def branch_if(self, cond, lbl):
        if cond:
            opcode = 'brtrue '
        else:
            opcode = 'brfalse '

        self.code.writeline(opcode + lbl)

    def call(self, func):
        self.code.writeline('call ' + func)

    def opcode(self, opcode, *args):
        self.code.write(opcode + ' ')
        self.code.writeline(' '.join(map(str, args)))
