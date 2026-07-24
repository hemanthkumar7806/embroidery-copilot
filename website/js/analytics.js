// Google Analytics (gtag.js) — inert placeholder.
//
// To enable analytics later: paste your GA4 Measurement ID below
// (looks like "G-XXXXXXXXXX") and reload. No other file needs to change —
// until then this script loads and does nothing, no network requests fired.
(function () {
  "use strict";

  var GA_MEASUREMENT_ID = "";

  if (!GA_MEASUREMENT_ID) return;

  var script = document.createElement("script");
  script.async = true;
  script.src = "https://www.googletagmanager.com/gtag/js?id=" + GA_MEASUREMENT_ID;
  document.head.appendChild(script);

  window.dataLayer = window.dataLayer || [];
  function gtag() {
    window.dataLayer.push(arguments);
  }
  window.gtag = gtag;
  gtag("js", new Date());
  gtag("config", GA_MEASUREMENT_ID);
})();
