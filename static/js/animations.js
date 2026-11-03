// Lightweight IntersectionObserver-based entrance animations
document.addEventListener('DOMContentLoaded', function () {
  // Fade-in elements meant to animate on load
  document.querySelectorAll('.animate-load').forEach(el => el.classList.add('in-view'));

  // Observe elements with .animate-on-scroll
  const observerOpts = { root: null, rootMargin: '0px 0px -10% 0px', threshold: 0.08 };
  const io = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('in-view');
        io.unobserve(entry.target);
      }
    });
  }, observerOpts);

  document.querySelectorAll('.animate-on-scroll').forEach(el => io.observe(el));

  // Add ripple effect helper for buttons with class ripple
  document.addEventListener('pointerdown', (e) => {
    const btn = e.target.closest('.ripple');
    if (!btn) return;
    // the CSS handles the visual; nothing further required here
  });
});
