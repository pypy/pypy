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
