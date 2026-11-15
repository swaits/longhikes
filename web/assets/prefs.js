/* Runs in <head>, before first paint: marks that JavaScript runs, and applies the
   reader's saved theme and length order. Saved by app.js (footer switches). */
(function () {
  'use strict';
  var root = document.documentElement;
  root.classList.add('js');
  try {
    var theme = localStorage.getItem('lh-theme');
    var units = localStorage.getItem('lh-units');
    if (theme === 'light' || theme === 'dark') root.dataset.theme = theme;
    if (units === 'km') root.dataset.units = 'km';  /* anything else, an old 'mi' included, is miles */
  } catch (e) { /* storage blocked: defaults apply */ }
})();
