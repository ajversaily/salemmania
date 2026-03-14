/* ================================================
   SALEM MANIA — get-involved.js
   Scroll reveal only. Forms submit natively via Formspree.
   ================================================ */

(function () {
  'use strict';

  /* Scroll-triggered reveal */
  if ('IntersectionObserver' in window) {
    const targets = document.querySelectorAll(
      '.gi-way, .gi-form, .gi-tier, .gi-form-info, .gi-mission-inner, .gi-patron-title, .gi-patron-sub'
    );

    targets.forEach(function (el) {
      el.style.opacity = '0';
      el.style.transform = 'translateY(24px)';
      el.style.transition = 'opacity .5s ease, transform .5s ease';
      el.style.animationName = 'none';
    });

    const io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.style.opacity = '1';
          entry.target.style.transform = 'translateY(0)';
          io.unobserve(entry.target);
        }
      });
    }, { threshold: 0.1, rootMargin: '0px 0px -30px 0px' });

    targets.forEach(function (el) { io.observe(el); });
  }

})();
