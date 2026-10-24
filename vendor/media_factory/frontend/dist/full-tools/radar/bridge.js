(() => {
  const nativeFetch = window.fetch.bind(window);
  const prefix = '/api/integrations/radar';

  const rewriteUrl = (value) => {
    if (typeof value !== 'string') return value;
    if (value.startsWith('/api/')) return `${prefix}${value}`;
    return value;
  };

  window.fetch = (input, init) => {
    if (input instanceof Request) {
      const url = new URL(input.url, window.location.origin);
      if (url.origin === window.location.origin && url.pathname.startsWith('/api/')) {
        const next = `${prefix}${url.pathname}${url.search}`;
        return nativeFetch(new Request(next, input), init);
      }
      return nativeFetch(input, init);
    }
    return nativeFetch(rewriteUrl(input), init);
  };

  window.__COFI_STUDIO_FULL_TOOL__ = { id: 'radar', version: 1 };
})();
