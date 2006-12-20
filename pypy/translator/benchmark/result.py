import os, pickle

class BenchmarkResult(object):

    def __init__(self, filename, max_results=10):
        self.filename    = filename
        self.max_results = max_results
        if os.path.exists(filename):
            f = open(filename, 'r')
            self.n_results   = pickle.load(f)
            self.best_result = pickle.load(f)
            f.close()
            # any exception while loading the file is best reported
            # as a crash, instead of as a silent loss of all the
            # data :-/
        else:
            self.n_results   = {}
            self.best_result = {}

    def is_stable(self, name):
        try:
            return self.n_results[name] >= self.max_results
        except:
            return False

    def update(self, name, result, ascending_good):
        try:
            if ascending_good:
                self.best_result[name] = max(self.best_result[name], result)
            else:
                self.best_result[name] = min(self.best_result[name], result)
        except KeyError:
            self.n_results[name] = 0
            self.best_result[name] = result
        self.n_results[name] += 1

        f = open(self.filename, 'w')
        pickle.dump(self.n_results  , f)
        pickle.dump(self.best_result, f)
        f.close()

    def get_best_result(self, name):
        return self.best_result[name]

