(function () {
  "use strict";

  var shell = document.querySelector(".cook-shell");
  if (!shell) return;

  var MIN_DISTANCE = 60; // px - minimum horizontal travel to count as a swipe
  var MAX_VERTICAL_RATIO = 0.5; // vertical movement must stay under half of horizontal, to tell a swipe from a scroll

  var startX = null;
  var startY = null;

  shell.addEventListener(
    "touchstart",
    function (e) {
      if (e.touches.length !== 1) return;
      // Ignore swipes starting on an interactive control (a checklist row,
      // the Prev/Next buttons, the Leave link) so a tap-drag there is never
      // reinterpreted as page navigation.
      if (e.target.closest("button, a, input, form")) {
        startX = null;
        return;
      }
      startX = e.touches[0].clientX;
      startY = e.touches[0].clientY;
    },
    { passive: true }
  );

  shell.addEventListener(
    "touchend",
    function (e) {
      if (startX === null) return;
      var touch = e.changedTouches[0];
      var dx = touch.clientX - startX;
      var dy = touch.clientY - startY;
      startX = null;

      if (Math.abs(dx) < MIN_DISTANCE) return;
      if (Math.abs(dy) > Math.abs(dx) * MAX_VERTICAL_RATIO) return;

      var target = dx < 0 ? shell.getAttribute("data-swipe-next") : shell.getAttribute("data-swipe-prev");
      if (target) window.location.href = target;
    },
    { passive: true }
  );
})();
