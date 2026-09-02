(function () {
  "use strict";

  var shell = document.querySelector(".cook-shell");
  var stack = document.querySelector(".cook-step-stack");
  if (!shell || !stack) return;

  var LOCK_DISTANCE = 10; // px - travel before committing this gesture as vertical vs. a stray tap
  var MIN_DISTANCE = 70; // px - minimum vertical travel to count as a swipe on release
  var MAX_HORIZONTAL_RATIO = 0.6; // horizontal movement must stay under this fraction of vertical, to tell a swipe from a horizontal gesture
  var MAX_DRAG = 140; // px - visual clamp so a long drag doesn't overshoot the next/prev slot

  var startX = null;
  var startY = null;
  var verticalLock = false; // true once this gesture has committed to being a vertical swipe

  function reset() {
    stack.classList.remove("dragging");
    stack.style.removeProperty("--drag-y");
    verticalLock = false;
  }

  shell.addEventListener(
    "touchstart",
    function (e) {
      if (e.touches.length !== 1) {
        reset();
        return;
      }
      // Ignore swipes starting on an interactive control (Prev/Next
      // buttons, the Leave link) so a tap-drag there never becomes a step
      // navigation on top of the button's own action.
      if (e.target.closest("button, a, input, form")) {
        startX = null;
        return;
      }
      startX = e.touches[0].clientX;
      startY = e.touches[0].clientY;
      verticalLock = false;
    },
    { passive: true }
  );

  // Must be non-passive: once the gesture reveals itself as a vertical
  // swipe, preventDefault() stops the browser from treating it as a page
  // scroll/pull-to-refresh - same reasoning as cookbook-swipe.js and the
  // original cook-swipe.js, just on the other axis.
  shell.addEventListener(
    "touchmove",
    function (e) {
      if (startX === null || e.touches.length !== 1) return;
      var dx = e.touches[0].clientX - startX;
      var dy = e.touches[0].clientY - startY;

      if (!verticalLock) {
        var dist = Math.hypot(dx, dy);
        if (dist < LOCK_DISTANCE) return; // too small yet to tell intent
        if (Math.abs(dx) > Math.abs(dy) * MAX_HORIZONTAL_RATIO) {
          // Reveals itself as a horizontal gesture, not a step swipe.
          startX = null;
          return;
        }
        verticalLock = true;
        stack.classList.add("dragging");
      }

      if (e.cancelable) e.preventDefault();

      // Live drag-follow: the whole prev/current/next stack tracks the
      // finger directly on every touchmove (see the --drag-y-driven
      // transforms in app.css), instead of only reacting once released.
      var clamped = Math.max(-MAX_DRAG, Math.min(MAX_DRAG, dy));
      stack.style.setProperty("--drag-y", clamped + "px");
    },
    { passive: false }
  );

  shell.addEventListener(
    "touchend",
    function (e) {
      if (startX === null || !verticalLock) {
        reset();
        startX = null;
        return;
      }
      var touch = e.changedTouches[0];
      var dy = touch.clientY - startY;
      startX = null;

      // Dropping .dragging re-enables the CSS transition, so whichever
      // happens next - a snap-back to 0, or the page unloading mid-navigate
      // - animates smoothly from wherever the drag left off. On a browser
      // with the cross-document View Transition support this app already
      // opts into (see cook_step.html), a committed swipe's in-flight
      // navigation picks up from this exact dragged position instead of
      // jumping, so the drag and the page-transition read as one
      // continuous motion.
      reset();

      if (dy <= -MIN_DISTANCE) {
        window.location.href = shell.getAttribute("data-swipe-next");
      } else if (dy >= MIN_DISTANCE) {
        window.location.href = shell.getAttribute("data-swipe-prev");
      }
    },
    { passive: true }
  );

  shell.addEventListener(
    "touchcancel",
    function () {
      reset();
      startX = null;
    },
    { passive: true }
  );
})();
