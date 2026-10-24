(function () {
  function hardReloadApp() {
    try {
      const url = new URL(window.location.href);
      url.searchParams.set('_reload', String(Date.now()));
      window.location.replace(url.toString());
    } catch (_) {
      window.location.reload();
    }
  }

  document.getElementById('desktopReloadBtn')?.addEventListener('click', () => {
    hardReloadApp();
  });

  function bindChatToggles() {
    const dock = document.getElementById('globalCodexDock');
    if (!dock) return;
    const toggle = () => {
      const isOpen = dock.classList.contains('open');
      dock.classList.toggle('open', !isOpen);
      document.body.classList.toggle('global-chat-open', !isOpen);
      try { localStorage.setItem('cofi-global-chat-open', !isOpen ? '1' : '0'); } catch (_) {}
      if (!isOpen) {
        document.getElementById('globalCodexInput')?.focus();
      }
    };
    const close = () => {
      dock.classList.remove('open');
      document.body.classList.remove('global-chat-open');
      try { localStorage.setItem('cofi-global-chat-open', '0'); } catch (_) {}
    };

    document.getElementById('globalCodexToggle')?.addEventListener('click', (e) => { e.preventDefault(); toggle(); });
    document.getElementById('sidebarChatToggleBtn')?.addEventListener('click', (e) => { e.preventDefault(); toggle(); });
    document.getElementById('desktopChatToggleBtn')?.addEventListener('click', (e) => { e.preventDefault(); toggle(); });
    document.querySelectorAll('[data-toggle-global-chat]').forEach(b => b.addEventListener('click', (e) => { e.preventDefault(); toggle(); }));
    document.getElementById('globalCodexCloseBtn')?.addEventListener('click', (e) => { e.preventDefault(); close(); });
    document.getElementById('globalCodexMinimizeBtn')?.addEventListener('click', (e) => { e.preventDefault(); close(); });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bindChatToggles);
  } else {
    bindChatToggles();
  }

  function activate() {
    const controls = window.pywebview?.api;
    if (!controls || document.body.classList.contains('desktop-mode')) return;
    document.body.classList.add('desktop-mode');
    document.getElementById('desktopMinimizeBtn').addEventListener('click', () => controls.minimize());
    document.getElementById('desktopMaximizeBtn').addEventListener('click', async () => {
      const maximized = await controls.toggle_maximize();
      const button = document.getElementById('desktopMaximizeBtn');
      button.textContent = maximized ? '❐' : '□';
      button.setAttribute('aria-label', maximized ? 'Khôi phục cửa sổ' : 'Phóng to cửa sổ');
    });
    document.getElementById('desktopCloseBtn').addEventListener('click', () => controls.close());
  }

  // Handle F5 and Ctrl+R keyboard shortcuts across the desktop window
  window.addEventListener('keydown', (e) => {
    if (e.key === 'F5' || (e.ctrlKey && (e.key === 'r' || e.key === 'R'))) {
      e.preventDefault();
      hardReloadApp();
    }
  });

  window.addEventListener('pywebviewready', activate);
  if (window.pywebview?.api) activate();
})();
