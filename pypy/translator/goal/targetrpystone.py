import targetrpystonex

LOOPS = 150000

# targetrpystonex.rpystone.setslow(False)


# __________  Entry point  __________
# _____ Define and setup target _____
# _____ Run translated _____

(entry_point,
 target,
 run) = targetrpystonex.make_target_definition(LOOPS, "normal")
