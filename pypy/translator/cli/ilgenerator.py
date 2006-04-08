class CodeGenerator(object):
    def __init__(self, out, indentstep = 4, startblock = '{', endblock = '}'):
        self._out = out
        self._indent = 0
        self._bol = True # begin of line
        self._indentstep = indentstep
        self._startblock = startblock
        self._endblock = endblock

    def write(self, s, indent = 0):
        indent = self._indent + (indent * self._indentstep)
        
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

    def begin_namespace(self, name):
        self.code.writeline('.namespace ' + name)
        self.code.openblock()

    def end_namespace(self):
        self.code.closeblock()

    def begin_class(self, name, base = None):
        if base is None:
            base = '[mscorlib]System.Object'
        
        self.code.writeline('.class public %s extends %s' % (name, base))
        self.code.openblock()

    def end_class(self):
        self.code.closeblock()

    def field(self, name, type_, static = False):
        if static:
            s = 'static'
        else:
            s = ''

        self.code.writeline('.field public %s %s %s' % (s, type_, name))

    def begin_function(self, name, arglist, returntype, is_entrypoint = False, *args):
        # TODO: .maxstack

        attributes = ' '.join(args)
        arglist = ', '.join(['%s %s' % arg for arg in arglist])
        self.code.writeline('.method public %s %s %s(%s) il managed' %\
                            (attributes, returntype, name, arglist))
        
        self.code.openblock()
        if is_entrypoint:
            self.code.writeline('.entrypoint')

    def end_function(self):
        self.code.closeblock()

    def begin_try(self):
        self.code.writeline('.try')
        self.code.openblock()

    def end_try(self):
        self.code.closeblock()

    def begin_catch(self, type_):
        self.code.writeline('catch ' + type_)
        self.code.openblock()

    def end_catch(self):
        self.code.closeblock()

    def locals(self, vars):
        varlist = ', '.join(['%s %s' % var for var in vars])        
        self.code.write('.locals init (')
        self.code.write(varlist)
        self.code.writeline(')')

    def label(self, lbl):
        self.code.writeline()
        self.code.write(lbl + ':', indent=-1)
        self.code.writeline()

    def leave(self, lbl):
        self.code.writeline('leave ' + lbl)

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

    def call_method(self, meth):
        self.code.writeline('callvirt instance ' + meth)

    def new(self, class_):
        self.code.writeline('newobj ' + class_)

    def opcode(self, opcode, *args):
        self.code.write(opcode + ' ')
        self.code.writeline(' '.join(map(str, args)))
