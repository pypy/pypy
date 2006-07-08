from pypy.config.config import *
import py

def make_description():
    gcoption = ChoiceOption('name', 'GC name', ['ref', 'framework'], 'ref')
    gcdummy = BoolOption('dummy', 'dummy', default=False)
    objspaceoption = ChoiceOption('objspace', 'Object space', 
                                ['std', 'logic'], 'std')
    booloption = BoolOption('bool', 'Test boolean option')
    intoption = IntOption('int', 'Test int option')
    floatoption = FloatOption('float', 'Test float option', default=2.3)

    wantref_option = BoolOption('wantref', 'Test requires', default=False,
                                    requires=[('gc.name', 'ref')])
    
    gcgroup = OptionDescription('gc', [gcoption, gcdummy, floatoption])
    descr = OptionDescription('pypy', [gcgroup, booloption, objspaceoption,
                                       wantref_option, intoption])
    return descr
    

def test_base_config():
    descr = make_description()
    config = Config(descr, bool=False)
    
    assert config.gc.name == 'ref'
    config.gc.name = 'framework'
    assert config.gc.name == 'framework'

    assert config.objspace == 'std'
    config.objspace = 'logic'
    assert config.objspace == 'logic'
    
    assert config.gc.float == 2.3
    assert config.int == 0
    config.gc.float = 3.4
    config.int = 123
    assert config.gc.float == 3.4
    assert config.int == 123

    assert not config.wantref

    py.test.raises(ValueError, 'config.objspace = "foo"')
    py.test.raises(ValueError, 'config.gc.name = "foo"')
    py.test.raises(ValueError, 'config.gc.foo = "bar"')
    py.test.raises(ValueError, 'config.bool = 123')
    py.test.raises(ValueError, 'config.int = "hello"')
    py.test.raises(ValueError, 'config.gc.float = None')

    # test whether the gc.name is set to 'ref' when wantref is true (note that
    # the current value of gc.name is 'framework')
    config.wantref = True
    assert config.gc.name == 'ref'
    py.test.raises(ValueError, 'config.gc.name = "framework"')
    config.gc.name = "ref"

def test_annotator_folding():
    from pypy.translator.interactive import Translation

    gcoption = ChoiceOption('name', 'GC name', ['ref', 'framework'], 'ref')
    gcgroup = OptionDescription('gc', [gcoption])
    descr = OptionDescription('pypy', [gcgroup])
    config = Config(descr)
    
    def f(x):
        if config.gc.name == 'ref':
            return x + 1
        else:
            return 'foo'

    t = Translation(f)
    t.rtype([int])
    
    block = t.context.graphs[0].startblock
    assert len(block.exits[0].target.operations) == 0
    assert len(block.operations) == 1
    assert len(block.exits) == 1
    assert block.operations[0].opname == 'int_add'

    # the config should be frozen now
    py.test.raises(TypeError, 'config.gc.name = "framework"')

def test_compare_configs():
    descr = make_description()
    conf1 = Config(descr)
    conf2 = Config(descr, wantref=True)
    assert conf1 != conf2
    assert hash(conf1) != hash(conf2)
    assert conf1.getkey() != conf2.getkey()
    conf1.wantref = True
    assert conf1 == conf2
    assert hash(conf1) == hash(conf2)
    assert conf1.getkey() == conf2.getkey()

def test_loop():
    descr = make_description()
    conf = Config(descr)
    for (name, value), (gname, gvalue) in \
        zip(conf.gc, [("name", "ref"), ("dummy", False)]):
        assert name == gname
        assert value == gvalue
        
