/* Site script, served at /assets/app.js (deferred). Vanilla JS, no build step.

   1. Preferences: theme and length order (saved in localStorage; applied early by prefs.js)
   2. Maps: .mapfig[data-map] figures. Data is fetched from data-src (same origin);
      lines are drawn on a plain graticule first, then on an OpenFreeMap base map
      when MapLibre and WebGL are available.
   3. Trail finder (home page): search, filters, sort, URL query state, map/list highlight
   4. Copy-credit buttons

   Every page works without this script: the list holds every trail and each map
   frame keeps its size, border and caption. */
(function () {
  'use strict';

  var root = document.documentElement;
  var darkQuery = window.matchMedia('(prefers-color-scheme: dark)');
  var KM_PER_MI = 1.609344;
  var fmt = new Intl.NumberFormat('en-US');

  /* 1. Preferences ----------------------------------------------------------- */

  function readPref(key) {
    try { return localStorage.getItem(key); } catch (e) { return null; }
  }
  function writePref(key, value) {
    try {
      if (value) localStorage.setItem(key, value);
      else localStorage.removeItem(key);
    } catch (e) { /* storage blocked: the choice lasts for this page only */ }
  }

  function isDark() {
    var t = root.dataset.theme;
    return t ? t === 'dark' : darkQuery.matches;
  }
  function milesFirst() { return root.dataset.units !== 'km'; }

  function setTheme(value) {
    if (value === 'light' || value === 'dark') root.dataset.theme = value;
    else delete root.dataset.theme;
    writePref('lh-theme', value === 'light' || value === 'dark' ? value : null);
    document.dispatchEvent(new Event('olt:theme'));
  }

  function setUnits(value) {
    if (value === 'km') root.dataset.units = 'km';
    else delete root.dataset.units;
    writePref('lh-units', value === 'km' ? 'km' : null);
    syncRadios('input[name="units"], input[name="units-list"]', value === 'km' ? 'km' : 'mi');
    document.dispatchEvent(new Event('olt:units'));
  }

  function syncRadios(selector, value) {
    document.querySelectorAll(selector).forEach(function (input) { input.checked = input.value === value; });
  }

  syncRadios('input[name="theme"]', readPref('lh-theme') || 'auto');
  syncRadios('input[name="units"], input[name="units-list"]', milesFirst() ? 'mi' : 'km');
  document.querySelectorAll('input[name="theme"]').forEach(function (input) {
    input.addEventListener('change', function () { if (input.checked) setTheme(input.value); });
  });
  document.querySelectorAll('input[name="units"], input[name="units-list"]').forEach(function (input) {
    input.addEventListener('change', function () { if (input.checked) setUnits(input.value); });
  });
  darkQuery.addEventListener('change', function () {
    if (!root.dataset.theme) document.dispatchEvent(new Event('olt:theme'));
  });

  /* A length in both units, in the reader's order: "800 mi (1,287 km)". */
  function lengthText(km) {
    var k = fmt.format(km) + ' km';
    var m = fmt.format(Math.round(km / KM_PER_MI)) + ' mi';
    return milesFirst() ? m + ' (' + k + ')' : k + ' (' + m + ')';
  }

  /* Resolve a colour token (light-dark() included) to an rgb() string. */
  var probe = null;
  function token(name) {
    if (!probe) {
      probe = document.createElement('span');
      probe.hidden = true;
      document.body.appendChild(probe);
    }
    probe.style.color = 'var(' + name + ')';
    return getComputedStyle(probe).color;
  }

  /* 2. Maps ------------------------------------------------------------------- */

  var STYLE_URL = 'https://tiles.openfreemap.org/styles/positron';

  function linesOf(feature) {
    var g = feature.geometry || {};
    if (g.type === 'LineString') return [g.coordinates];
    return g.type === 'MultiLineString' ? g.coordinates : [];
  }

  function pointsOf(feature) {
    var g = feature.geometry || {};
    if (g.type === 'Point') return [g.coordinates];
    return g.type === 'MultiPoint' ? g.coordinates : [];
  }

  function allCoords(feature) {
    var out = [];
    linesOf(feature).forEach(function (line) { line.forEach(function (p) { out.push(p); }); });
    pointsOf(feature).forEach(function (p) { out.push(p); });
    return out;
  }

  function bboxOf(fc) {
    if (fc.bbox && fc.bbox.length === 4) return fc.bbox;
    var b = [180, 90, -180, -90];
    fc.features.forEach(function (f) {
      allCoords(f).forEach(function (p) {
        if (p[0] < b[0]) b[0] = p[0];
        if (p[1] < b[1]) b[1] = p[1];
        if (p[0] > b[2]) b[2] = p[0];
        if (p[1] > b[3]) b[3] = p[1];
      });
    });
    return b;
  }

  function bboxOfFeature(feature) {
    var b = [180, 90, -180, -90];
    var seen = false;
    allCoords(feature).forEach(function (p) {
      seen = true;
      if (p[0] < b[0]) b[0] = p[0];
      if (p[1] < b[1]) b[1] = p[1];
      if (p[0] > b[2]) b[2] = p[0];
      if (p[1] > b[3]) b[3] = p[1];
    });
    return seen ? b : null;
  }

  /* A single sketch point has no span; give it about a county of ground. */
  function ensureSpan(bbox) {
    var b = bbox.slice();
    if (b[2] - b[0] < 0.02) { var cx = (b[0] + b[2]) / 2; b[0] = cx - 0.25; b[2] = cx + 0.25; }
    if (b[3] - b[1] < 0.02) { var cy = (b[1] + b[3]) / 2; b[1] = cy - 0.18; b[3] = cy + 0.18; }
    return b;
  }

  function mercY(lat) { return Math.log(Math.tan(Math.PI / 4 + (lat * Math.PI) / 360)); }
  function invMercY(y) { return (360 / Math.PI) * Math.atan(Math.exp(y)) - 90; }

  function dms(value, pos, neg) {
    var a = Math.abs(value);
    var d = Math.floor(a);
    var m = Math.round((a - d) * 60);
    if (m === 60) { d += 1; m = 0; }
    return d + '°' + (m < 10 ? '0' : '') + m + '′' + (value >= 0 ? pos : neg);
  }

  /* Lines on a plain graticule (Web Mercator), no tiles. Returns the drawn extent. */
  function drawFallback(host, fc, bbox, routeMain) {
    bbox = ensureSpan(bbox);
    var rect = host.getBoundingClientRect();
    var W = Math.max(Math.round(rect.width), 280);
    var H = Math.max(Math.round(rect.height), 180);
    var pad = 28;
    var rad = Math.PI / 180;
    var cx = (bbox[0] + bbox[2]) / 2;
    var y0 = mercY(bbox[1]);
    var y1 = mercY(bbox[3]);
    var cy = (y0 + y1) / 2;
    var k = Math.min((W - 2 * pad) / Math.max((bbox[2] - bbox[0]) * rad, 1e-6),
                     (H - 2 * pad) / Math.max(y1 - y0, 1e-6));
    function x(lon) { return W / 2 + (lon - cx) * rad * k; }
    function y(lat) { return H / 2 - (mercY(lat) - cy) * k; }
    var ext = { w: cx - W / 2 / k / rad, e: cx + W / 2 / k / rad, n: invMercY(cy + H / 2 / k), s: invMercY(cy - H / 2 / k) };

    var span = Math.max(ext.e - ext.w, ext.n - ext.s);
    var step = [0.25, 0.5, 1, 2, 5, 10, 15].filter(function (s) { return span / s <= 9; })[0] || 20;
    var grat = '';
    for (var lon = Math.ceil(ext.w / step) * step; lon <= ext.e; lon += step) grat += 'M' + x(lon).toFixed(1) + ' 0V' + H;
    for (var lat = Math.ceil(ext.s / step) * step; lat <= ext.n; lat += step) grat += 'M0 ' + y(lat).toFixed(1) + 'H' + W;

    var ns = 'http://www.w3.org/2000/svg';
    var svg = document.createElementNS(ns, 'svg');
    svg.setAttribute('viewBox', '0 0 ' + W + ' ' + H);
    svg.setAttribute('preserveAspectRatio', 'xMidYMid slice');
    svg.setAttribute('aria-hidden', 'true');
    svg.setAttribute('focusable', 'false');
    function path(cls, d, id) {
      var p = document.createElementNS(ns, 'path');
      p.setAttribute('class', cls);
      p.setAttribute('d', d);
      if (id) p.setAttribute('data-id', id);
      svg.appendChild(p);
    }
    path('fallback__grat', grat);
    var drawn = fc.features.map(function (f) {
      var d = linesOf(f).map(function (line) {
        return 'M' + line.map(function (p) { return x(p[0]).toFixed(1) + ' ' + y(p[1]).toFixed(1); }).join('L');
      }).join('');
      var p = f.properties || {};
      var isRoute = p.kind === 'route' || (routeMain && (p.role === 'main' || p.sketch));
      var mod = p.sketch ? ' fallback__line--sketch' + (isRoute ? ' fallback__line--sketch-route' : '')
        : p.role === 'alternate' ? ' fallback__line--alternate'
        : isRoute ? ' fallback__line--route' : '';
      return { d: d, mod: mod, id: p.id || '', sketch: !!p.sketch };
    }).filter(function (l) { return l.d; });
    drawn.filter(function (l) { return !l.sketch; }).forEach(function (l) { path('fallback__casing', l.d, l.id); });
    drawn.forEach(function (l) { path('fallback__line' + l.mod, l.d, l.id); });
    fc.features.forEach(function (f) {
      var p = f.properties || {};
      var ringCls = 'fallback__ring' + ((p.kind === 'route' || routeMain) ? ' fallback__ring--route' : '');
      pointsOf(f).forEach(function (pt) {
        var c = document.createElementNS(ns, 'circle');
        c.setAttribute('class', ringCls);
        c.setAttribute('cx', x(pt[0]).toFixed(1));
        c.setAttribute('cy', y(pt[1]).toFixed(1));
        c.setAttribute('r', '4');
        if (p.id) c.setAttribute('data-id', p.id);
        svg.appendChild(c);
      });
    });
    host.replaceChildren(svg);
    return ext;
  }

  function webglAvailable() {
    try {
      var c = document.createElement('canvas');
      return !!(c.getContext('webgl2') || c.getContext('webgl'));
    } catch (e) { return false; }
  }

  /* Night version of the Positron base map: invert lightness, keep hue. */
  var COLOR_PROPS = ['background-color', 'fill-color', 'fill-outline-color', 'line-color', 'text-color', 'text-halo-color'];
  var ctx2d = null;

  function parseColor(str) {
    if (typeof str !== 'string' || !/^(#|rgb|hsl)/i.test(str.trim())) return null;
    if (!ctx2d) ctx2d = document.createElement('canvas').getContext('2d');
    ctx2d.fillStyle = '#000';
    ctx2d.fillStyle = str;
    var v = ctx2d.fillStyle;
    var m;
    if (v.charAt(0) === '#') return [parseInt(v.slice(1, 3), 16), parseInt(v.slice(3, 5), 16), parseInt(v.slice(5, 7), 16), 1];
    if ((m = v.match(/rgba?\(([^)]+)\)/))) {
      var parts = m[1].split(',').map(Number);
      return [parts[0], parts[1], parts[2], parts.length > 3 ? parts[3] : 1];
    }
    return null;
  }

  function toHsl(r, g, b) {
    r /= 255; g /= 255; b /= 255;
    var max = Math.max(r, g, b), min = Math.min(r, g, b), l = (max + min) / 2, h = 0, s = 0;
    if (max !== min) {
      var d = max - min;
      s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
      h = max === r ? (g - b) / d + (g < b ? 6 : 0) : max === g ? (b - r) / d + 2 : (r - g) / d + 4;
      h *= 60;
    }
    return [h, s, l];
  }

  function nightColor(value, prop, layerId) {
    if (Array.isArray(value)) return value.map(function (v) { return nightColor(v, prop, layerId); });
    if (value && typeof value === 'object') {
      var out = {};
      Object.keys(value).forEach(function (k) { out[k] = nightColor(value[k], prop, layerId); });
      return out;
    }
    var c = parseColor(value);
    if (!c) return value;
    if (layerId === 'water') return 'hsla(205, 22%, 6%, ' + c[3] + ')';
    var hsl = toHsl(c[0], c[1], c[2]);
    var l = prop === 'text-color' ? 0.92 - hsl[2] * 0.55 : 0.07 + (1 - hsl[2]) * 0.55;
    return 'hsla(' + hsl[0].toFixed(0) + ', ' + (hsl[1] * 80).toFixed(0) + '%, ' + (l * 100).toFixed(1) + '%, ' + c[3] + ')';
  }

  function tintBasemap(map, originals) {
    var dark = isDark();
    map.getStyle().layers.forEach(function (layer) {
      if (layer.id.indexOf('olt-') === 0) return;
      COLOR_PROPS.forEach(function (prop) {
        var key = layer.id + '|' + prop;
        if (!(key in originals)) {
          try { originals[key] = map.getPaintProperty(layer.id, prop); } catch (e) { originals[key] = undefined; }
        }
        var orig = originals[key];
        if (orig === undefined) return;
        try { map.setPaintProperty(layer.id, prop, dark ? nightColor(orig, prop, layer.id) : orig); } catch (e) { /* no such property */ }
      });
    });
  }

  /* Track features carry no sketch property at all, so has/!has is the
     type-safe test (a != against true would compare boolean with null). */
  var NOT_SKETCH = ['!', ['has', 'sketch']];
  var IS_SKETCH = ['has', 'sketch'];

  function layerDefs(kind, routeMain) {
    if (kind === 'overview') {
      return [
        { id: 'olt-casing', color: '--casing', width: [3, 4, 9, 9], filter: NOT_SKETCH },
        { id: 'olt-hi', color: '--ink', width: [3, 7, 9, 11], filter: ['==', ['get', 'id'], ''] },
        { id: 'olt-hi-point', type: 'circle', stroke: '--ink', strokeWidth: 3, radius: [3, 5, 9, 9], filter: ['==', ['get', 'id'], ''] },
        { id: 'olt-line', color: '--trail', width: [3, 1.6, 9, 4], filter: ['all', NOT_SKETCH, ['!=', ['get', 'kind'], 'route']], hit: true },
        { id: 'olt-route', color: '--route', width: [3, 1.6, 9, 4], dash: [1.6, 1.1], filter: ['all', NOT_SKETCH, ['==', ['get', 'kind'], 'route']], hit: true },
        { id: 'olt-sketch', color: '--trail', width: [3, 2, 9, 3.5], dash: [0, 2], cap: 'round', filter: ['all', IS_SKETCH, ['!=', ['get', 'kind'], 'route']], hit: true },
        { id: 'olt-sketch-route', color: '--route', width: [3, 2, 9, 3.5], dash: [0, 2], cap: 'round', filter: ['all', IS_SKETCH, ['==', ['get', 'kind'], 'route']], hit: true },
        { id: 'olt-sketch-points', type: 'circle', strokeByKind: true, strokeWidth: 2, radius: [3, 3, 9, 6], filter: IS_SKETCH, hit: true }
      ];
    }
    if (kind === 'sketch') {
      var col = routeMain ? '--route' : '--trail';
      return [
        { id: 'olt-sketch', color: col, width: [5, 3, 12, 5], dash: [0, 2], cap: 'round', filter: IS_SKETCH },
        { id: 'olt-sketch-points', type: 'circle', stroke: col, strokeWidth: 2.5, radius: [5, 5, 12, 8], filter: IS_SKETCH }
      ];
    }
    return [
      { id: 'olt-casing', color: '--casing', width: [5, 4, 12, 8] },
      { id: 'olt-alt', color: '--trail', width: [5, 1.5, 12, 3], dash: [2, 1.6], filter: ['==', ['get', 'role'], 'alternate'] },
      { id: 'olt-main', color: routeMain ? '--route' : '--trail', width: [5, 2.5, 12, 5],
        dash: routeMain ? [2, 1.2] : null, filter: ['==', ['get', 'role'], 'main'] }
    ];
  }

  function circleStroke(def) {
    if (def.strokeByKind) return ['match', ['get', 'kind'], 'route', token('--route'), token('--trail')];
    return token(def.stroke || '--trail');
  }

  /* Trail lines go under the base map's labels, as on a printed map. */
  function addLineLayers(map, fc, defs) {
    var firstLabel = map.getStyle().layers.filter(function (l) { return l.type === 'symbol'; })[0];
    map.addSource('olt', { type: 'geojson', data: fc });
    defs.forEach(function (def) {
      var layer;
      if (def.type === 'circle') {
        layer = {
          id: def.id, type: 'circle', source: 'olt',
          paint: {
            'circle-radius': ['interpolate', ['linear'], ['zoom'], def.radius[0], def.radius[1], def.radius[2], def.radius[3]],
            'circle-color': token('--casing'),
            'circle-stroke-color': circleStroke(def),
            'circle-stroke-width': def.strokeWidth || 2
          }
        };
      } else {
        layer = {
          id: def.id,
          type: 'line',
          source: 'olt',
          layout: { 'line-join': 'round', 'line-cap': def.cap || (def.dash ? 'butt' : 'round') },
          paint: {
            'line-color': token(def.color),
            'line-width': ['interpolate', ['linear'], ['zoom'], def.width[0], def.width[1], def.width[2], def.width[3]]
          }
        };
        if (def.dash) layer.paint['line-dasharray'] = def.dash;
      }
      if (def.filter) layer.filter = def.filter;
      map.addLayer(layer, firstLabel && firstLabel.id);
    });
  }

  var maps = [];
  var mapStarters = [];

  function initMap(fig) {
    var host = fig.querySelector('.map');
    var fallback = host.querySelector('.map__fallback');
    var status = host.querySelector('.map__status');
    var nw = fig.querySelector('.mapfig__corner--nw');
    var se = fig.querySelector('.mapfig__corner--se');
    var kind = fig.dataset.map;
    var routeMain = fig.dataset.route === 'yes';
    var defs = layerDefs(kind, routeMain);
    var onlyIds = (fig.dataset.ids || '').trim().split(/\s+/).filter(Boolean);
    var entry = { kind: kind, map: null, fc: null, defs: defs, fallback: fallback,
                  visibleIds: onlyIds.length ? onlyIds : null, ready: false,
                  mapStarted: false, fullBounds: null, boundsById: null };
    maps.push(entry);

    var bbox = (fig.dataset.bbox || '').split(',').map(Number);
    if (bbox.length !== 4 || bbox.some(isNaN)) bbox = null;

    function corners(ext) {
      /* A wide map of Alaska reaches past 180°: name that longitude as the east one it is. */
      var wrap = function (lon) { return ((lon + 540) % 360) - 180; };
      if (nw) nw.textContent = dms(ext.n, 'N', 'S') + ' ' + dms(wrap(ext.w), 'E', 'W');
      if (se) se.textContent = dms(ext.s, 'N', 'S') + ' ' + dms(wrap(ext.e), 'E', 'W');
    }
    function redrawFallback() {
      if (!entry.ready && entry.fc) {
        corners(drawFallback(fallback, entry.fc, bbox || bboxOf(entry.fc), routeMain));
        if (entry.visibleIds) setVisible(entry, entry.visibleIds);
      }
    }
    function fail(reason) {
      if (entry.ready) return;
      host.dataset.state = 'fallback';
      status.textContent = 'Base map unavailable (' + reason + '). ' +
        (kind === 'sketch' ? 'The start and end are drawn on a plain graticule.' : 'The track is drawn on a plain graticule.');
    }

    status.textContent = kind === 'sketch' ? 'Loading the map…' : 'Loading the track…';
    var dataReady = fetch(fig.dataset.src, { credentials: 'same-origin' })
      .then(function (r) {
        if (!r.ok) throw new Error(r.status);
        return r.json();
      })
      .then(function (fc) {
        entry.fc = fc;
        bbox = bbox || bboxOf(fc);
        entry.fullBounds = bbox.slice();
        if (kind === 'overview') {
          entry.boundsById = {};
          fc.features.forEach(function (f) {
            var id = (f.properties || {}).id;
            var fb = id && bboxOfFeature(f);
            if (!fb) return;
            var prev = entry.boundsById[id];
            entry.boundsById[id] = prev
              ? [Math.min(prev[0], fb[0]), Math.min(prev[1], fb[1]), Math.max(prev[2], fb[2]), Math.max(prev[3], fb[3])]
              : fb;
          });
        }
        if (!entry.ready && entry.mapStarted && window.maplibregl) status.textContent = 'Loading the base map…';
        redrawFallback();
        return fc;
      })
      .catch(function () {
        host.dataset.state = 'error';
        status.textContent = 'The track data did not load. Downloads on this page are unaffected.';
        return null;
      });

    var resizeTimer;
    window.addEventListener('resize', function () {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(redrawFallback, 150);
    });

    /* The MapLibre half of the map. Everything above (the fetch and the
       fallback drawing) runs as soon as this script does; this part waits
       until MapLibre is present (see startMaps below), because the page loads
       this script before the MapLibre script. If it never arrives the
       fallback drawing stays and fail() says why. */
    function startMapLibre() {
      if (!window.maplibregl) { dataReady.then(function (fc) { if (fc) fail('the map library did not load'); }); return; }
      if (!webglAvailable()) { dataReady.then(function (fc) { if (fc) fail('WebGL is off in this browser'); }); return; }
      if (!entry.ready && entry.fc) status.textContent = 'Loading the base map…';

      var options = {
        container: host.querySelector('.map__canvas'),
        style: STYLE_URL,
        attributionControl: { compact: true },
        cooperativeGestures: true,
        dragRotate: false,
        pitchWithRotate: false,
        touchPitch: false
      };
      if (bbox) {
        options.bounds = [[bbox[0], bbox[1]], [bbox[2], bbox[3]]];
        options.fitBoundsOptions = { padding: 32 };
      }
      var map = new maplibregl.Map(options);
      entry.map = map;
      map.touchZoomRotate.disableRotation();
      map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right');
      var scale = new maplibregl.ScaleControl({ unit: milesFirst() ? 'imperial' : 'metric', maxWidth: 110 });
      map.addControl(scale, 'bottom-left');
      document.addEventListener('olt:units', function () {
        scale.setUnit(milesFirst() ? 'imperial' : 'metric');
      });

      /* A narrow frame has no room for the open attribution beside the scale
         bar; keep it behind its button there, resizing included. */
      function collapseAttribution() {
        if (host.clientWidth >= 560) return;
        host.querySelectorAll('.maplibregl-ctrl-attrib').forEach(function (el) {
          el.classList.remove('maplibregl-compact-show');
          el.removeAttribute('open');
        });
      }
      map.on('resize', collapseAttribution);

      var originals = {};
      var timer = setTimeout(function () { fail('tiles did not load'); }, 15000);
      map.on('error', function () { if (!map.isStyleLoaded()) fail('the map style did not load'); });

      var styleReady = new Promise(function (resolve) { map.on('load', resolve); });
      Promise.all([dataReady, styleReady]).then(function (results) {
        var fc = results[0];
        if (!fc) return;
        clearTimeout(timer);
        tintBasemap(map, originals);
        addLineLayers(map, fc, defs);
        if (!bbox) {
          bbox = bboxOf(fc);
          entry.fullBounds = bbox.slice();
          map.fitBounds([[bbox[0], bbox[1]], [bbox[2], bbox[3]]], { padding: 32, animate: false });
        }
        entry.ready = true;
        host.dataset.state = 'ready';
        status.textContent = '';
        collapseAttribution();
        if (entry.visibleIds) setVisible(entry, entry.visibleIds);
        if (kind === 'overview') wireOverview(map, defs);
        mapCorners();
      });

      function mapCorners() {
        var b = map.getBounds();
        corners({ w: b.getWest(), e: b.getEast(), n: b.getNorth(), s: b.getSouth() });
      }
      map.on('moveend', function () { if (entry.ready) mapCorners(); });
      document.addEventListener('olt:theme', function () {
        if (!entry.ready) return;
        tintBasemap(map, originals);
        defs.forEach(function (def) {
          if (def.type === 'circle') {
            map.setPaintProperty(def.id, 'circle-color', token('--casing'));
            map.setPaintProperty(def.id, 'circle-stroke-color', circleStroke(def));
          } else {
            map.setPaintProperty(def.id, 'line-color', token(def.color));
          }
        });
      });
    }

    mapStarters.push(function () {
      if (entry.mapStarted) return;
      entry.mapStarted = true;
      startMapLibre();
    });
  }

  function startMaps() {
    mapStarters.forEach(function (start) { start(); });
  }

  function entryFor(id) {
    return document.querySelector('.entry[data-id="' + (window.CSS && CSS.escape ? CSS.escape(id) : id) + '"]');
  }

  function highlight(id) {
    maps.forEach(function (m) {
      if (!m.map || !m.ready) return;
      if (m.map.getLayer('olt-hi')) m.map.setFilter('olt-hi', ['==', ['get', 'id'], id || '']);
      if (m.map.getLayer('olt-hi-point')) m.map.setFilter('olt-hi-point', ['==', ['get', 'id'], id || '']);
    });
    document.querySelectorAll('.entry.is-highlit').forEach(function (li) { li.classList.remove('is-highlit'); });
    if (id) {
      var li = entryFor(id);
      if (li) li.classList.add('is-highlit');
    }
  }

  function wireOverview(map, defs) {
    var popup = new maplibregl.Popup({ closeButton: true, maxWidth: '18rem' });
    defs.filter(function (d) { return d.hit; }).forEach(function (def) {
      map.on('mousemove', def.id, function (e) {
        map.getCanvas().style.cursor = 'pointer';
        highlight(e.features[0].properties.id);
      });
      map.on('mouseleave', def.id, function () {
        map.getCanvas().style.cursor = '';
        highlight('');
      });
      map.on('click', def.id, function (e) {
        var p = e.features[0].properties;
        var box = document.createElement('div');
        var a = document.createElement('a');
        a.href = '/trails/' + encodeURIComponent(p.id) + '/';
        a.textContent = p.name;
        var meta = document.createElement('p');
        meta.textContent = lengthText(Number(p.length_km)) + (p.kind === 'route' ? ' · Route' : '');
        box.appendChild(a);
        box.appendChild(meta);
        if (p.sketch) {
          var g = e.features[0].geometry || {};
          var pointOnly = (g.type === 'MultiPoint' && g.coordinates.length === 1) || g.type === 'Point';
          var note = document.createElement('p');
          note.textContent = pointOnly
            ? 'No GPX here. The ring only marks one end of it; it is not the trail\u2019s path.'
            : 'No GPX here. The dotted line only joins the start and the end; it is not the trail\u2019s path.';
          box.appendChild(note);
        }
        popup.setLngLat(e.lngLat).setDOMContent(box).addTo(map);
      });
    });
  }

  /* Fit the overview map to the lines still shown; when every line is shown
     again that is the full extent the map opened at. */
  function fitToVisible(entry, ids) {
    var map = entry.map;
    if (!map || !entry.ready || entry.kind !== 'overview' || !entry.boundsById) return;
    var union = null;
    var shown = 0;
    var total = Object.keys(entry.boundsById).length;
    ids.forEach(function (id) {
      var b = entry.boundsById[id];
      if (!b) return;
      shown += 1;
      union = union
        ? [Math.min(union[0], b[0]), Math.min(union[1], b[1]), Math.max(union[2], b[2]), Math.max(union[3], b[3])]
        : b.slice();
    });
    if (!union) return;
    var target = shown >= total && entry.fullBounds ? entry.fullBounds : union;
    var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    map.fitBounds([[target[0], target[1]], [target[2], target[3]]],
      { padding: 32, maxZoom: 11, animate: !reduceMotion });
  }

  function setVisible(entry, ids) {
    entry.visibleIds = ids;
    var set = {};
    ids.forEach(function (id) { set[id] = true; });
    /* Without the base map, the plain drawing is redrawn on the tracks still
       shown, so the map shows what the filters leave at a useful scale. */
    if (!entry.ready && entry.fc && entry.kind === 'overview') {
      var sub = entry.fc.features.filter(function (f) { return set[(f.properties || {}).id]; });
      var whole = sub.length === entry.fc.features.length;
      if (sub.length) drawFallback(entry.fallback, whole ? entry.fc : { type: 'FeatureCollection', features: sub },
        whole && entry.fullBounds ? entry.fullBounds : bboxOf({ features: sub }), false);
    }
    entry.fallback.querySelectorAll('[data-id]').forEach(function (path) {
      path.style.display = set[path.getAttribute('data-id')] ? '' : 'none';
    });
    var map = entry.map;
    if (!map || !entry.ready) return;
    var inSet = ['in', ['get', 'id'], ['literal', ids]];
    entry.defs.forEach(function (def) {
      if (def.id.indexOf('olt-hi') === 0) return;
      map.setFilter(def.id, def.filter ? ['all', def.filter, inSet] : inSet);
    });
    fitToVisible(entry, ids);
  }

  /* Fetch the line data and draw the fallback at once; start MapLibre now if
     it is already here, and otherwise when the page has loaded (the deferred
     MapLibre script follows this one). The finder and the other controls
     below never wait for it. */
  document.querySelectorAll('.mapfig[data-map]').forEach(initMap);
  if (window.maplibregl || document.readyState === 'complete') startMaps();
  else window.addEventListener('load', startMaps);

  /* 2b. Sorting every list of trails -----------------------------------------
     The same orders as facets.SORTS in Python, over the rows' data-*
     attributes. The "Sort by" select is the one control for keyboard and
     screen-reader users (the column-head buttons are aria-hidden pointer
     shortcuts that always agree with it); each new order is announced in
     the [data-sort-status] live region. ?sort=<key> is written with
     replaceState when the order is not the page's default, and honoured
     on load and on back/forward. */

  var SORT_KEYS = { 'name': 1, 'name-desc': 1, 'length-desc': 1, 'length-asc': 1,
                    'time-asc': 1, 'time-desc': 1, 'climb-desc': 1, 'climb-asc': 1 };
  var SORT_OLD = { 'long': 'length-desc', 'short': 'length-asc', 'quick': 'time-asc', 'climb': 'climb-desc' };
  var SORT_COLUMN = { 'name': 'name', 'name-desc': 'name', 'length-desc': 'length', 'length-asc': 'length',
                      'time-asc': 'time', 'time-desc': 'time', 'climb-desc': 'climb', 'climb-asc': 'climb' };
  var SORT_ARROW = { 'name': '↑', 'name-desc': '↓', 'length-desc': '↓', 'length-asc': '↑',
                     'time-asc': '↑', 'time-desc': '↓', 'climb-desc': '↓', 'climb-asc': '↑' };
  var COLUMN_PRIMARY = { 'name': 'name', 'length': 'length-desc', 'time': 'time-asc', 'climb': 'climb-desc' };
  var COLUMN_TOGGLE = { 'name': 'name-desc', 'name-desc': 'name', 'length-desc': 'length-asc', 'length-asc': 'length-desc',
                        'time-asc': 'time-desc', 'time-desc': 'time-asc', 'climb-desc': 'climb-asc', 'climb-asc': 'climb-desc' };

  function normalizeSortKey(value, dflt) {
    if (SORT_KEYS[value]) return value;
    if (SORT_OLD[value]) return SORT_OLD[value];
    return SORT_KEYS[dflt] ? dflt : 'name';
  }
  function cmpStr(a, b) { return a < b ? -1 : a > b ? 1 : 0; }
  function cmpNum(a, b) { return a < b ? -1 : a > b ? 1 : 0; }

  function compareEntries(a, b, key) {
    key = normalizeSortKey(key, 'name');
    var an = a.dataset.name || '', bn = b.dataset.name || '';
    if (key === 'name') return cmpStr(an, bn);
    if (key === 'name-desc') return cmpStr(bn, an);
    if (key === 'climb-desc' || key === 'climb-asc') {
      var ac = a.dataset.climb === '' || a.dataset.climb == null ? null : Number(a.dataset.climb);
      var bc = b.dataset.climb === '' || b.dataset.climb == null ? null : Number(b.dataset.climb);
      if (ac === null || bc === null) {
        if (ac === null && bc === null) return cmpStr(an, bn);
        return ac === null ? 1 : -1;
      }
      return (key === 'climb-desc' ? cmpNum(bc, ac) : cmpNum(ac, bc)) || cmpStr(an, bn);
    }
    var av = Number(key.indexOf('length') === 0 ? a.dataset.km : a.dataset.days);
    var bv = Number(key.indexOf('length') === 0 ? b.dataset.km : b.dataset.days);
    return (key.slice(-5) === '-desc' ? cmpNum(bv, av) : cmpNum(av, bv)) || cmpStr(an, bn);
  }

  function sortEntriesIn(root, key) {
    root.querySelectorAll('ol.entries').forEach(function (list) {
      Array.prototype.slice.call(list.querySelectorAll('.entry'))
        .sort(function (a, b) { return compareEntries(a, b, key); })
        .forEach(function (li) { list.appendChild(li); });
    });
  }

  function defaultSortOf(root) {
    return normalizeSortKey(root && root.dataset ? root.dataset.defaultSort : '', 'name');
  }

  function syncSortHeads(root, key) {
    root.querySelectorAll('[data-sort-col]').forEach(function (btn) {
      var active = SORT_COLUMN[key] === btn.dataset.sortCol;
      btn.classList.toggle('is-active', active);
      var arrow = btn.querySelector('[data-arrow]');
      if (arrow) arrow.textContent = active ? SORT_ARROW[key] : '↕';
    });
  }

  function announceSort(root, key) {
    if (!root) return;
    var status = root.querySelector('[data-sort-status]');
    var select = root.querySelector('[data-sort-select]');
    if (!status || !select) return;
    var label = key;
    Array.prototype.forEach.call(select.options, function (o) { if (o.value === key) label = o.textContent; });
    var text = 'Sorted by ' + label + '.';
    if (status.textContent !== text) status.textContent = text;
  }

  function applySortUI(root, key, announce) {
    key = normalizeSortKey(key, defaultSortOf(root));
    sortEntriesIn(root, key);
    var select = root.querySelector('[data-sort-select]');
    if (select && select.value !== key) select.value = key;
    syncSortHeads(root, key);
    if (announce) announceSort(root, key);
    return key;
  }

  function nextSortForColumn(col, current) {
    current = normalizeSortKey(current, 'name');
    return SORT_COLUMN[current] === col ? COLUMN_TOGGLE[current] : COLUMN_PRIMARY[col];
  }

  function wireSortHeads(root, getKey, setKey) {
    root.querySelectorAll('[data-sort-col]').forEach(function (btn) {
      btn.addEventListener('click', function () { setKey(nextSortForColumn(btn.dataset.sortCol, getKey())); });
    });
  }

  function sortFromUrl(root) {
    return normalizeSortKey(new URLSearchParams(window.location.search).get('sort'), defaultSortOf(root));
  }

  function replaceSortInUrl(root, key) {
    var p = new URLSearchParams(window.location.search);
    if (key === defaultSortOf(root)) p.delete('sort'); else p.set('sort', key);
    var q = p.toString();
    window.history.replaceState(null, '', (q ? '?' + q : window.location.pathname) + window.location.hash);
  }

  function initSortableLists() {
    document.querySelectorAll('.results[data-sortable]').forEach(function (root) {
      if (root.querySelector('#entries')) return; /* the finder wires its own list */
      var select = root.querySelector('[data-sort-select]');
      var current = defaultSortOf(root);
      function setSort(key, updateUrl, announce) {
        current = applySortUI(root, key, announce);
        if (updateUrl) replaceSortInUrl(root, current);
      }
      if (select) select.addEventListener('change', function () { setSort(select.value, true, true); });
      wireSortHeads(root, function () { return current; }, function (k) { setSort(k, true, true); });
      setSort(sortFromUrl(root), false, false);
      window.addEventListener('popstate', function () { setSort(sortFromUrl(root), false, false); });
    });
  }

  /* 3. Trail finder (home page) ------------------------------------------------
     The filters are the attributes every page names: Where, Length, Time,
     Season, Terrain, Kind, Walking, Shape and GPX. Each row carries its values
     as data-* attributes (olt/home.py entry()). A filter on a facet that a
     trail has no value for leaves that trail out, and the note under the
     filter (data-missing) says how many trails have no value on file. */

  var MULTI = ['time', 'terrain', 'walking', 'shape', 'gpx'];
  var MORE = ['walking', 'shape', 'gpx'];
  /* Addresses from before the site had these filters still work. */
  var OLD_POLICY = { open: 'free', sold: 'sold', withheld: 'unpublished', unclear: 'elsewhere' };

  function initFinder(form) {
    var list = document.getElementById('entries');
    var items = Array.prototype.slice.call(list.querySelectorAll('.entry'));
    var count = document.getElementById('results-count');
    var empty = document.getElementById('empty-state');
    var active = form.querySelector('.filters__active');
    var lenHint = document.getElementById('len-hint');
    var resultsRoot = list.closest('.results');
    var listHead = resultsRoot ? resultsRoot.querySelector('.list-head') : document.querySelector('.list-head');
    var el = form.elements;
    var sort = document.getElementById('sort');
    var defaultSort = defaultSortOf(resultsRoot);
    var more = form.querySelector('.filters__more');
    var total = items.length;

    /* The count is the one live region. Keep it quiet through the first
       application below so nothing is announced on load, and write to it
       only when its text changes. The length hint is a description of the
       length fields, not a live region of its own. */
    if (count) count.setAttribute('aria-live', 'off');
    if (lenHint) {
      lenHint.removeAttribute('aria-live');
      lenHint.removeAttribute('role');
      [el.min, el.max].forEach(function (field) {
        if (!field) return;
        var described = (field.getAttribute('aria-describedby') || '').split(/\s+/).filter(Boolean);
        if (described.indexOf('len-hint') === -1) described.push('len-hint');
        field.setAttribute('aria-describedby', described.join(' '));
      });
    }

    function setText(node, text) {
      if (node && node.textContent !== text) node.textContent = text;
    }

    function hasOption(select, value) {
      return !!select && Array.prototype.some.call(select.options, function (o) { return o.value === value; });
    }

    function boxes(name) {
      return Array.prototype.slice.call(form.querySelectorAll('input[type="checkbox"][name="' + name + '"]'));
    }
    function checked(name) {
      return boxes(name).filter(function (b) { return b.checked; }).map(function (b) { return b.value; });
    }
    function radio(name) {
      var r = form.querySelector('input[name="' + name + '"]:checked');
      return r ? r.value : '';
    }

    function read() {
      var min = stepKm(el.min.value) || 0;
      var max = stepKm(el.max.value) || Infinity;
      var minRaw = el.min.value, maxRaw = el.max.value;
      var swapped = min > max;
      if (swapped) { var keep = min; min = max; max = keep; keep = minRaw; minRaw = maxRaw; maxRaw = keep; }
      var s = {
        q: el.q.value.trim(),
        words: el.q.value.trim().toLowerCase().split(/\s+/).filter(Boolean),
        where: el.where.value,
        min: min,
        max: max,
        minRaw: minRaw,
        maxRaw: maxRaw,
        swapped: swapped,
        month: el.month ? el.month.value : '',
        kind: radio('kind')
      };
      MULTI.forEach(function (name) { s[name] = checked(name); });
      return s;
    }

    function words(value) { return (value || '').split(' ').filter(Boolean); }
    function anyOf(chosen, value) { return !chosen.length || chosen.indexOf(value) !== -1; }

    function matches(li, s) {
      var d = li.dataset;
      if (s.words.some(function (w) { return d.search.indexOf(w) === -1; })) return false;
      if (s.where && words(d.where).indexOf(s.where) === -1) return false;
      var km = Number(d.km);
      if (km < s.min || km > s.max) return false;
      if (!anyOf(s.time, d.time)) return false;
      if (s.month && words(d.months).indexOf(s.month) === -1) return false;
      if (s.terrain.length && !words(d.terrain).some(function (t) { return s.terrain.indexOf(t) !== -1; })) return false;
      if (s.kind && d.kind !== s.kind) return false;
      if (s.walking.length && !anyOf(s.walking, d.walking)) return false;
      if (s.shape.length && !anyOf(s.shape, d.shape)) return false;
      if (!anyOf(s.gpx, d.gpx)) return false;
      return true;
    }

    /* A length step's value is "100mi" or "160km": round in its own unit, so the
       list offered follows the reader's units. Filtering compares kilometres. */
    function stepKm(value) {
      var m = /^(\d+(?:\.\d+)?)(mi|km)$/.exec(value || '');
      return m ? Number(m[1]) * (m[2] === 'mi' ? KM_PER_MI : 1) : 0;
    }

    function stepLabel(n, unit) {
      var km = unit === 'mi' ? n * KM_PER_MI : n;
      var other = unit === 'mi' ? fmt.format(Math.round(km)) + ' km' : fmt.format(Math.round(km / KM_PER_MI)) + ' mi';
      return fmt.format(n) + ' ' + unit + ' \u00b7 ' + other;
    }

    /* Offer round steps in the reader's units. The server writes the mile steps;
       a reader who chose kilometres gets the kilometre steps (data-steps-km), and
       a chosen step moves to the nearest one in the new list. */
    function buildLengthOptions() {
      var unit = milesFirst() ? 'mi' : 'km';
      form.querySelectorAll('select[data-length-options]').forEach(function (select) {
        var kind = select.dataset.lengthOptions;
        var steps = (select.getAttribute('data-steps-' + unit) || '').split(',').filter(Boolean).map(Number);
        var wasKm = stepKm(select.value);
        select.textContent = '';
        function add(value, text, selected) {
          var o = document.createElement('option');
          o.value = value;
          o.textContent = text;
          if (selected) o.selected = true;
          select.appendChild(o);
        }
        if (kind === 'min') add('', 'Any', false);
        steps.slice(kind === 'min' ? 0 : 1, kind === 'min' ? -1 : undefined).forEach(function (n) {
          add(n + unit, stepLabel(n, unit), false);
        });
        if (kind === 'max') add('', 'Any', !wasKm);
        if (wasKm) {
          var best = null, gap = Infinity;
          Array.prototype.forEach.call(select.options, function (o) {
            var k = stepKm(o.value);
            if (!k) return;
            var d = Math.abs(Math.log(k / wasKm));
            if (d < gap) { gap = d; best = o; }
          });
          if (best) best.selected = true;
        }
      });
    }

    function describeLength(s) {
      var text;
      if (!s.min && s.max === Infinity) text = 'Any length.';
      else if (!s.min) text = 'Up to ' + lengthText(Math.round(s.max)) + '.';
      else if (s.max === Infinity) text = 'From ' + lengthText(Math.round(s.min)) + ' up.';
      else text = 'From ' + lengthText(Math.round(s.min)) + ' to ' + lengthText(Math.round(s.max)) + '.';
      if (s.swapped) text += ' Shortest and longest were swapped.';
      return text;
    }

    function relabelLengths() {
      buildLengthOptions();
      setText(lenHint, describeLength(read()));
      apply(true);
    }

    /* URL query <-> form. Only values that differ from the defaults are written. */
    function toQuery(s) {
      var p = new URLSearchParams();
      if (s.q) p.set('q', s.q);
      if (s.where) p.set('where', s.where);
      if (s.min) p.set('min', s.minRaw);
      if (s.max !== Infinity) p.set('max', s.maxRaw);
      if (s.month) p.set('month', s.month);
      if (s.kind) p.set('kind', s.kind);
      MULTI.forEach(function (name) { if (s[name].length) p.set(name, s[name].join(',')); });
      if (sort.value !== defaultSort) p.set('sort', sort.value);
      return p.toString();
    }

    function fromQuery() {
      var p = new URLSearchParams(window.location.search);
      el.q.value = p.get('q') || '';
      var where = p.get('where') || p.get('region') || '';
      if (!where && (p.get('country') === 'US' || p.get('country') === 'CA')) where = p.get('country');
      el.where.value = hasOption(el.where, where) ? where : '';
      ['min', 'max', 'month'].forEach(function (name) {
        if (!el[name]) return;
        var v = p.get(name) || '';
        el[name].value = hasOption(el[name], v) ? v : '';
      });
      var kind = p.get('kind') || '';
      if (kind === 'designated') kind = 'trail';
      syncRadios('#finder-form input[name="kind"]', kind === 'trail' || kind === 'route' ? kind : '');
      var lists = {};
      MULTI.forEach(function (name) { lists[name] = (p.get(name) || '').split(',').filter(Boolean); });
      if (p.get('line') === '1' && !lists.gpx.length) lists.gpx = ['here', 'partial'];
      if (p.get('policy') && OLD_POLICY[p.get('policy')] && !lists.gpx.length) lists.gpx = [OLD_POLICY[p.get('policy')]];
      MULTI.forEach(function (name) {
        boxes(name).forEach(function (b) { b.checked = lists[name].indexOf(b.value) !== -1; });
      });
      sort.value = normalizeSortKey(p.get('sort'), defaultSort);
    }

    function applySort() {
      if (resultsRoot) applySortUI(resultsRoot, sort.value, false);
    }

    function apply(updateUrl) {
      var s = read();
      var shown = [];
      items.forEach(function (li) {
        var ok = matches(li, s);
        li.hidden = !ok;
        if (ok) shown.push(li.dataset.id);
      });
      var noun = total === 1 ? ' trail' : ' trails';
      if (count && count.textContent !== shown.length + ' of ' + total + noun) {
        count.innerHTML = '';
        var strong = document.createElement('strong');
        strong.textContent = String(shown.length);
        count.appendChild(strong);
        count.appendChild(document.createTextNode(' of ' + total + noun));
      }
      empty.hidden = shown.length > 0;
      if (listHead) listHead.hidden = shown.length === 0;
      setText(lenHint, describeLength(s));

      /* Say how many trails a filter leaves out for having no value on file. */
      var on = { season: !!s.month, terrain: s.terrain.length > 0, walking: s.walking.length > 0, shape: s.shape.length > 0 };
      form.querySelectorAll('[data-missing]').forEach(function (note) { note.hidden = !on[note.dataset.missing]; });

      var n = MORE.reduce(function (sum, name) { return sum + (s[name].length ? 1 : 0); }, 0);
      active.textContent = n ? n + ' on' : '';
      var all = (s.where ? 1 : 0) + (s.min ? 1 : 0) + (s.max !== Infinity ? 1 : 0) + (s.month ? 1 : 0) + (s.kind ? 1 : 0) +
        (s.time.length ? 1 : 0) + (s.terrain.length ? 1 : 0) + n;
      setText(form.querySelector('.filters__count'), all ? all + ' on' : '');

      maps.forEach(function (m) { if (m.kind === 'overview') setVisible(m, shown); });
      if (updateUrl) {
        var q = toQuery(s);
        window.history.replaceState(null, '', (q ? '?' + q : window.location.pathname) + window.location.hash);
      }
    }

    form.addEventListener('input', function () { apply(true); });
    form.addEventListener('change', function () { apply(true); });
    form.addEventListener('submit', function (e) { e.preventDefault(); });
    form.addEventListener('reset', function () { setTimeout(function () { apply(true); }, 0); });
    document.querySelectorAll('[data-reset]').forEach(function (b) {
      b.addEventListener('click', function () { form.reset(); el.q.focus(); });
    });
    sort.addEventListener('change', function () { applySort(); apply(true); announceSort(resultsRoot, sort.value); });
    if (resultsRoot) wireSortHeads(resultsRoot, function () { return sort.value; }, function (k) {
      sort.value = k; applySort(); apply(true); announceSort(resultsRoot, sort.value);
    });
    document.addEventListener('olt:units', relabelLengths);

    items.forEach(function (li) {
      li.addEventListener('mouseenter', function () { highlight(li.dataset.id); });
      li.addEventListener('mouseleave', function () { highlight(''); });
      li.addEventListener('focusin', function () { highlight(li.dataset.id); });
      li.addEventListener('focusout', function () { highlight(''); });
    });

    buildLengthOptions();
    fromQuery();
    applySort();
    apply(false);
    /* The count can announce from here on; the first application is done. */
    setTimeout(function () { if (count) count.removeAttribute('aria-live'); }, 0);
    /* The filters behind "More" stay folded, unless the address already sets one. */
    var s0 = read();
    if (more && MORE.some(function (name) { return s0[name].length; })) more.open = true;
    /* On a narrow screen the filters fold behind their heading, so the trails
       come first; they stay open when the address already sets one. */
    var panel = form.querySelector('.filters__panel');
    var firstOn = s0.where || s0.min || s0.max !== Infinity || s0.month || s0.kind || s0.time.length || s0.terrain.length;
    if (panel && window.matchMedia('(max-width: 63.99rem)').matches && !firstOn) panel.open = false;
    window.addEventListener('popstate', function () { fromQuery(); applySort(); apply(false); });
  }

  var finder = document.getElementById('finder-form');
  if (finder) initFinder(finder);
  initSortableLists();

  /* 4. A link to a part of the page inside a closed <details> (About this data)
     opens it, so the target is shown rather than hidden. */
  function revealHash() {
    var id = decodeURIComponent(window.location.hash.slice(1));
    var target = id && document.getElementById(id);
    var opened = false;
    for (var el = target; el; el = el.parentElement) {
      if (el.tagName === 'DETAILS' && !el.open) { el.open = true; opened = true; }
    }
    if (opened) target.scrollIntoView();
  }
  window.addEventListener('hashchange', revealHash);
  if (window.location.hash) revealHash();

  /* 5. Copy a required credit ------------------------------------------------ */

  document.querySelectorAll('[data-copy]').forEach(function (button) {
    var target = document.querySelector(button.dataset.copy);
    var done = document.querySelector(button.dataset.copyStatus);
    if (!target) return;
    button.hidden = false;
    button.addEventListener('click', function () {
      var text = target.textContent.trim();
      function ok() { if (done) done.textContent = 'Copied: ' + text; }
      function manual() {
        var range = document.createRange();
        range.selectNodeContents(target);
        var sel = window.getSelection();
        sel.removeAllRanges();
        sel.addRange(range);
        if (done) done.textContent = 'Selected. Press Ctrl+C or ⌘C to copy.';
      }
      if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(text).then(ok, manual);
      else manual();
    });
  });
})();
