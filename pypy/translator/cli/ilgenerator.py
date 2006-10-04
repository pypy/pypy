from pypy.rpython.lltypesystem.lltype import Signed, Unsigned, Void, Bool, Float
from pypy.rpython.lltypesystem.lltype import SignedLongLong, UnsignedLongLong

TRACE_CALL = False

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
        self.code.writeline('.assembly extern pypylib {}')
        self.code.writeline('.assembly %s {}' % name)

    def close(self):
        self.out.close()

    def begin_namespace(self, name):
        self.code.writeline('.namespace ' + name)
        self.code.openblock()

    def end_namespace(self):
        self.code.closeblock()

    def write(self, s, indent=0):
        self.code.write(s, indent)

    def writeline(self, s=''):
        self.code.writeline(s)

    def openblock(self):
        self.code.openblock()

    def closeblock(self):
        self.code.closeblock()

    def begin_class(self, name, base=None, sealed=False, interfaces=(), abstract=False,
                    beforefieldinit=False, serializable=True):
        if base is None:
            base = '[mscorlib]System.Object'
        s = ''
        if abstract:
            s += 'abstract '
        if sealed:
            s += 'sealed '
        if beforefieldinit:
            s += 'beforefieldinit '
        if serializable:
            s += 'serializable '

        self.code.writeline('.class public %s %s extends %s' % (s, name, base))
        if interfaces:
            self.code.writeline('  implements %s' % ', '.join(interfaces))
        self.code.openblock()

    def end_class(self):
        self.code.closeblock()

    def field(self, name, type_, static = False):
        if static:
            s = 'static'
        else:
            s = ''

        self.code.writeline('.field public %s %s %s' % (s, type_, name))

    def begin_function(self, name, arglist, returntype, is_entrypoint = False, *args, **kwds):
        # TODO: .maxstack
        runtime = kwds.get('runtime', False)
        if runtime:
            method_type = 'runtime'
        else:
            method_type = 'il'
        attributes = ' '.join(args)
        arglist = ', '.join(['%s %s' % arg for arg in arglist])
        self.code.writeline('.method public %s %s %s(%s) %s managed' %\
                            (attributes, returntype, name, arglist, method_type))
        
        self.code.openblock()
        if is_entrypoint:
            self.code.writeline('.entrypoint')
        self.code.writeline('.maxstack 32')
        self.stderr('start %s' % name, TRACE_CALL and name!='.ctor'
                    and method_type!='runtime')

    def end_function(self):
        self.flush()
        self.code.closeblock()

    def begin_try(self):
        self.writeline('.try')
        self.openblock()

    def end_try(self):
        self.closeblock()

    def begin_catch(self, type_):
        self.writeline('catch ' + type_)
        self.openblock()

    def end_catch(self):
        self.closeblock()

    def locals(self, vars):
        varlist = ', '.join(['%s %s' % var for var in vars])        
        self.write('.locals init (')
        self.write(varlist)
        self.writeline(')')

    def label(self, lbl):
        self.writeline()
        self.write(lbl + ':', indent=-1)
        self.writeline()

    def leave(self, lbl):
        self.opcode('leave', lbl)

    def branch(self, lbl):
        self.opcode('br', lbl)

    def branch_if(self, cond, lbl):
        if cond:
            opcode = 'brtrue'
        else:
            opcode = 'brfalse'

        self.opcode(opcode, lbl)

    def call(self, func):
        self.opcode('call ', func)

    def call_method(self, meth, virtual):
        if virtual:
            self.opcode('callvirt instance', meth)
        else:
            self.opcode('call instance', meth)

    def new(self, class_):
        self.opcode('newobj', class_)

    def set_field(self, field_data ):
        self.opcode('stfld', '%s %s::%s' % field_data )

    def get_field(self, field_data):
        self.opcode('ldfld', '%s %s::%s' % field_data )
    
    def throw(self):
        self.opcode('throw')
    
    def pop(self):
        self.opcode('pop')
    
    def ret(self):
        self.opcode('ret')

    def castclass(self, cts_type):
        self.opcode('castclass', cts_type)
    
    def load_self(self):
        self.opcode('ldarg.0')
    
    def load_arg(self,v):
        self.opcode('ldarg', repr(v.name))
    
    def load_local(self,v):
        self.opcode('ldloc', repr(v.name))

    def load_const(self,type_,v):
        if type_ is Void:
            pass
        elif type_ is Bool:
            self.opcode('ldc.i4', str(int(v)))
        elif type_ is Float:
            self.opcode('ldc.r8', repr(v))
        elif type_ in (Signed, Unsigned):
            self.opcode('ldc.i4', str(v))
        elif type_ in (SignedLongLong, UnsignedLongLong):
            self.opcode('ldc.i8', str(v))

    def store_local (self, v):
        self.opcode('stloc', repr(v.name))

    def store_static_constant(self, cts_type, CONST_NAMESPACE, CONST_CLASS, name):
        self.opcode('stsfld', '%s %s.%s::%s' % (cts_type, CONST_NAMESPACE, CONST_CLASS, name))

    def load_static_constant(self, cts_type, CONST_NAMESPACE, CONST_CLASS, name):
        self.opcode('ldsfld', '%s %s.%s::%s' % (cts_type, CONST_NAMESPACE, CONST_CLASS, name))

    def load_static_field(self, cts_type, name):
        self.opcode('ldsfld', '%s %s' % (cts_type, name))

    def emit(self, opcode, *args):
        self.opcode(opcode,*args)

    def begin_link(self):
        pass

    def opcode(self, opcode, *args):
        self.code.write(opcode + ' ')
        self.code.writeline(' '.join(map(str, args)))

    def stderr(self, msg, cond=True):
        from pypy.translator.cli.support import string_literal
        if cond:
            self.call('class [mscorlib]System.IO.TextWriter class [mscorlib]System.Console::get_Error()')
            self.opcode('ldstr', string_literal(msg))
            self.call_method('void class [mscorlib]System.IO.TextWriter::WriteLine(string)', virtual=True)

    def flush(self):
        pass
