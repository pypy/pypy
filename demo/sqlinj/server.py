"""SQL injection example, needs gadfly
  (sf.net/projects/gadfly) to be on the python path.

   Use populate.py to create the example db.

   Passwords are the reverse of user names :).

   Query is the number of a calendar month, purchases
   for the user with the password since including that month
   are shown.

   Works with an --allworkingmodules --oldstyle pypy-c .
"""

import sys

import gadfly

import BaseHTTPServer
import cgi
import md5

page="""
<html>
<head>
<title>DEMO</title>
</head>
<body>
<form method="get" action="/">
<label for="pwd">Passwd</label>
<input name="pwd" type="text" size="10"></input><br />
<label for="query">Query</label>
<input name="query" type="text" size="20"></input><br />
<input type="submit">
</form>

<div>
%s
</div>
</body>
</html>
"""

table = """
<table>
<th>customer</th>
<th>month</th>
<th>year</th>
<th>prod.</th>
<th>qty</th>
<th>amount</th>
%s
</table>
"""

row = "<tr>"+"<td>%s</td>"*6 +"</tr>"

def do_query(query):
    conn = gadfly.gadfly("db0", "DBS")
    cursor = conn.cursor()
    pwd = md5.new(query['pwd'][0]).hexdigest()
    q = query['query'][0]

    sel = ("""select user,month,year,product,qty,amount from purchases
                      where pwd='%s' and month>=%s
                   """ % (pwd, q))
    cursor.execute(sel)
    rows = []
    for x in cursor.fetchall():
        rows.append(row % x)
    results = table % ('\n'.join(rows))
    
    conn.close()
    return results
    
    

class RequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    
    def do_GET(self):
        self.send_response(200, "OK")
        self.end_headers()
        parts = self.path.split('?')
        if len(parts) > 1:
            _, query = parts
            query = cgi.parse_qs(query, strict_parsing=True)
        else:
            query = None

        if query is not None:
            results = do_query(query)
        else:
            results = "no query"

        self.wfile.write(page % results)



if __name__ == '__main__':
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    else:
        port = 8000
    
    server_address = ('', port)
    httpd = BaseHTTPServer.HTTPServer(server_address, RequestHandler)
    httpd.serve_forever()
