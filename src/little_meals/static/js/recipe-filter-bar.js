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

  // The reset icon lives inside <summary>, which otherwise treats any
  // click within it as a toggle - stop that so resetting doesn't also
  // flip the panel open/closed on its way to /recipes.
  var reset = document.querySelector(".filter-bar-reset");
  if (reset) {
    reset.addEventListener("click", function (e) {
      e.stopPropagation();
    });
  }
})();
