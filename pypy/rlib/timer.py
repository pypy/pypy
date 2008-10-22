import time
import os


def _create_name(name, generation):
    if generation == 0:
        return name
    else:
        return "%s[%s]" % (name, str(generation))


class Timer:
    def __init__(self):
        self.reset()

    def reset(self):
        self.timings = {}
        self.levels = {}
        self.timingorder = []

    def _freeze_(self):
        self.reset()

    def start(self, timer):
        level = self.levels.setdefault(timer, -1)
        new_level = level + 1
        name = _create_name(timer, new_level)
        if name not in self.timings:
            self.timingorder.append(name)
        self.timings[name] = time.time() - self.timings.get(name, 0)
        self.levels[timer] = new_level

    def stop(self, timer):
        level = self.levels.setdefault(timer, -1)
        if level == -1:
            raise ValueError("Invalid timer name")
        if level >= 0: # timer is active
            name = _create_name(timer, level)
            self.timings[name] = time.time() - self.timings[name]
            self.levels[timer] = level - 1

    def value(self, timer):
        level = self.levels.get(timer, -1)
        if level == -1:
            result = "%fs" % self.timings[timer]
        else:
            result = "%fs (still running)" % (time.time() - self.timings[timer])
        return result

    def dump(self):
        outlist = []
        for timer in self.timingorder:
            value = self.value(timer)
            outlist.append("%s = %s" % (timer, value))
        os.write(2, "\n".join(outlist))


class DummyTimer:
    def start(self, timer):
        pass
    def stop(self, timer):
        pass
    def value(self, timer):
        return "Timing disabled"
    def dump(self):
        pass

