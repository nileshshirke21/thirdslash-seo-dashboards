var taSortDir = {};

function showTab(name, el) {
  document.querySelectorAll('.section').forEach(function(s){s.classList.remove('active');});
  document.querySelectorAll('.nav-tab').forEach(function(t){t.classList.remove('active');});
  document.getElementById('tab-' + name).classList.add('active');
  if(el) el.classList.add('active');
  syncRankHeaders();
  if(name === 'gmb' && !_gmbDone && typeof initGmbChart === 'function') { initGmbChart(); _gmbDone = true; }
  if (typeof onShowTab === 'function') onShowTab(name);
}

function sortTable(col) {
  var tbody = document.getElementById('rankTableBody');
  if(!tbody) return;
  var rows = Array.from(tbody.querySelectorAll('tr'));
  var asc = !sortDir[col]; sortDir = {}; sortDir[col] = asc;
  rows.sort(function(a,b){
    var av=a.cells[col]?a.cells[col].innerText.trim():'';
    var bv=b.cells[col]?b.cells[col].innerText.trim():'';
    var an=parseFloat(av.replace(/[^0-9.-]/g,'')); var bn=parseFloat(bv.replace(/[^0-9.-]/g,''));
    if(!isNaN(an)&&!isNaN(bn)) return asc?an-bn:bn-an;
    if(av==='NR') return asc?1:-1; if(bv==='NR') return asc?-1:1;
    return asc?av.localeCompare(bv):bv.localeCompare(av);
  });
  rows.forEach(function(r){tbody.appendChild(r);});
  rows.forEach(function(r,i){if(r.cells[0])r.cells[0].innerText=i+1;});
}

function filterTable() {
  var q=document.getElementById('kwSearch').value.toLowerCase();
  document.getElementById('rankTableBody').querySelectorAll('tr').forEach(function(r){
    r.style.display=(r.cells[1]?r.cells[1].innerText.toLowerCase():'').includes(q)?'':'none';
  });
}

function filterLB() {
  var t=document.getElementById('lbType').value;
  var s=document.getElementById('lbStatus').value;
  var sr=1;
  document.getElementById('lbBody').querySelectorAll('tr').forEach(function(r){
    var rt=r.getAttribute('data-type')||'';
    var rs=r.getAttribute('data-status')||'';
    var show=(t==='all'||rt===t)&&(s==='all'||rs===s);
    r.style.display=show?'':'none';
    if(show&&r.cells[0])r.cells[0].innerText=sr++;
  });
}

function populateLBTypeFilter() {
  var body = document.getElementById('lbBody');
  var sel = document.getElementById('lbType');
  if (!body || !sel) return;
  var known = [
    ['Reddit', 'Reddit'],
    ['Blog Comment', 'Blog Comment'],
    ['Guest Posting', 'Guest Posting'],
    ['Directory', 'Directories']
  ];
  var present = {};
  body.querySelectorAll('tr[data-type]').forEach(function(r){ present[r.getAttribute('data-type')] = true; });
  var current = sel.value;
  var opts = '<option value="all">All Types</option>';
  known.forEach(function(pair){
    if (present[pair[0]]) opts += '<option value="' + pair[0] + '">' + pair[1] + '</option>';
  });
  sel.innerHTML = opts;
  if (sel.querySelector('option[value="' + current + '"]')) sel.value = current;
}
document.addEventListener('DOMContentLoaded', populateLBTypeFilter);

function sortLBTable(col) {
  var tbody=document.getElementById('lbBody');
  if(!tbody) return;
  var rows=Array.from(tbody.querySelectorAll('tr')).filter(function(r){return r.style.display!=='none';});
  var asc=!lbSortDir[col]; lbSortDir={}; lbSortDir[col]=asc;
  rows.sort(function(a,b){var av=a.cells[col]?a.cells[col].innerText.trim():'';var bv=b.cells[col]?b.cells[col].innerText.trim():'';return asc?av.localeCompare(bv):bv.localeCompare(av);});
  rows.forEach(function(r,i){tbody.appendChild(r);if(r.cells[0])r.cells[0].innerText=i+1;});
}

function sortTaskTable(col) {
  var tbody=document.getElementById('taskBody');
  if(!tbody) return;
  var rows=Array.from(tbody.querySelectorAll('tr'));
  var asc=!taskSortDir[col]; taskSortDir={}; taskSortDir[col]=asc;
  rows.sort(function(a,b){var av=a.cells[col]?a.cells[col].innerText.trim():'';var bv=b.cells[col]?b.cells[col].innerText.trim():'';return asc?av.localeCompare(bv):bv.localeCompare(av);});
  rows.forEach(function(r,i){tbody.appendChild(r);if(r.cells[0])r.cells[0].innerText=i+1;});
}

function syncRankHeaders() {
  document.querySelectorAll('.rank-table-wrap').forEach(function(wrap) {
    var header = wrap.querySelector(':scope > .rank-table-header');
    var table = wrap.querySelector(':scope > table');
    if (!header || !table) return;
    var w = table.scrollWidth;
    if (w > 0) header.style.minWidth = w + 'px';
  });
}

window.taSortTable = function(col) {
    var tbody = document.querySelector('.ta-table tbody');
    if (!tbody) return;
    var pairs = Array.from(tbody.querySelectorAll('tr.ta-row-issue')).map(function(row) {
      var panel = row.nextElementSibling;
      if (!panel || !panel.classList.contains('ta-url-panel')) panel = null;
      return { row: row, panel: panel };
    });
    var asc = !taSortDir[col]; taSortDir = {}; taSortDir[col] = asc;
    var prioOrder = { high: 3, medium: 2, low: 1 };
    pairs.sort(function(a, b) {
      var av, bv;
      if (col === 2) { av = prioOrder[a.row.dataset.prio] || 0; bv = prioOrder[b.row.dataset.prio] || 0; }
      else if (col === 1) { av = parseFloat((a.row.cells[1].innerText || '').replace(/[^\d.-]/g, '')) || 0; bv = parseFloat((b.row.cells[1].innerText || '').replace(/[^\d.-]/g, '')) || 0; }
      else if (col === 5) { av = (a.row.querySelector('.ta-own-sel') || {}).value || ''; bv = (b.row.querySelector('.ta-own-sel') || {}).value || ''; }
      else if (col === 6) { av = (a.row.querySelector('.ta-stat-sel') || {}).value || ''; bv = (b.row.querySelector('.ta-stat-sel') || {}).value || ''; }
      else { av = (a.row.cells[col] || {}).innerText || ''; bv = (b.row.cells[col] || {}).innerText || ''; }
      if (typeof av === 'number') return asc ? av - bv : bv - av;
      av = String(av).trim().toLowerCase(); bv = String(bv).trim().toLowerCase();
      return asc ? av.localeCompare(bv) : bv.localeCompare(av);
    });
    pairs.forEach(function(p) { tbody.appendChild(p.row); if (p.panel) tbody.appendChild(p.panel); });
  }
