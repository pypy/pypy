import os, pickle, sys, time, re

STAT2TITLE = {
    'stat:st_mtime':  "date",
    'exe_name':       "executable",
}

def stat2title(s):
    if s.startswith('bench:'):
        return s[6:]
    else:
        return STAT2TITLE.get(s, s)


class BenchmarkResultSet(object):
    def __init__(self, max_results=10):
        self.benchmarks = {}
        self.max_results = max_results

    def result(self, exe, allowcreate=False):
        if exe in self.benchmarks or not allowcreate:
            return self.benchmarks[exe]
        else:
            r = self.benchmarks[exe] = BenchmarkResult(exe, self.max_results)
            return r

    def txt_summary(self, stats, **kw):
        sortkey = kw.get('sortby', 'stat:st_mtime')
        lst = self.benchmarks.values()
        lst.sort(key=lambda x:x.getstat(sortkey, None), reverse=kw.get('reverse', False))
        if 'filteron' in kw:
            filteron = kw['filteron']
            lst = [r for r in lst if filteron(r)]
        relto = kw.get('relto', None)
        table = [[(stat2title(s),0) for s in stats]]
        for r in lst:
            row = []
            for stat in stats:
                if stat.startswith('bench:'):
                    benchname = stat[6:]
                    if r.getstat(stat, None) is None:
                        row.append(('XXX',-1))
                    elif relto:
                        factor = self.result(relto).getstat(stat)/r.getstat(stat)
                        if not r.asc_goods[benchname]:
                            factor = 1/factor
                        s, f = r.fmtstat(stat)
                        row.append((s + ' (%6.2fx)'%factor, f))
                    else:
                        row.append(r.fmtstat(stat))
                else:
                    row.append(r.fmtstat(stat))
            table.append(row)
        widths = [0 for thing in stats]
        for row in table:
            for i, cell in enumerate(row):
                widths[i] = max(len(cell[0]), widths[i])
        concretetable = []
        concreterow = []
        for w, cell in zip(widths, table[0]):
            concreterow.append(cell[0].center(w))
        concretetable.append(' '.join(concreterow))
        for row in table[1:]:
            concreterow = []
            for w, cell in zip(widths, row):
                concreterow.append("%*s"%(cell[1]*w, cell[0]))
            concretetable.append(' '.join(concreterow))
        return concretetable

class BenchmarkResult(object):
    IDS = {}

    def __init__(self, exe, max_results=10):
        self.max_results = max_results
        self.exe_stat = os.stat(exe)
        self.exe_name = exe
        self.codesize = os.popen('size "%s" | tail -n1 | cut -f1'%(exe,)).read().strip()
        try:
            self.pypy_rev = int(os.popen(
                exe + ' -c "import sys; print sys.pypy_version_info[-1]" 2>/dev/null').read().strip())
        except ValueError:
            self.pypy_rev = -1
        self.best_benchmarks = {}
        self.benchmarks = {}
        self.asc_goods = {}
        self.run_counts = {}

    def run_benchmark(self, benchmark, verbose=False):
        self.asc_goods[benchmark.name] = benchmark.asc_good
        if self.run_counts.get(benchmark.name, 0) > self.max_results:
            return
        if verbose:
            print 'running', benchmark.name, 'for', self.exe_name,
            sys.stdout.flush()
        new_result = benchmark.run(self.exe_name)
        if verbose:
            print new_result
        self.run_counts[benchmark.name] = self.run_counts.get(benchmark.name, 0) + 1
        if new_result == '-FAILED-':
            return
        self.benchmarks.setdefault(benchmark.name, []).append(new_result)
        if benchmark.name in self.best_benchmarks:
            old_result = self.best_benchmarks[benchmark.name]
            if benchmark.asc_good:
                new_result = max(new_result, old_result)
            else:
                new_result = min(new_result, old_result)
        self.best_benchmarks[benchmark.name] = new_result

    def getstat(self, *args):
        # oh for supplied-p!
        return_default = False
        if len(args) == 1:
            stat, = args
        else:
            stat, default = args
            return_default = True
        if hasattr(self, stat):
            return getattr(self, stat)
        if stat == 'exe':
            myid = len(BenchmarkResult.IDS)
            myid = BenchmarkResult.IDS.setdefault(self, myid)
            return '[%s]' % myid
        statkind, statdetail = stat.split(':')
        if statkind == 'stat':
            return getattr(self.exe_stat, statdetail)
        elif statkind == 'bench':
            if return_default:
                return self.best_benchmarks.get(statdetail, default)
            else:
                return self.best_benchmarks[statdetail]
        else:
            1/0

    def fmtstat(self, *args):
        stat = args[0]
        statvalue = self.getstat(*args)
        if stat == 'stat:st_mtime':
            return time.ctime(statvalue), -1
        elif stat == 'exe_name':
            return os.path.basename(statvalue), -1
        elif stat.startswith('bench:'):
            from pypy.translator.benchmark import benchmarks
            statkind, statdetail = stat.split(':', 1)
            b = benchmarks.BENCHMARKS_BY_NAME[statdetail]
            return "%8.2f%s"%(statvalue, b.units), 1
        elif stat == 'pypy_rev':
            return str(statvalue), 1
        else:
            return str(statvalue), -1

    def summary(self, stats):
        return [self.getstat(stat) for stat in stats]

    def is_stable(self, name):
        try:
            return self.n_results[name] >= self.max_results
        except:
            return False

if __name__ == '__main__':
    import autopath
    from pypy.translator.benchmark import benchmarks, result
    import cPickle
    if os.path.exists('foo.pickle'):
        s = cPickle.load(open('foo.pickle', 'rb'))
    else:
        s = result.BenchmarkResultSet(4)
    for exe in sys.argv[1:]:
        r = s.result(exe)
        r.run_benchmark(benchmarks.BENCHMARKS_BY_NAME['richards'])
        r.run_benchmark(benchmarks.BENCHMARKS_BY_NAME['pystone'])
    cPickle.dump(s, open('foo.pickle', 'wb'))
    stats = ['stat:st_mtime', 'exe_name', 'bench:richards', 'bench:pystone']
    
    for row in s.txt_summary(stats, sortby="exe_name", reverse=True, relto="/usr/local/bin/python2.4"):
        print row
