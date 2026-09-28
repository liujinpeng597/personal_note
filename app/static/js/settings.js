/* 设置页：资料与密码两张表单。 */
(function () {
  function clearErrors(form) {
    form.querySelectorAll('.field-error').forEach((el) => { el.hidden = true; el.textContent = ''; });
    form.querySelectorAll('.field.has-error').forEach((el) => el.classList.remove('has-error'));
  }

  function showErrors(form, fields) {
    Object.keys(fields || {}).forEach((name) => {
      const el = form.querySelector('#' + name + '-error');
      if (el) {
        el.textContent = fields[name];
        el.hidden = false;
        const wrapper = el.closest('.field');
        if (wrapper) { wrapper.classList.add('has-error'); }
      }
    });
  }

  document.querySelectorAll('form[data-settings-form]').forEach((form) => {
    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      const button = form.querySelector('button[type="submit"]');
      const original = button.textContent;
      clearErrors(form);
      button.disabled = true;
      button.textContent = form.dataset.loadingText || '保存中…';

      const data = Object.fromEntries(new FormData(form).entries());
      const result = await window.request(form.action, { method: 'POST', body: data });

      button.disabled = false;
      button.textContent = original;
      if (result.code !== 'OK') {
        showErrors(form, result.data && result.data.fields);
        return;
      }
      if (form.action.indexOf('password') !== -1) {
        form.reset();
      }
    });
  });
})();
