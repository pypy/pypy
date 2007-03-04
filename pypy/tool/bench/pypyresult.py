import py

class ResultDB(object):
    def __init__(self):
        self.benchmarks = []

    def parsepickle(self, path):
        f = path.open("rb")
        id2numrun = py.std.pickle.load(f)
        id2bestspeed = py.std.pickle.load(f)
        f.close()
        for id in id2numrun:
            besttime = id2bestspeed[id]
            numruns = id2numrun[id]
            bench = BenchResult(id, besttime, numruns)
            self.benchmarks.append(bench)

    def getbenchmarks(self, name=None):
        l = []
        for bench in self.benchmarks: 
            if name is not None and name != bench.name:
                continue
            l.append(bench)
        return l 

class BenchResult(object):
    def __init__(self, id, besttime, numruns):
        self._id = id 
        if id.startswith("./"):
            id = id[2:]
        parts = id.split("-")
        self.name = parts.pop(-1)
        self.backend = parts[1]
        self.revision = int(parts[2])
        self.executable = "-".join(parts)
        self.besttime = besttime
        self.numruns = numruns
