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

    assert config._freeze_()
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
        
def test_to_optparse():
    gcoption = ChoiceOption('name', 'GC name', ['ref', 'framework'], 'ref',
                                cmdline='--gc -g')
    gcgroup = OptionDescription('gc', [gcoption])
    descr = OptionDescription('pypy', [gcgroup])
    config = Config(descr)
    
    parser = to_optparse(config, ['gc.name'])
    (options, args) = parser.parse_args(args=['--gc=framework'])
    
    assert config.gc.name == 'framework'
    
    (options, args) = parser.parse_args(args=['-g ref'])
    assert config.gc.name == 'ref'

    # XXX strange exception
    py.test.raises(SystemExit, 
                    "(options, args) = parser.parse_args(args=['-g foobar'])")

def test_to_optparse_number():
    intoption = IntOption('int', 'Int option test', cmdline='--int -i')
    floatoption = FloatOption('float', 'Float option test', 
                                cmdline='--float -f')
    descr = OptionDescription('test', [intoption, floatoption])
    config = Config(descr)

    parser = to_optparse(config, ['int', 'float'])
    (options, args) = parser.parse_args(args=['-i 2', '--float=0.1'])

    assert config.int == 2
    assert config.float == 0.1
    
    py.test.raises(SystemExit, 
        "(options, args) = parser.parse_args(args=['--int=foo', '-f bar'])")
    
def test_to_optparse_bool():
    booloption = BoolOption('bool', 'Boolean option test', default=False,
                            cmdline='--bool -b')
    descr = OptionDescription('test', [booloption])
    config = Config(descr)

    parser = to_optparse(config, ['bool'])
    (options, args) = parser.parse_args(args=['-b'])

    assert config.bool

    config = Config(descr)
    parser = to_optparse(config, ['bool'])
    (options, args) = parser.parse_args(args=[])
    assert not config.bool

    py.test.raises(SystemExit,
            "(options, args) = parser.parse_args(args=['-bfoo'])")

def test_optparse_boolgroup():
    group = OptionDescription("test", [
        BoolOption("smallint", "use tagged integers",
                   default=False),
        BoolOption("strjoin", "use strings optimized for addition",
                   default=False),
        BoolOption("strslice", "use strings optimized for slicing",
                   default=False),
        BoolOption("strdict", "use dictionaries optimized for string keys",
                   default=False),
    ], cmdline="--test")
    descr = OptionDescription("all", [group])
    config = Config(descr)
    parser = to_optparse(config, ['test'])
    (options, args) = parser.parse_args(
        args=['--test=smallint,strjoin,strdict'])
    
    assert config.test.smallint
    assert config.test.strjoin
    assert config.test.strdict

    config = Config(descr)
    parser = to_optparse(config, ['test'])
    (options, args) = parser.parse_args(
        args=['--test=smallint'])
    
    assert config.test.smallint
    assert not config.test.strjoin
    assert not config.test.strdict

def test_config_start():
    descr = make_description()
    config = Config(descr)
    parser = to_optparse(config, ["gc.*"])

    options, args = parser.parse_args(args=["--gc-name=framework", "--gc-dummy"])
    assert config.gc.name == "framework"
    assert config.gc.dummy


def test_optparse_path_options():
    gcoption = ChoiceOption('name', 'GC name', ['ref', 'framework'], 'ref')
    gcgroup = OptionDescription('gc', [gcoption])
    descr = OptionDescription('pypy', [gcgroup])
    config = Config(descr)
    
    parser = to_optparse(config, ['gc.name'])
    (options, args) = parser.parse_args(args=['--gc-name=framework'])

    assert config.gc.name == 'framework'

def test_getpaths():
    descr = make_description()
    config = Config(descr)
    
    assert config.getpaths(), ['gc.name', 'gc.dummy', 'gc.float', 'bool', 
                                'objspace', 'wantref', 'int']
    assert config.gc.getpaths(), ['name', 'dummy', 'float']
