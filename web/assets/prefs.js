/* Runs in <head>, before first paint: marks that JavaScript runs, and applies the
   reader's saved theme, length order and base map. Saved by app.js (the units
   switch and theme menu in the header, and the Outdoor / Plain switch on a
   trail map). The theme menu's button shows the theme from html[data-theme],
   so it is right from the first paint too. */
(function () {
  'use strict';
  var root = document.documentElement;
  root.classList.add('js');
  try {
    var theme = localStorage.getItem('lh-theme');
    var units = localStorage.getItem('lh-units');
    var basemap = localStorage.getItem('lh-basemap');
    if (theme === 'light' || theme === 'dark') root.dataset.theme = theme;
    if (units === 'km') root.dataset.units = 'km';  /* anything else, an old 'mi' included, is miles */
    if (basemap === 'plain') root.dataset.basemap = 'plain';  /* anything else is the outdoor map */
  } catch (e) { /* storage blocked: defaults apply */ }
})();
