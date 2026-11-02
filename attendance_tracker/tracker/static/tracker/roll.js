(function () {
  var form = document.getElementById("roll");
  if (!form) return;

  var CYCLE = ["", "present", "late", "absent"];
  var WORD = { "": "Not marked", present: "Present", late: "Late", absent: "Absent" };
  var tiles = Array.prototype.slice.call(form.querySelectorAll(".tile"));
  var total = tiles.length;
  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  var railFill = document.getElementById("rail-fill");
  var progressText = document.getElementById("progress-text");
  var nums = {
    present: document.getElementById("n-present"),
    late: document.getElementById("n-late"),
    absent: document.getElementById("n-absent")
  };

  function setState(tile, state, animate) {
    tile.setAttribute("data-state", state);
    tile.querySelector(".tile-word").textContent = WORD[state];
    tile.querySelector("use").setAttribute("href", "#i-" + (state || "empty"));
    tile.setAttribute("aria-label", tile.getAttribute("data-name") + ": " + WORD[state]);
    tile.parentNode.querySelector("input[type=hidden]").value = state;
    if (animate && !reduceMotion) {
      tile.classList.remove("pop");
      void tile.offsetWidth; // restart the animation
      tile.classList.add("pop");
    }
  }

  function refresh() {
    var counts = { present: 0, late: 0, absent: 0 };
    tiles.forEach(function (t) {
      var s = t.getAttribute("data-state");
      if (s) counts[s] += 1;
    });
    var marked = counts.present + counts.late + counts.absent;
    nums.present.textContent = counts.present;
    nums.late.textContent = counts.late;
    nums.absent.textContent = counts.absent;
    railFill.style.width = (total ? (marked * 100) / total : 0) + "%";
    progressText.textContent =
      marked === total ? "All " + total + " marked" : marked + " of " + total + " marked";
  }

  tiles.forEach(function (tile) {
    tile.addEventListener("click", function () {
      var current = CYCLE.indexOf(tile.getAttribute("data-state"));
      setState(tile, CYCLE[(current + 1) % CYCLE.length], true);
      refresh();
    });

    // Direct keys when a tile has focus: P, L, A set it; Backspace or Delete clears it.
    tile.addEventListener("keydown", function (e) {
      var key = e.key.toLowerCase();
      var map = { p: "present", l: "late", a: "absent", backspace: "", delete: "" };
      if (Object.prototype.hasOwnProperty.call(map, key)) {
        e.preventDefault();
        setState(tile, map[key], true);
        refresh();
      }
    });
  });

  var allBtn = document.getElementById("all-present");
  if (allBtn) {
    allBtn.addEventListener("click", function () {
      tiles.forEach(function (t) {
        if (!t.getAttribute("data-state")) setState(t, "present", false);
      });
      refresh();
    });
  }

  // Sync tiles with any marks that were already saved for this day.
  tiles.forEach(function (t) {
    setState(t, t.getAttribute("data-state"), false);
  });
  refresh();
})();
