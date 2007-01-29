import py, random

Option = py.test.config.Option

option = py.test.config.addoptions("demo options",
        Option('--seed', action="store", type="int",
               default=random.randrange(0, 10000),
               dest="randomseed",
               help="choose a fixed random seed"),
        Option('--backend', action="store",
               default='llgraph',
               choices=['llgraph', 'dump', 'ppc', 'i386', 'llvm'],
               dest="backend",
               help="select the backend to run the functions with"),
        )
