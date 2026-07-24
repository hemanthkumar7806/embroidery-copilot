(function () {
  "use strict";

  // OS install tabs
  var tabs = Array.prototype.slice.call(document.querySelectorAll('[role="tab"]'));

  function selectTab(tab) {
    tabs.forEach(function (t) {
      var selected = t === tab;
      t.setAttribute("aria-selected", String(selected));
      t.tabIndex = selected ? 0 : -1;
      var panel = document.getElementById(t.getAttribute("aria-controls"));
      if (panel) panel.hidden = !selected;
    });
    tab.focus();
  }

  tabs.forEach(function (tab, index) {
    tab.addEventListener("click", function () {
      selectTab(tab);
    });
    tab.addEventListener("keydown", function (event) {
      var newIndex = null;
      if (event.key === "ArrowRight") newIndex = (index + 1) % tabs.length;
      if (event.key === "ArrowLeft") newIndex = (index - 1 + tabs.length) % tabs.length;
      if (newIndex !== null) {
        event.preventDefault();
        selectTab(tabs[newIndex]);
      }
    });
  });

  // Detect the visitor's OS and pre-select the matching install tab
  function detectOsTabId() {
    var platform = (navigator.userAgentData && navigator.userAgentData.platform) || navigator.platform || "";
    platform = platform.toLowerCase();
    if (platform.indexOf("mac") !== -1) return "tab-mac";
    if (platform.indexOf("linux") !== -1) return "tab-linux";
    if (platform.indexOf("win") !== -1) return "tab-windows";
    return null;
  }

  var detectedId = detectOsTabId();
  if (detectedId) {
    var detectedTab = document.getElementById(detectedId);
    if (detectedTab) selectTab(detectedTab);
  }

  // Footer year
  var yearEl = document.getElementById("footer-year");
  if (yearEl) yearEl.textContent = String(new Date().getFullYear());
})();
