import py
from pypy.jit.tl import interp
from pypy.jit.bytecode import *

#from pypy.rpython.l3interp import l3interp
#from pypy.rpython.l3interp import model
#from pypy.rpython.l3interp.model import Op
#from pypy.translator.c.test.test_genc import compile 
from pypy.translator.translator import TranslationContext
from pypy.annotation import policy

def translate(func, inputargs):
    t = TranslationContext()
    pol = policy.AnnotatorPolicy()
    pol.allow_someobjects = False
    t.buildannotator(policy=pol).build_types(func, inputargs)
    t.buildrtyper().specialize()

    from pypy.translator.tool.cbuild import skip_missing_compiler
    from pypy.translator.c import genc
    builder = genc.CExtModuleBuilder(t, func)
    builder.generate_source()
    skip_missing_compiler(builder.compile)
    builder.import_module()
    return builder.get_entry_point()  

# actual tests go here

def test_tl_push():
    assert interp(PUSH+chr(16)) == 16

def test_tl_pop():
    assert interp( ''.join([PUSH,chr(16), PUSH,chr(42), PUSH,chr(200), POP]) ) == 42

def test_tl_add():
    assert interp( ''.join([PUSH,chr(42), PUSH,chr(200), ADD]) ) == 242
    assert interp( ''.join([PUSH,chr(16), PUSH,chr(42), PUSH,chr(200), ADD]) ) == 242

def test_tl_error():
    py.test.raises(IndexError, interp,POP)
    py.test.raises(IndexError, interp,ADD)
    py.test.raises(IndexError, interp,''.join([PUSH,chr(200), ADD]) )

def test_tl_invalid_codetype():
    py.test.raises(TypeError, interp,[INVALID])

def test_tl_invalid_bytecode():
    py.test.raises(RuntimeError, interp,INVALID)

def test_tl_translatable():
    code = ''.join([PUSH,chr(42), PUSH,chr(200), ADD])
    fn = translate(interp, [str])
    assert interp(code) == fn(code)
