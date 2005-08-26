import time

def clock(space):
    return space.wrap(time.clock())

def time_(space):
    return space.wrap(time.time())

def sleep(seconds):
    time.sleep(seconds)
sleep.unwrap_spec = [float]
