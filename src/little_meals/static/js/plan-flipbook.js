(function () {
  "use strict";

  var track = document.querySelector(".flipbook-track");
  if (!track) return;

  var dots = document.querySelectorAll(".flipbook-dot");
  if (!dots.length) return;

  function updateActive() {
    var pages = track.querySelectorAll(".flipbook-page");
    var trackRect = track.getBoundingClientRect();
    var center = trackRect.left + trackRect.width / 2;
    var closest = 0;
    var closestDist = Infinity;

    pages.forEach(function (page, i) {
      var rect = page.getBoundingClientRect();
      var dist = Math.abs(rect.left + rect.width / 2 - center);
      if (dist < closestDist) {
        closestDist = dist;
        closest = i;
      }
    });

    dots.forEach(function (dot, i) {
      dot.classList.toggle("flipbook-dot-active", i === closest);
    });
  }

  var ticking = false;
  track.addEventListener(
    "scroll",
    function () {
      if (ticking) return;
      ticking = true;
      requestAnimationFrame(function () {
        updateActive();
        ticking = false;
      });
    },
    { passive: true }
  );

  updateActive();
})();
