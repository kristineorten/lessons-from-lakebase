/* Applies the saved theme before the page paints. */
try {
  var saved = localStorage.getItem("theme");
  if (saved) document.documentElement.dataset.theme = saved;
} catch (e) {}
