import py, time, os

#  Usage:  py.test --benchmark
#
#  This module provides an RPython class to use as follows:
#
#      bench = Benchmark()
#      while 1:
#          do_something
#          if bench.stop():
#              break

Option = py.test.Config.Option

option = py.test.Config.addoptions("pypy options", 
        Option('--benchmark', action="store_true",
               dest="benchmark", default=False,
               help="give benchmarks in tests that support it"),
    )


class Benchmark(object):
    RUN_TIME = 2.0    # repeat the benchmarked loop for two seconds

    class __metaclass__(type):
        def ENABLED(cls):
            return option.benchmark
        ENABLED = property(ENABLED)

    def __init__(self, name=''):
        self.name = name
        self.iterations = 0
        self.million_iterations = 0
        self.nextcheck = 0
        self.starttime = time.time()

    def stop(self):
        iterations = self.iterations = self.iterations + 1
        if not Benchmark.ENABLED:    # only run once if not benchmarking
            return True
        if iterations < self.nextcheck:
            return False    # continue, don't call time.time() too often
        now = time.time()
        if now - self.starttime < self.RUN_TIME:
            if iterations > 1000000:   # avoid wrap-around trouble
                self.million_iterations += 1
                self.iterations -= 1000000
                self.nextcheck = 200000
            else:
                self.nextcheck = iterations * 5 // 4
            return False    # continue looping
        self.endtime = now
        self.print_report()
        return True

    def print_report(self):
        elapsed = self.endtime - self.starttime
        iterations = float(self.million_iterations) * 1000000.0
        iterations += self.iterations
        prefix = self.name
        if prefix:
            prefix += ': '
        os.write(1, '{%s%f iterations/second}\n' % (prefix,
                                                    iterations / elapsed))
