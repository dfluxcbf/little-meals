(function () {
  "use strict";

  var grid = document.querySelector(".recipe-grid");
  if (!grid) return;

  var LOCK_DISTANCE = 10; // px - travel before committing this gesture as horizontal vs. a vertical scroll
  var MIN_DISTANCE = 60; // px - minimum horizontal travel to count as a swipe on release
  var MAX_VERTICAL_RATIO = 0.5; // vertical movement must stay under half of horizontal, to tell a swipe from a scroll
  var MAX_DRAG = 90; // px - visual clamp so a long drag doesn't fling the card off-card

  var startX = null;
  var startY = null;
  var startCard = null;
  var horizontalLock = false; // true once this gesture has committed to being a swipe, not a page scroll

  function reset(card) {
    if (card) {
      card.classList.remove("swiping", "recipe-card-swipe-right-hint", "recipe-card-swipe-left-hint");
      card.style.removeProperty("--swipe-x");
      card.style.removeProperty("--swipe-progress");
    }
    startCard = null;
    horizontalLock = false;
  }

  grid.addEventListener(
    "touchstart",
    function (e) {
      if (e.touches.length !== 1) {
        reset(startCard);
        return;
      }
      var card = e.target.closest(".recipe-card");
      // Ignore swipes starting on an interactive control (the recipe title
      // link) so a tap-drag there is never reinterpreted as an add/remove.
      if (!card || e.target.closest("a, button, input, form")) {
        reset(startCard);
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
          reset(startCard);
          return;
        }
        horizontalLock = true;
        startCard.classList.add("swiping");
      }

      if (e.cancelable) e.preventDefault();

      // Live drag-follow: the card (and its add/remove color hint) tracks
      // the finger directly, every touchmove, instead of only reacting
      // once the gesture is released - see the --swipe-x/--swipe-progress
      // custom properties in app.css.
      var clamped = Math.max(-MAX_DRAG, Math.min(MAX_DRAG, dx));
      var progress = Math.min(1, Math.abs(dx) / MIN_DISTANCE);
      startCard.style.setProperty("--swipe-x", clamped + "px");
      startCard.style.setProperty("--swipe-progress", String(progress));
      startCard.classList.toggle("recipe-card-swipe-right-hint", dx > 0);
      startCard.classList.toggle("recipe-card-swipe-left-hint", dx < 0);
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
      var committed = horizontalLock && Math.abs(dx) >= MIN_DISTANCE && Math.abs(dy) <= Math.abs(dx) * MAX_VERTICAL_RATIO;

      // Always resets --swipe-x to 0 and re-enables the transition (by
      // dropping .swiping), so a committed swipe's card springs the rest of
      // the way over while the add/remove request is in flight, and an
      // under-threshold release just springs straight back to resting.
      reset(card);

      if (!committed) return;

      var recipeId = card.getAttribute("data-recipe-id");
      if (!recipeId) return;

      var adding = dx > 0;
      var url = "/recipes/" + recipeId + (adding ? "/add-to-plan" : "/remove-from-plan");
      htmx.ajax("POST", url, { target: card, swap: "outerHTML" });
    },
    { passive: true }
  );

  grid.addEventListener(
    "touchcancel",
    function () {
      reset(startCard);
    },
    { passive: true }
  );
})();
