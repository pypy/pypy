

toggle_list = ['alpha', 'grandmissing', 'incompleteness'];
TABLE_HIDE = "display: none"
TABLE_SHOW = "display: table"

function toggle(on) {
  for (i in toggle_list) {
     x = toggle_list[i];
     if (x!=on) {
       document.getElementById(x).setAttribute("style", TABLE_HIDE);
     }
  };
  document.getElementById(on).setAttribute("style", TABLE_SHOW);
}