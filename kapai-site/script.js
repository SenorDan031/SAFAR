// SAFAR Professional Website Interactive Script
document.addEventListener('DOMContentLoaded', () => {
  // 1. Mobile Navigation Toggle
  const menuToggle = document.getElementById('menuToggle');
  const mainNav = document.getElementById('mainNav');

  if (menuToggle && mainNav) {
    menuToggle.addEventListener('click', () => {
      const isVisible = mainNav.style.display === 'flex';
      mainNav.style.display = isVisible ? 'none' : 'flex';
      mainNav.style.flexDirection = 'column';
      mainNav.style.position = 'absolute';
      mainNav.style.top = '100%';
      mainNav.style.left = '0';
      mainNav.style.width = '100%';
      mainNav.style.background = 'rgba(6, 9, 14, 0.98)';
      mainNav.style.padding = '24px';
      mainNav.style.borderBottom = '1px solid rgba(255, 255, 255, 0.1)';
      mainNav.style.boxShadow = '0 10px 30px rgba(0, 0, 0, 0.8)';
    });
  }

  // 2. Smooth Scrolling for Anchor Links
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
      e.preventDefault();
      const targetId = this.getAttribute('href');
      if (targetId === '#') return;
      const targetEl = document.querySelector(targetId);
      if (targetEl) {
        if (window.innerWidth <= 768 && mainNav) {
          mainNav.style.display = 'none';
        }
        targetEl.scrollIntoView({
          behavior: 'smooth',
          block: 'start'
        });
      }
    });
  });

  // 3. Interactive HUD Telemetry Scenario Simulator
  const scenarioData = {
    clear: {
      lead: '#NONE',
      conf: 'NONE',
      confClass: 'text-muted',
      path: 'NONE',
      motion: 'UNKNOWN',
      decision: 'SAFE → CONTINUE',
      decClass: 'text-green',
      control: 'PLAYER_CONTROL (Brake: Released)',
      ctrlClass: 'text-green',
      boxStyle: { top: '30%', left: '45%', width: '0%', height: '0%', opacity: '0' },
      sideBoxStyle: { opacity: '0' },
      boxText: ''
    },
    side: {
      lead: '#NONE',
      conf: 'NONE',
      confClass: 'text-muted',
      path: 'LOW / NONE (Outside Corridor)',
      motion: 'STABLE',
      decision: 'SAFE → CONTINUE',
      decClass: 'text-green',
      control: 'PLAYER_CONTROL (Brake: Released)',
      ctrlClass: 'text-green',
      boxStyle: { opacity: '0' },
      sideBoxStyle: { top: '25%', left: '6%', width: '14%', height: '24%', opacity: '1' },
      boxText: ''
    },
    lead: {
      lead: '#image-2 car',
      conf: 'CONFIRMED',
      confClass: 'text-cyan',
      path: 'HIGH (Centered)',
      motion: 'STABLE',
      decision: 'MEDIUM → WARN',
      decClass: 'text-cyan',
      control: 'WARNING (No Control Override)',
      ctrlClass: 'text-cyan',
      boxStyle: { top: '22%', left: '44%', width: '12%', height: '20%', border: '2px solid #00e5ff', background: 'rgba(0, 229, 255, 0.12)', opacity: '1' },
      sideBoxStyle: { opacity: '0.4' },
      boxText: '#image-2 car [LEAD AHEAD]'
    },
    approaching: {
      lead: '#image-2 car',
      conf: 'HAZARD',
      confClass: 'text-yellow',
      path: 'HIGH',
      motion: 'APPROACHING',
      decision: 'HIGH → SLOWDOWN',
      decClass: 'text-yellow',
      control: 'SLOWDOWN_OVERRIDE (Light Brake)',
      ctrlClass: 'text-yellow',
      boxStyle: { top: '35%', left: '40%', width: '20%', height: '32%', border: '2px solid #ffd600', background: 'rgba(255, 214, 0, 0.15)', opacity: '1' },
      sideBoxStyle: { opacity: '0.2' },
      boxText: '#image-2 car [APPROACHING]'
    },
    cutin: {
      lead: '#image-5 truck',
      conf: 'HAZARD (Imminent)',
      confClass: 'text-red',
      path: 'HIGH (Direct Cut-In)',
      motion: 'APPROACHING',
      decision: 'CRITICAL → EMERGENCY_BRAKE',
      decClass: 'text-red',
      control: 'BRAKE_OVERRIDE (Strong Brake + Handbrake)',
      ctrlClass: 'text-red',
      boxStyle: { top: '42%', left: '36%', width: '28%', height: '42%', border: '2px solid #ff3d71', background: 'rgba(255, 61, 113, 0.22)', opacity: '1' },
      sideBoxStyle: { opacity: '0.1' },
      boxText: '#image-5 truck [IMMINENT CUT-IN]'
    }
  };

  const scenarioBtns = document.querySelectorAll('.scenario-btn');
  const tLead = document.getElementById('tLead');
  const tConf = document.getElementById('tConf');
  const tPath = document.getElementById('tPath');
  const tMotion = document.getElementById('tMotion');
  const tDecision = document.getElementById('tDecision');
  const tControl = document.getElementById('tControl');
  const viewportBox = document.getElementById('viewportBox');
  const viewportSideBox = document.getElementById('viewportSideBox');
  const boxBadge = document.getElementById('boxBadge');

  if (scenarioBtns.length > 0) {
    scenarioBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        scenarioBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');

        const scKey = btn.dataset.scenario;
        const data = scenarioData[scKey];
        if (!data) return;

        // Update Text & Classes
        tLead.textContent = data.lead;
        tConf.textContent = data.conf;
        tConf.className = `t-val ${data.confClass}`;
        tPath.textContent = data.path;
        tMotion.textContent = data.motion;
        tDecision.textContent = data.decision;
        tDecision.className = `t-val ${data.decClass}`;
        tControl.textContent = data.control;
        tControl.className = `t-val ${data.ctrlClass}`;

        // Update Viewport Boxes
        if (viewportBox) {
          Object.assign(viewportBox.style, data.boxStyle);
          boxBadge.textContent = data.boxText;
        }
        if (viewportSideBox) {
          Object.assign(viewportSideBox.style, data.sideBoxStyle);
        }
      });
    });
  }

  // 4. Live Subtle Telemetry Fluctuations (FPS / Latency)
  const liveFps = document.getElementById('liveFps');
  const liveLat = document.getElementById('liveLat');
  if (liveFps && liveLat) {
    setInterval(() => {
      liveFps.textContent = (29.6 + Math.random() * 1.2).toFixed(1);
      liveLat.textContent = (36.2 + Math.random() * 4.5).toFixed(1);
    }, 1600);
  }

  // 5. Scroll Reveal IntersectionObserver
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('reveal-active');
      }
    });
  }, {
    threshold: 0.08,
    rootMargin: '0px 0px -30px 0px'
  });

  document.querySelectorAll('.info-card, .achievement-card, .insight-row, .timeline-card, .team-profile-card, .exp-tier').forEach(el => {
    el.classList.add('reveal-item');
    observer.observe(el);
  });

  // Inject dynamic CSS for smooth reveal
  const style = document.createElement('style');
  style.innerHTML = `
    .reveal-item {
      opacity: 0;
      transform: translateY(22px);
      transition: opacity 0.55s cubic-bezier(0.16, 1, 0.3, 1), transform 0.55s cubic-bezier(0.16, 1, 0.3, 1);
    }
    .reveal-active {
      opacity: 1 !important;
      transform: translateY(0) !important;
    }
  `;
  document.head.appendChild(style);
});
