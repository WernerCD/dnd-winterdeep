/* Winterdeep campaign journal. Data: window.WD (data.js, built by tools/build_data.py). */
(function () {
  var D = window.WD, panel = document.getElementById('panel'), q = document.getElementById('q');
  var nohits = document.getElementById('nohits'), tabs = document.querySelectorAll('[data-tab]');
  var cur = 'overview';
  document.getElementById('asof').textContent = 'Campaign state as of ' + D.asof + '.';

  function sessionsHTML() {
    return '<p class="lede">' + D.sessions.length + ' sessions, newest first. The four latest have full write-ups from the recordings; older ones come from the players’ notes.</p>' +
      D.sessions.map(function (s) {
        return '<details class="sess' + (s.full ? ' full' : '') + (s.empty ? ' empty' : '') + '" id="s-' + s.d + '">' +
          '<summary><span class="date">' + s.day + ' ' + s.d + '</span>' + (s.full ? '<span class="pill">Full recap</span>' : '') +
          '<span class="sum">' + s.sum.replace(/<\/?p>/g, '') + '</span></summary><div class="body">' + s.body + '</div></details>';
      }).join('');
  }
  var render = {
    overview: function () { return D.world.overview; },
    now: function () { return D.overview; },
    diary: function () { return D.world.diary; },
    legend: function () { return D.world.legend; },
    sessions: sessionsHTML,
    party: function () { return D.party; },
    npcs: function () { return D.world.npcs; },
    places: function () {
      return (D.world.map ? '<figure class="map-fig"><div class="map-scroll">' + D.world.map + '</div>' +
        '<figcaption>A players’ sketch of the places in the notes, not the DM’s map and not to scale.</figcaption></figure>' : '') + D.world.places;
    },
    factions: function () { return D.world.factions; },
    items: function () { return D.world.items; },
    lore: function () { return D.world.lore; },
    timeline: function () { return D.timeline; }
  };

  function show(tab, keepQuery) {
    if (!render[tab]) tab = 'overview';
    cur = tab;
    tabs.forEach(function (b) { b.setAttribute('aria-selected', b.dataset.tab === tab ? 'true' : 'false'); });
    panel.innerHTML = render[tab]();
    if (!keepQuery) q.value = '';
    filter();
  }

  // Search: hide blocks (sessions, table rows, list items, paragraphs) that don't contain every word.
  function filter() {
    var words = q.value.toLowerCase().split(/\s+/).filter(Boolean), any = false;
    var units = panel.querySelectorAll('details.sess, tbody tr, .prose > ul > li, .prose > ol > li, .prose > p, .prose > blockquote');
    units.forEach(function (el) {
      var hit = words.every(function (w) { return el.textContent.toLowerCase().indexOf(w) >= 0; });
      el.hidden = words.length > 0 && !hit;
      if (hit) any = true;
      if (words.length && hit && el.tagName === 'DETAILS') el.open = true;
    });
    if (!words.length) panel.querySelectorAll('details.sess').forEach(function (d) { d.open = d.dataset.keep === '1'; });
    nohits.hidden = !(words.length && !any);
  }
  q.addEventListener('input', filter);

  tabs.forEach(function (b) {
    b.addEventListener('click', function () { history.replaceState(null, '', '#' + b.dataset.tab); show(b.dataset.tab); });
  });

  // Citation links (#s-YYYY-MM-DD) open that session.
  function route() {
    var h = location.hash.slice(1);
    if (/^s-\d{4}-\d{2}-\d{2}$/.test(h)) {
      show('sessions');
      var el = document.getElementById(h);
      if (el) { el.open = true; el.dataset.keep = '1'; el.scrollIntoView({ block: 'start' }); }
      return;
    }
    show(h || 'overview');
  }
  window.addEventListener('hashchange', route);
  route();
})();
