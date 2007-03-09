# Populate the database for the SQL injection demo,
# it creates a DBS directory in the current working dir.
# Requires Gadfly on the python path, and a --allworkingmodules --oldstyle
# pypy-c.
# Passwords for the demo are just the reverse of user names.

import md5
import sys, os
import random

os.mkdir("DBS")

import gadfly

conn = gadfly.gadfly()
conn.startup("db0", "DBS")

names = ['bob', 'jamie', 'david', 'monica', 'rose', 'anna']

def make_pwd(name):
    rname = list(name)
    rname.reverse()
    rname = ''.join(rname)
    return md5.new(rname).hexdigest()

pwds = [make_pwd(name) for name in names]

products = [('superglue', 10.0, 5),
            ('pink wallpaper', 25.0, 20),
            ('red wallpaper', 20.0, 20),
            ('gray wallpaper', 15.0, 20),
            ('white wallpaper', 15.0, 20),
            ('green wallpaper', 20.0, 20) ]

cursor = conn.cursor()
cursor.execute("""create table purchases (pwd varchar, user varchar,
                                          month integer, year integer,
                                          product varchar,
                                          qty integer,
                                          amount float)
               """)



ins = "insert into purchases values (?,?,?,2007,?,?,?)"
for i in range(15):
    uid = random.randrange(0, len(names))
    pwd = pwds[uid]
    name = names[uid]
    month = random.randrange(1, 13)
    product, unitprice, maxqty = random.choice(products)
    qty = random.randrange(1, maxqty)
    data = (pwd, name, month, product, qty, qty*unitprice)
    cursor.execute(ins, data)

conn.commit()

print "Done"
