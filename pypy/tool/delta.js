

toggle_list = ['alpha', 'grandmissing', 'incompleteness'];
ALPHA = 'alpha'
GRANDMISSING = 'grandmissing'
INCOMPLETENESS = 'incompleteness'

function toggle(on) {
  for (i in toggle_list) {
     x = toggle_list[i];
     if (x!=on) {
       document.getElementById(x).style.display='none';
     }
  };
  document.getElementById(on).style.display='';
}
