<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html>
<head>
    <meta content="text/html; charset=UTF-8" http-equiv="content-type"/>
    <title>Bub'n'bros</title>
    <script language="javascript" src="/tgtest${std.tg_js}/MochiKit.js"/>
    <script language="javascript" src="${std.tg_js}/MochiKit.js"/>
    <script type="text/javascript" src="js_basic.js"/>
    <script type="text/javascript">
    function call_fun () {
        result = undefined;
        exc = undefined;
        try {
            result = ${onload}();
        } catch ( e ) {
            exc = e;
            xml = new XMLHttpRequest();
            xml.open('GET', '/send_result?result=0;exc='+exc, true);
            xml.send(null);
        }
    }
    </script>
</head>
<body onload="${onload}()">
  <p>This is a test!</p><br/>
  <p>Code:</p><br/>
  <pre>
    ${code}
  </pre>
</body>
</html>
