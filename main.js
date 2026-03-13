/* ================================================
   THE DAILY DISPATCH — Spider Web Navigation JS
   main.js
   ================================================ */

(function () {
  'use strict';

  const trigger = document.getElementById('webTrigger');
  const nav     = document.getElementById('webNav');
  const close   = document.getElementById('webClose');

  function openNav() {
    nav.classList.add('open');
    document.body.style.overflow = 'hidden';
    nav.setAttribute('aria-hidden', 'false');
    close.focus();
  }

  function closeNav() {
    nav.classList.remove('open');
    document.body.style.overflow = '';
    nav.setAttribute('aria-hidden', 'true');
    trigger.focus();
  }

  trigger.addEventListener('click', openNav);
  close.addEventListener('click', closeNav);

  // Close on backdrop click (not on SVG/links)
  nav.addEventListener('click', function (e) {
    if (e.target === nav) closeNav();
  });

  // Close on Escape
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && nav.classList.contains('open')) closeNav();
  });

  // Close nav when a web link is clicked (smooth scroll to section)
  nav.querySelectorAll('.web-link').forEach(function (link) {
    link.addEventListener('click', function () {
      closeNav();
    });
  });

  // ── Intersection Observer: fade-up cards on scroll ──
  if ('IntersectionObserver' in window) {
    const items = document.querySelectorAll('.card, .section-title, .subscribe-band');

    // Reset initial state for scroll-triggered reveal
    items.forEach(function (el) {
      el.style.opacity = '0';
      el.style.transform = 'translateY(28px)';
      el.style.transition = 'opacity .55s ease, transform .55s ease';
      el.style.animationName = 'none'; // cancel CSS animation, use JS instead
    });

    const io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.style.opacity = '1';
          entry.target.style.transform = 'translateY(0)';
          io.unobserve(entry.target);
        }
      });
    }, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });

    items.forEach(function (el) { io.observe(el); });
  }

  // ── Web trigger button: spin web icon on hover ──
  const triggerSvg = trigger.querySelector('svg');
  let spinning = false;
  trigger.addEventListener('mouseenter', function () {
    if (spinning) return;
    spinning = true;
    let start = null;
    function step(ts) {
      if (!start) start = ts;
      const deg = ((ts - start) / 800) * 360;
      triggerSvg.style.transform = `rotate(${deg}deg)`;
      if (deg < 360) requestAnimationFrame(step);
      else {
        triggerSvg.style.transform = '';
        spinning = false;
      }
    }
    requestAnimationFrame(step);
  });

  // ── Subscribe form feedback ──
  const form  = document.querySelector('.sub-form');
  const input = document.querySelector('.sub-input');
  const btn   = document.querySelector('.sub-btn');

  if (form) {
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      const val = input.value.trim();
      if (!val || !val.includes('@')) {
        input.style.borderColor = '#e8001f';
        input.focus();
        return;
      }
      btn.textContent = 'CAUGHT! ✓';
      btn.style.background = '#1a7a3a';
      btn.style.boxShadow = '0 0 18px rgba(26,122,58,.5)';
      input.value = '';
      input.disabled = true;
      btn.disabled = true;
    });
    input.addEventListener('input', function () {
      input.style.borderColor = '';
    });
  }

})();
