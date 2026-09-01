(function () {
  "use strict";

  var grid = document.querySelector(".recipe-grid");
  if (!grid) return;

  var LOCK_DISTANCE = 10; // px - travel before committing this gesture as horizontal vs. a vertical scroll
  var MIN_DISTANCE = 60; // px - minimum horizontal travel to count as a swipe
  var MAX_VERTICAL_RATIO = 0.5; // vertical movement must stay under half of horizontal, to tell a swipe from a scroll
  var FLASH_DURATION = 220; // ms - matches the CSS animation below

  var startX = null;
  var startY = null;
  var startCard = null;
  var horizontalLock = false; // true once this gesture has committed to being a swipe, not a page scroll

  function reset() {
    startCard = null;
    horizontalLock = false;
  }

  grid.addEventListener(
    "touchstart",
    function (e) {
      if (e.touches.length !== 1) {
        reset();
        return;
      }
      var card = e.target.closest(".recipe-card");
      // Ignore swipes starting on an interactive control (the recipe title
      // link) so a tap-drag there is never reinterpreted as an add/remove.
      if (!card || e.target.closest("a, button, input, form")) {
        reset();
        return;
      }
      startCard = card;
      startX = e.touches[0].clientX;
      startY = e.touches[0].clientY;
      horizontalLock = false;
    },
    { passive: true }
  );

  // Must be non-passive: the whole point is to call preventDefault() once a
  // gesture reveals itself as a horizontal swipe, so the browser's own
  // scroll/pull-to-refresh gesture recognizer doesn't claim it first and
  // fire touchcancel instead of touchend - which silently drops the swipe
  // before touchend logic ever runs. Vertical drags are left untouched
  // (no preventDefault), so normal page scrolling still works everywhere
  // else on the grid.
  grid.addEventListener(
    "touchmove",
    function (e) {
      if (startCard === null || e.touches.length !== 1) return;
      var dx = e.touches[0].clientX - startX;
      var dy = e.touches[0].clientY - startY;

      if (!horizontalLock) {
        var dist = Math.hypot(dx, dy);
        if (dist < LOCK_DISTANCE) return; // too small yet to tell intent
        if (Math.abs(dy) > Math.abs(dx) * MAX_VERTICAL_RATIO) {
          // Reveals itself as a vertical scroll - stop tracking this
          // gesture as a swipe candidate and let the browser scroll.
          reset();
          return;
        }
        horizontalLock = true;
      }

      if (horizontalLock && e.cancelable) e.preventDefault();
    },
    { passive: false }
  );

  grid.addEventListener(
    "touchend",
    function (e) {
      if (startCard === null) return;
      var card = startCard;
      var touch = e.changedTouches[0];
      var dx = touch.clientX - startX;
      var dy = touch.clientY - startY;
      reset();

      if (Math.abs(dx) < MIN_DISTANCE) return;
      if (Math.abs(dy) > Math.abs(dx) * MAX_VERTICAL_RATIO) return;

      var recipeId = card.getAttribute("data-recipe-id");
      if (!recipeId) return;

      var adding = dx > 0;
      var url = "/recipes/" + recipeId + (adding ? "/add-to-plan" : "/remove-from-plan");

      card.classList.add(adding ? "recipe-card-swipe-right" : "recipe-card-swipe-left");
      window.setTimeout(function () {
        htmx.ajax("POST", url, { target: card, swap: "outerHTML" });
      }, FLASH_DURATION);
    },
    { passive: true }
  );

  grid.addEventListener("touchcancel", reset, { passive: true });
})();
