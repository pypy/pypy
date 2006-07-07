from pypy.config.config import *
import py

def test_base_config():
    gcoption = Option('name', 'GC name', ['ref', 'framework'], 'ref')
    objspaceoption = Option('objspace', 'Object space', 
                                ['std', 'logic'], 'std')
    gcgroup = OptionDescription('gc', [gcoption])
    descr = OptionDescription('pypy', [gcgroup, objspaceoption])
    config = Config(descr)
    
    assert config.gc.name == 'ref'
    config.gc.name = 'framework'
    assert config.gc.name == 'framework'
    assert config.objspace == 'std'
    config.objspace = 'logic'
    assert config.objspace == 'logic'
    py.test.raises(ValueError, 'config.objspace = "foo"')
    py.test.raises(ValueError, 'config.gc.name = "foo"')
    py.test.raises(ValueError, 'config.gc.foo = "bar"')

def test_annotator_folding():
    from pypy.translator.interactive import Translation

    gcoption = Option('name', 'GC name', ['ref', 'framework'], 'ref')
    objspaceoption = Option('objspace', 'Object space', 
                                ['std', 'logic'], 'std')
    gcgroup = OptionDescription('gc', [gcoption])
    descr = OptionDescription('pypy', [gcgroup, objspaceoption])
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
