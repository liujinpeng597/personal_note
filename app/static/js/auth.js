/* 注册 / 登录表单：统一信封提示 + 字段级错误。 */
(function () {
  function clearErrors(form) {
    form.querySelectorAll('.field-error').forEach((el) => {
      el.hidden = true;
      el.textContent = '';
    });
    form.querySelectorAll('.field.has-error').forEach((el) => el.classList.remove('has-error'));
  }

  function showFieldErrors(form, fields) {
    Object.keys(fields).forEach((name) => {
      const errorEl = form.querySelector('#' + name + '-error');
      if (errorEl) {
        errorEl.textContent = fields[name];
        errorEl.hidden = false;
        const wrapper = errorEl.closest('.field');
        if (wrapper) { wrapper.classList.add('has-error'); }
      }
    });
  }

  async function submitAuth(form) {
    const button = form.querySelector('button[type="submit"]');
    const original = button.textContent;
    clearErrors(form);
    button.disabled = true;
    button.textContent = form.dataset.loadingText || '提交中…';

    const data = Object.fromEntries(new FormData(form).entries());
    const target = (data.next && data.next.indexOf('/') === 0) ? data.next : null;
    const result = await window.request(form.action, { method: 'POST', body: data });

    button.disabled = false;
    button.textContent = original;

    if (result.code === 'OK') {
      window.location.href = target || (result.data && result.data.redirect) || form.dataset.successUrl;
      return;
    }
    const fields = (result.data && result.data.fields) || {};
    showFieldErrors(form, fields);
    if (Object.keys(fields).length === 0) {
      const first = form.querySelector('input');
      if (first) { first.focus(); }
    }
  }

  document.querySelectorAll('form[data-auth-form]').forEach((form) => {
    form.addEventListener('submit', (event) => {
      event.preventDefault();
      submitAuth(form);
    });
  });
})();
