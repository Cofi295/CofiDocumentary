(() => {
  const nativeFetch = window.fetch.bind(window);
  const prefix = '/api/integrations/voice';

  const rewriteUrl = (value) => {
    if (typeof value !== 'string') return value;
    if (value.startsWith('/api/')) return `${prefix}${value}`;
    if (value.startsWith('/static/')) return `${prefix}${value}`;
    return value;
  };

  window.fetch = (input, init) => {
    if (input instanceof Request) {
      const url = new URL(input.url, window.location.origin);
      if (url.origin === window.location.origin && (url.pathname.startsWith('/api/') || url.pathname.startsWith('/static/'))) {
        const next = `${prefix}${url.pathname}${url.search}`;
        return nativeFetch(new Request(next, input), init);
      }
      return nativeFetch(input, init);
    }
    return nativeFetch(rewriteUrl(input), init);
  };

  document.addEventListener('click', (event) => {
    const anchor = event.target instanceof Element ? event.target.closest('a[href]') : null;
    if (!anchor) return;
    const href = anchor.getAttribute('href');
    const next = rewriteUrl(href);
    if (typeof next === 'string' && next !== href) anchor.setAttribute('href', next);
  }, true);

  window.__COFI_STUDIO_FULL_TOOL__ = { id: 'voice', version: 1 };
})();
