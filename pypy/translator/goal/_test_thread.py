import thread, time

running = []

def f(name, count, modulus):
    running.append(name)
    i = 0
    print "starting", name, count, modulus
    for i in xrange(count):
        if i % modulus == 0:
            print name, i
    running.remove(name)

thread.start_new_thread(f, ("eins", 10000000, 12345))
thread.start_new_thread(f, ("zwei", 10000000, 13579))
thread.start_new_thread(f, ("drei", 10000000, 14680))
thread.start_new_thread(f, ("vier", 10000000, 15725))

print "waiting for", running, "to finish"
while running:
    pass
print "finished waiting."

