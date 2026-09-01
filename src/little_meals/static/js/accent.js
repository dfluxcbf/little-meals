(function () {
  var STORAGE_KEY = "lmAccentColor";
  // Hex equivalents of each preset's base oklch() token, for the native
  // theme-color meta tag (status bar / task switcher chrome), which needs a
  // color it can render outside the page's own CSS cascade.
  var THEME_COLORS = {
    terracotta: "#c55123",
    sage: "#4b8358",
    rose: "#b65a5c",
    teal: "#2c7e8b",
    plum: "#814a8d",
    gold: "#aa7e00",
  };

  function applyAccent(name) {
    if (!THEME_COLORS.hasOwnProperty(name)) return;
    var root = document.documentElement.style;
    if (name === "terracotta") {
      root.removeProperty("--accent");
      root.removeProperty("--accent-dark");
      root.removeProperty("--accent-soft");
    } else {
      root.setProperty("--accent", "var(--" + name + ")");
      root.setProperty("--accent-dark", "var(--" + name + "-dark)");
      root.setProperty("--accent-soft", "var(--" + name + "-soft)");
    }
    var meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.setAttribute("content", THEME_COLORS[name]);
    // Mirrored server-side so /manifest.webmanifest can match this device's
    // choice - localStorage isn't sent with that plain HTTP fetch.
    try {
      document.cookie = "lm_accent=" + name + ";path=/;max-age=31536000;samesite=lax";
    } catch (e) {}
  }

  window.lmAccentStorageKey = STORAGE_KEY;
  window.lmApplyAccent = applyAccent;

  try {
    var stored = localStorage.getItem(STORAGE_KEY);
    if (stored && stored !== "terracotta") applyAccent(stored);
  } catch (e) {}
})();
