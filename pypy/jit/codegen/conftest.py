import py, time, os

#  Usage:  py.test --brenchmark
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
option._freeze_ = lambda: True


class Benchmark(object):
    RUN_TIME = 2.0    # repeat the benchmarked loop for two seconds

    def __init__(self):
        self.starttime = time.time()
        self.iterations = 0
        self.million_iterations = 0
        self.nextcheck = 0

    def stop(self):
        iterations = self.iterations = self.iterations + 1
        if not option.benchmark:    # only run once if not benchmarking
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
        os.write(1, '{%f iterations/second}\n' % (iterations / elapsed))
