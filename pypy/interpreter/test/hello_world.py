
def main(aStr):
    print len(aStr)

map(main, ["hello world", "good bye"])
apply(main, ("apply works, too",))