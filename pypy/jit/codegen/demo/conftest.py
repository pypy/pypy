import py, random

from pypy.jit.codegen.ppc import conftest

Option = py.test.config.Option

option = py.test.config.addoptions("demo options",
        Option('--seed', action="store", type="int",
               default=random.randrange(0, 10000),
               dest="randomseed",
               help="choose a fixed random seed"),
        Option('--backend', action="store",
               default='llgraph',
               choices=['llgraph', 'dump', 'ppc', 'i386', 'llvm', 'ppcfew'],
               dest="backend",
               help="select the backend to run the functions with"),
        Option('--nb-blocks', action="store", type="int",
               default=15,
               dest="nb_blocks",
               help="how many blocks to include in the random function"),
        Option('--max-block-length', action="store", type="int",
               default=20,
               dest="max_block_length",
               help="insert up to this many operations in each block"),
        Option('--n-vars', action="store", type="int",
               default=26,
               dest="n_vars",
               help="supply this many randomly-valued arguments to the function"),
        Option('--iterations', action="store", type="int",
               default=0,
               dest="iterations",
               help="run the loop of the generated function this many times - "
                    "the default is backend dependent"),
        )

very_slow_backends = {'llgraph': True,
                      'dump': True}
