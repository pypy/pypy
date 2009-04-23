import py, random

option = py.test.config.option

class RandomRunnerPlugin:
    def pytest_addoption(self, parser):
        group = parser.addgroup('random test options')
        group.addoption('--seed', action="store", type="int",
                        default=random.randrange(0, 10000),
                        dest="randomseed",
                        help="choose a fixed random seed")
        group.addoption('--backend', action="store",
                        default='llgraph',
                        choices=['llgraph', 'minimal', 'x86'],
                        dest="backend",
                        help="select the backend to run the functions with")
        group.addoption('--block-length', action="store", type="int",
                        default=30,
                        dest="block_length",
                        help="insert up to this many operations in each test")
        group.addoption('--n-vars', action="store", type="int",
                        default=10,
                        dest="n_vars",
                        help="supply this many randomly-valued arguments to "
                             "the function")

ConftestPlugin = RandomRunnerPlugin
