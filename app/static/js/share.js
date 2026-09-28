/* 分享弹窗与密码解锁。 */
(function () {
  const unlockForm = document.querySelector('[data-unlock-form]');
  if (unlockForm) {
    unlockForm.addEventListener('submit', async (event) => {
      event.preventDefault();
      const errorEl = unlockForm.querySelector('#password-error');
      if (errorEl) { errorEl.hidden = true; }
      const data = Object.fromEntries(new FormData(unlockForm).entries());
      const result = await window.request(unlockForm.action, { method: 'POST', body: data });
      if (result.code === 'OK') {
        window.location.href = (result.data && result.data.redirect) || window.location.href;
      } else if (errorEl) {
        errorEl.textContent = result.message;
        errorEl.hidden = false;
        const input = unlockForm.querySelector('#password');
        if (input) { input.value = ''; input.focus(); }
      }
    });
  }

  const openButton = document.getElementById('share-open');
  const dialog = document.getElementById('share-dialog');
  if (!openButton || !dialog) { return; }

  const statusEl = document.getElementById('share-status');
  const formEl = document.getElementById('share-form');
  const resultEl = document.getElementById('share-result');
  const urlInput = document.getElementById('share-url');
  const passwordInput = document.getElementById('share-password');
  const copyButton = document.getElementById('share-copy');

  function render() {
    const url = openButton.dataset.shareUrl || '';
    if (url) {
      statusEl.textContent = openButton.dataset.hasPassword === 'true' ? '已分享（有密码）' : '已分享（无密码）';
      formEl.hidden = true;
      resultEl.hidden = false;
      urlInput.value = url;
    } else {
      statusEl.textContent = '未分享';
      formEl.hidden = false;
      resultEl.hidden = true;
      urlInput.value = '';
    }
  }

  openButton.addEventListener('click', () => {
    render();
    window.openDialog(dialog, openButton);
  });

  document.getElementById('share-generate').addEventListener('click', async () => {
    const errorEl = document.getElementById('password-error');
    if (errorEl) { errorEl.hidden = true; }
    const result = await window.request('/notes/' + openButton.dataset.noteId + '/share', {
      method: 'POST',
      body: { password: passwordInput.value }
    });
    if (result.code === 'OK') {
      const url = result.data.url.indexOf('http') === 0 ? result.data.url : window.location.origin + result.data.url;
      openButton.dataset.shareUrl = url;
      openButton.dataset.hasPassword = result.data.has_password ? 'true' : 'false';
      render();
    } else if (errorEl) {
      errorEl.textContent = result.message;
      errorEl.hidden = false;
    }
  });

  copyButton.addEventListener('click', async () => {
    try {
      await navigator.clipboard.writeText(urlInput.value);
      copyButton.textContent = '已复制';
    } catch (err) {
      urlInput.select();
      document.execCommand('copy');
      copyButton.textContent = '已复制';
    }
    window.setTimeout(() => { copyButton.textContent = '复制'; }, 2000);
  });

  document.getElementById('share-revoke').addEventListener('click', async () => {
    const confirmed = await window.confirmDialog('取消后，这个链接会立刻失效。确定取消分享吗？',
      { title: '取消分享', confirmText: '取消分享' });
    if (!confirmed) { return; }
    const result = await window.request('/notes/' + openButton.dataset.noteId + '/share', { method: 'DELETE' });
    if (result.code === 'OK') {
      openButton.dataset.shareUrl = '';
      openButton.dataset.hasPassword = 'false';
      render();
    }
  });
})();
