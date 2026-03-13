/* ================================================
   GET INVOLVED — Form handling JS
   get-involved.js
   ================================================ */

(function () {
  'use strict';

  /* Generic form submit handler */
  function handleForm(formId, btnId, successText, successColor) {
    const form = document.getElementById(formId);
    if (!form) return;

    const btn = btnId
      ? document.getElementById(btnId)
      : form.querySelector('button[type="submit"]');

    form.addEventListener('submit', function (e) {
      e.preventDefault();

      // Basic validation — check all required visible inputs
      const inputs = form.querySelectorAll('input:not([type="hidden"]), textarea, select');
      let valid = true;

      inputs.forEach(function (el) {
        // Skip optional fields (those whose label contains "(optional)")
        const label = form.querySelector('label[for="' + el.id + '"]');
        const isOptional = label && label.textContent.includes('optional');
        if (!isOptional && !el.value.trim()) {
          el.style.borderColor = 'var(--web)';
          el.style.boxShadow = '0 0 0 3px rgba(200,0,42,.2)';
          valid = false;
          el.focus();
        }
      });

      if (!valid) return;

      // Success state
      if (btn) {
        btn.textContent = successText || 'SENT ✓';
        btn.style.background = successColor || '#1a7a3a';
        btn.style.boxShadow = '0 0 18px rgba(26,122,58,.4)';
        btn.disabled = true;
      }

      // Disable all inputs
      inputs.forEach(function (el) {
        el.disabled = true;
        el.style.borderColor = '';
        el.style.boxShadow = '';
      });
    });

    // Clear error styling on input
    form.querySelectorAll('input, textarea, select').forEach(function (el) {
      el.addEventListener('input', function () {
        el.style.borderColor = '';
        el.style.boxShadow = '';
      });
    });
  }

  handleForm('pitchForm',  'pitchSubmit', 'PITCH SENT ✓',    '#1a6a3a');
  handleForm('joinForm',   null,          'REQUEST SENT ✓',  '#1a6a3a');
  handleForm('tipForm',    null,          'SUBMITTED ✓',     '#1a6a3a');

  /* Scroll-triggered reveal for gi-way, gi-tier, gi-form */
  if ('IntersectionObserver' in window) {
    const targets = document.querySelectorAll(
      '.gi-way, .gi-form, .gi-tier, .gi-form-info, .gi-patron-title, .gi-patron-sub'
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
