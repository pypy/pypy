from pypy.config.config import *
import py

def test_base_config():
    gcoption = ChoiceOption('name', 'GC name', ['ref', 'framework'], 'ref')
    objspaceoption = ChoiceOption('objspace', 'Object space', 
                                ['std', 'logic'], 'std')
    booloption = BoolOption('bool', 'Test Boolean option')
    listoption = ListOption('list', 'Test list valued option', ['foo', 'bar'],
                                ['foo'])
    
    gcgroup = OptionDescription('gc', [gcoption])
    descr = OptionDescription('pypy', [gcgroup, booloption, objspaceoption,
                                        listoption])
    config = Config(descr, bool=False)
    
    assert config.gc.name == 'ref'
    config.gc.name = 'framework'
    assert config.gc.name == 'framework'

    assert config.objspace == 'std'
    config.objspace = 'logic'
    assert config.objspace == 'logic'
    
    assert not config.bool
    config.bool = True
    assert config.bool

    assert config.list == ['foo']
    config.list = ['bar']
    assert config.list == ['bar']

    py.test.raises(ValueError, 'config.objspace = "foo"')
    py.test.raises(ValueError, 'config.gc.name = "foo"')
    py.test.raises(ValueError, 'config.gc.foo = "bar"')
    py.test.raises(ValueError, 'config.bool = 123')
    py.test.raises(ValueError, 'config.list = ["baz"]')

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

