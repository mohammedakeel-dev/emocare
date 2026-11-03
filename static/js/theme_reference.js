/* ==========================================================================
   EmoCare – Interactive Experience Script
   Replicating reference site interactions: Cursor, Loading Screen, Reveals, Nav
   ========================================================================== */

document.addEventListener("DOMContentLoaded", () => {
  // 1. Loading Screen Transition
  const loadingScreen = document.querySelector(".loading-screen");
  if (loadingScreen) {
    const dismissLoader = () => requestAnimationFrame(() => {
      loadingScreen.classList.add("hidden");
    });
    if (document.readyState === "complete") {
      dismissLoader();
    } else {
      window.addEventListener("load", dismissLoader, { once: true });
    }
  }

  // 2. Custom Interactive Cursor (Pointer Fine only)
  const cursorDot = document.querySelector(".cursor-dot");
  const cursorRing = document.querySelector(".cursor-ring");

  if (window.matchMedia("(pointer: fine)").matches) {
    document.addEventListener("pointermove", (event) => {
      if (cursorDot) {
        cursorDot.style.left = `${event.clientX}px`;
        cursorDot.style.top = `${event.clientY}px`;
      }
      if (cursorRing) {
        cursorRing.style.left = `${event.clientX}px`;
        cursorRing.style.top = `${event.clientY}px`;
      }
    });

    const hoverSelectors = "a, button, input, select, textarea, .btn, .button-link, .pill-link, .icon-btn, .card, .panel, .mini-card, .track-card, .game-card, .exercise-card, .subnav-link";
    document.querySelectorAll(hoverSelectors).forEach((element) => {
      element.addEventListener("mouseenter", () => document.body.classList.add("cursor-hover"));
      element.addEventListener("mouseleave", () => document.body.classList.remove("cursor-hover"));
    });
  }

  // 3. Navigation Toggle for Mobile View
  const navToggle = document.querySelector(".nav-toggle");
  const siteNav = document.querySelector(".site-nav");

  if (navToggle && siteNav) {
    navToggle.addEventListener("click", () => {
      const isOpen = siteNav.classList.toggle("open");
      navToggle.setAttribute("aria-expanded", String(isOpen));
    });

    siteNav.querySelectorAll("a").forEach((link) => {
      link.addEventListener("click", () => {
        siteNav.classList.remove("open");
        navToggle.setAttribute("aria-expanded", "false");
      });
    });

    document.addEventListener("click", (event) => {
      const target = event.target;
      const clickedInsideNav = siteNav.contains(target);
      const clickedToggle = navToggle.contains(target);

      if (!clickedInsideNav && !clickedToggle) {
        siteNav.classList.remove("open");
        navToggle.setAttribute("aria-expanded", "false");
      }
    });
  }

  // 4. Scroll Reveal Observer
  const revealItems = document.querySelectorAll(".reveal");
  if (revealItems.length > 0 && "IntersectionObserver" in window) {
    const revealObserver = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            revealObserver.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.08 }
    );

    revealItems.forEach((item) => revealObserver.observe(item));
  } else {
    revealItems.forEach((item) => item.classList.add("is-visible"));
  }

  // 5. Chart.js Dark Luxury Defaults
  if (typeof Chart !== "undefined") {
    Chart.defaults.color = "#77738b";
    Chart.defaults.borderColor = "rgba(80, 70, 126, 0.11)";
    if (Chart.defaults.plugins?.tooltip) {
      Chart.defaults.plugins.tooltip.backgroundColor = "#ffffff";
      Chart.defaults.plugins.tooltip.borderColor = "rgba(80, 70, 126, 0.18)";
      Chart.defaults.plugins.tooltip.borderWidth = 1;
      Chart.defaults.plugins.tooltip.titleColor = "#28253d";
      Chart.defaults.plugins.tooltip.bodyColor = "#68647e";
      Chart.defaults.plugins.tooltip.padding = 10;
      Chart.defaults.plugins.tooltip.cornerRadius = 10;
    }
  }

  // 6. Year in Footer
  const yearEl = document.getElementById("year");
  if (yearEl) {
    yearEl.textContent = new Date().getFullYear();
  }
});


