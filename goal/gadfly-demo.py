import os
os.mkdir('db')

import gadfly
connection = gadfly.gadfly()
connection.startup('test', 'db')
cursor = connection.cursor()

def print_and_execute(cursor, operation):
    print operation
    cursor.execute(operation)

print_and_execute(cursor, "CREATE TABLE pypy(py varchar)")
print_and_execute(cursor, "INSERT INTO pypy(py) VALUES ('py')")
print_and_execute(cursor, "SELECT * FROM pypy")
for row in cursor.fetchall():
    print row

connection.commit()
connection.close()

import shutil
shutil.rmtree('db')
