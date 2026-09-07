(function () {
  "use strict";

  var listContainer = document.getElementById("ingredient-lists");
  var dialog = document.getElementById("ingredient-action-dialog");
  if (!listContainer || !dialog) return;

  var title = document.getElementById("ingredient-action-dialog-title");
  var closeBtn = document.getElementById("ingredient-action-dialog-close");
  var actionButtons = dialog.querySelectorAll(".action-sheet-item");

  var HOLD_MS = 500; // long-press duration before the action sheet opens
  var MOVE_TOLERANCE = 10; // px - travel past this cancels the press (treated as a scroll/drag instead)

  var timer = null;
  var startX = 0;
  var startY = 0;
  var pressedRow = null;

  // Tapped-and-still-selected ingredient names, by name (not DOM refs - the
  // list re-renders after every move). Holding any row moves this whole set
  // at once; holding with nothing selected falls back to moving just the
  // held row, same as before multi-select existed.
  var selected = new Set();

  function clearPress() {
    if (timer !== null) {
      clearTimeout(timer);
      timer = null;
    }
    if (pressedRow) pressedRow.classList.remove("ingredient-row-active");
    pressedRow = null;
  }

  function toggleSelected(row) {
    var name = row.getAttribute("data-name");
    if (selected.has(name)) {
      selected.delete(name);
      row.classList.remove("ingredient-row-selected");
    } else {
      selected.add(name);
      row.classList.add("ingredient-row-selected");
    }
  }

  function rowFor(name) {
    var rows = listContainer.querySelectorAll(".ingredient-row");
    for (var i = 0; i < rows.length; i++) {
      if (rows[i].getAttribute("data-name") === name) return rows[i];
    }
    return null;
  }

  function currentSearchValue() {
    var input = document.getElementById("q");
    return input ? input.value : "";
  }

  function openMenuFor(names) {
    var isSingle = names.length === 1;
    var singleRow = isSingle ? rowFor(names[0]) : null;
    var currentCategory = singleRow ? singleRow.getAttribute("data-category") : null;
    title.textContent = isSingle ? names[0] : names.length + " ingredients selected";
    actionButtons.forEach(function (btn) {
      var isCurrent = isSingle && btn.getAttribute("data-category") === currentCategory;
      btn.disabled = isCurrent;
      btn.textContent = "Move to '" + btn.getAttribute("data-label") + "'" + (isCurrent ? " (current)" : "");
    });
    dialog.dataset.activeNames = JSON.stringify(names);
    dialog.showModal();
  }

  function performMove(names, category) {
    var params = new URLSearchParams();
    names.forEach(function (name) {
      params.append("name", name);
    });
    params.append("category", category);
    params.append("q", currentSearchValue());
    fetch("/settings/ingredients/move", { method: "POST", body: params })
      .then(function (response) {
        return response.text();
      })
      .then(function (html) {
        selected.clear();
        listContainer.innerHTML = html;
      });
  }

  listContainer.addEventListener("pointerdown", function (e) {
    var row = e.target.closest(".ingredient-row");
    if (!row || e.target.closest("a, button, input")) return;
    startX = e.clientX;
    startY = e.clientY;
    clearPress();
    pressedRow = row;
    row.classList.add("ingredient-row-active");
    timer = setTimeout(function () {
      timer = null;
      row.classList.remove("ingredient-row-active");
      var names = selected.size > 0 ? Array.from(selected) : [row.getAttribute("data-name")];
      openMenuFor(names);
    }, HOLD_MS);
  });

  listContainer.addEventListener("pointermove", function (e) {
    if (timer === null || !pressedRow) return;
    var dx = e.clientX - startX;
    var dy = e.clientY - startY;
    if (Math.hypot(dx, dy) > MOVE_TOLERANCE) clearPress();
  });

  listContainer.addEventListener("pointerup", function () {
    // If the hold timer never fired (still pending here), this was a quick
    // tap, not a long-press - toggle that row's selection instead of
    // opening the action sheet.
    var wasTap = timer !== null;
    var row = pressedRow;
    clearPress();
    if (wasTap && row) toggleSelected(row);
  });

  ["pointercancel", "pointerleave"].forEach(function (evt) {
    listContainer.addEventListener(evt, clearPress);
  });

  // A genuine long-press otherwise also triggers the OS text-selection/
  // copy callout on mobile - suppress it for ingredient rows specifically.
  listContainer.addEventListener("contextmenu", function (e) {
    if (e.target.closest(".ingredient-row")) e.preventDefault();
  });

  actionButtons.forEach(function (btn) {
    btn.addEventListener("click", function () {
      if (btn.disabled) return;
      var names = JSON.parse(dialog.dataset.activeNames || "[]");
      var category = btn.getAttribute("data-category");
      dialog.close();
      performMove(names, category);
    });
  });

  closeBtn.addEventListener("click", function () {
    dialog.close();
  });

  dialog.addEventListener("click", function (e) {
    if (e.target === dialog) dialog.close();
  });
})();
