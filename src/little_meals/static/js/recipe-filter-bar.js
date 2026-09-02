(function () {
  "use strict";

  var form = document.getElementById("filter-form");
  if (!form) return;

  // Any field change (a pill/select/radio click, or committing a number
  // field via blur/Enter) re-submits immediately - the Apply button stays
  // as a plain-HTML fallback for anyone navigating without JS.
  form.addEventListener("change", function () {
    form.requestSubmit();
  });

  var details = document.querySelector(".filter-bar");
  var summary = details ? details.querySelector(".filter-bar-summary") : null;
  var panel = form; // the <form class="filter-bar-panel"> itself is the animated element

  // The reset icon lives inside <summary>, which otherwise treats any
  // click within it as a toggle - stop that so resetting doesn't also
  // flip the panel open/closed on its way to /recipes.
  var reset = document.querySelector(".filter-bar-reset");
  if (reset) {
    reset.addEventListener("click", function (e) {
      e.stopPropagation();
    });
  }

  if (!details || !summary) return;

  var OPEN_MS = 260;
  var CLOSE_MS = 200;
  var COMMIT_RATIO = 0.35; // fraction of the panel's height a drag must reveal/hide to commit
  var LOCK_DISTANCE = 10; // px - travel before committing this gesture as vertical vs. a tap
  var MAX_HORIZONTAL_RATIO = 0.6; // vertical movement must dominate to count as this gesture

  // The panel already carries its own resting max-height/overflow rules in
  // CSS (a 70vh-based cap on mobile, none on desktop) - read whatever that
  // resolves to right now (before any inline override) so an animated open
  // never overshoots past it and has to visibly snap back down afterward.
  function restingCap() {
    var parsed = parseFloat(getComputedStyle(panel).maxHeight);
    return isNaN(parsed) ? Infinity : parsed;
  }

  function openTargetHeight() {
    return Math.min(panel.scrollHeight, restingCap());
  }

  function clearInlineStyle() {
    panel.style.transition = "";
    panel.style.maxHeight = "";
    panel.style.overflow = "";
  }

  // Animates the panel from `fromHeight` (px) to fully open, ending by
  // clearing all inline overrides so the CSS-authored rules (including the
  // scrollable 70vh cap) take back over.
  function animateOpen(fromHeight, duration) {
    details.open = true;
    var target = openTargetHeight();
    panel.style.overflow = "hidden";
    panel.style.transition = "none";
    panel.style.maxHeight = fromHeight + "px";
    // eslint-disable-next-line no-unused-expressions
    panel.offsetHeight; // force reflow so the 0/from-height starting point actually paints first
    panel.style.transition = "max-height " + duration + "ms cubic-bezier(.2,.8,.2,1)";
    panel.style.maxHeight = target + "px";
    panel.addEventListener("transitionend", function handler(e) {
      if (e.propertyName !== "max-height") return;
      panel.removeEventListener("transitionend", handler);
      clearInlineStyle();
    });
  }

  // Same idea in reverse; sets details.open = false once fully collapsed.
  function animateClose(fromHeight, duration) {
    panel.style.overflow = "hidden";
    panel.style.transition = "none";
    panel.style.maxHeight = fromHeight + "px";
    // eslint-disable-next-line no-unused-expressions
    panel.offsetHeight;
    panel.style.transition = "max-height " + duration + "ms cubic-bezier(.4,0,.6,1)";
    panel.style.maxHeight = "0px";
    panel.addEventListener("transitionend", function handler(e) {
      if (e.propertyName !== "max-height") return;
      panel.removeEventListener("transitionend", handler);
      details.open = false;
      clearInlineStyle();
    });
  }

  // Set right before endDrag() finishes a committed swipe, in case the
  // browser still fires a synthetic click after touchend despite the
  // preventDefault() in touchmove - without this a completed swipe would
  // immediately be undone by this click handler toggling it right back.
  var justDragged = false;

  summary.addEventListener("click", function (e) {
    e.preventDefault();
    if (justDragged) {
      justDragged = false;
      return;
    }
    if (details.open) {
      animateClose(panel.scrollHeight, CLOSE_MS);
    } else {
      animateOpen(0, OPEN_MS);
    }
  });

  // --- Vertical swipe on the handle bar: swipe up to open, down to close,
  // with the panel height tracking the finger live every touchmove (the
  // same "instant feedback" drag-follow idea as the recipe card swipe -
  // see cookbook-swipe.js - applied to revealing/hiding the panel instead
  // of translating a card).
  var startX = null;
  var startY = null;
  var dragging = false;
  var verticalLock = false;
  var wasOpenAtStart = false;
  var naturalHeight = 0;

  function beginDrag() {
    wasOpenAtStart = details.open;
    if (!wasOpenAtStart) {
      details.open = true;
    }
    naturalHeight = openTargetHeight();
    panel.style.transition = "none";
    panel.style.overflow = "hidden";
    panel.style.maxHeight = (wasOpenAtStart ? naturalHeight : 0) + "px";
    // eslint-disable-next-line no-unused-expressions
    panel.offsetHeight;
  }

  function applyDragProgress(dy) {
    var revealed;
    if (wasOpenAtStart) {
      // dragging down closes: dy > 0 hides more of the panel
      revealed = naturalHeight - dy;
    } else {
      // dragging up opens: dy < 0 reveals more of the panel
      revealed = -dy;
    }
    revealed = Math.max(0, Math.min(naturalHeight, revealed));
    panel.style.maxHeight = revealed + "px";
  }

  function endDrag() {
    justDragged = true;
    setTimeout(function () {
      justDragged = false;
    }, 400);
    var current = parseFloat(panel.style.maxHeight) || 0;
    var fraction = naturalHeight > 0 ? current / naturalHeight : 0;
    if (fraction >= COMMIT_RATIO) {
      animateOpen(current, Math.round(OPEN_MS * (1 - fraction)));
    } else {
      animateClose(current, Math.round(CLOSE_MS * fraction));
    }
  }

  summary.addEventListener(
    "touchstart",
    function (e) {
      if (e.touches.length !== 1 || e.target.closest("a, button")) {
        dragging = false;
        return;
      }
      startX = e.touches[0].clientX;
      startY = e.touches[0].clientY;
      dragging = true;
      verticalLock = false;
    },
    { passive: true }
  );

  summary.addEventListener(
    "touchmove",
    function (e) {
      if (!dragging || e.touches.length !== 1) return;
      var dy = e.touches[0].clientY - startY;
      var dx = e.touches[0].clientX - startX;

      if (!verticalLock) {
        var dist = Math.hypot(dx, dy);
        if (dist < LOCK_DISTANCE) return;
        if (Math.abs(dx) > Math.abs(dy) * MAX_HORIZONTAL_RATIO) {
          dragging = false;
          return;
        }
        // Only the legal direction for the current state starts a drag -
        // swipe up to open when closed, swipe down to close when open.
        if ((!details.open && dy >= 0) || (details.open && dy <= 0)) {
          dragging = false;
          return;
        }
        verticalLock = true;
        beginDrag();
      }

      if (e.cancelable) e.preventDefault();
      applyDragProgress(dy);
    },
    { passive: false }
  );

  summary.addEventListener(
    "touchend",
    function () {
      if (dragging && verticalLock) endDrag();
      dragging = false;
      verticalLock = false;
    },
    { passive: true }
  );

  summary.addEventListener(
    "touchcancel",
    function () {
      if (dragging && verticalLock) endDrag();
      dragging = false;
      verticalLock = false;
    },
    { passive: true }
  );
})();
