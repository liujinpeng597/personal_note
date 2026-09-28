/* 统一 fetch 封装：自动带 CSRF、统一信封、网络异常提示。 */
(function () {
  async function request(url, options) {
    const opts = options || {};
    const method = opts.method || 'GET';
    const headers = { 'Accept': 'application/json' };
    if (opts.body !== undefined && opts.body !== null) {
      headers['Content-Type'] = 'application/json';
    }
    const meta = document.querySelector('meta[name="csrf-token"]');
    if (meta && method !== 'GET') {
      headers['X-CSRF-Token'] = meta.content;
    }
    if (opts.headers) {
      Object.assign(headers, opts.headers);
    }

    let response;
    try {
      response = await fetch(url, {
        method: method,
        headers: headers,
        body: (opts.body === undefined || opts.body === null) ? null : JSON.stringify(opts.body)
      });
    } catch (err) {
      window.toast('error', '网络异常，请检查连接后重试');
      return { code: 'ERR_NETWORK', message: '网络异常，请检查连接后重试', data: {} };
    }

    let payload = null;
    try {
      payload = await response.json();
    } catch (err) {
      payload = null;
    }
    if (!payload || !payload.message) {
      payload = { code: 'ERR_SERVER', message: '服务器开小差了，请稍后再试', data: {} };
    }
    if (method !== 'GET' || response.status >= 400) {
      window.toast(payload.code === 'OK' ? 'success' : 'error', payload.message);
    }
    return payload;
  }

  window.request = request;
})();
