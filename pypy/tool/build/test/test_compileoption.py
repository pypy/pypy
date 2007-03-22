import py
from pypy.tool.build.compileoption import combine_config
from pypy.config.config import OptionDescription, BoolOption, IntOption, \
                               ArbitraryOption, FloatOption, ChoiceOption, \
                               StrOption, to_optparse, Config

def test_combine_config():
    c1 = Config(OptionDescription('c1', 'c1',
                                  [BoolOption('foo', 'foo option',
                                              default=False)]))
    c2 = Config(OptionDescription('c2', 'c2',
                                  [BoolOption('bar', 'bar option',
                                              default=False)]))
    combined = combine_config(c1, c2, 'combined', 'combined config')
    assert isinstance(combined, Config)
    assert combined.foo == False
    assert combined.bar == False

def test_annotator_folding():
    from pypy.translator.interactive import Translation

    gcoption = ChoiceOption('name', 'GC name', ['ref', 'framework'], 'ref')
    gcgroup = OptionDescription('gc', '', [gcoption])
    descr1 = OptionDescription('pypy', '', [gcgroup])
    c1 = Config(descr1)

    foooption = IntOption('foo', 'foo', default=0)
    descr2 = OptionDescription('foo', '', [foooption])
    c2 = Config(descr2)

    config = combine_config(c1, c2, 'pypy')
    
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

    assert config._freeze_()
    # does not raise, since it does not change the attribute
    config.gc.name = "ref"
    py.test.raises(TypeError, 'config.gc.name = "framework"')

