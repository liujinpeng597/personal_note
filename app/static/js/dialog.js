/* 弹窗与二次确认。 */
(function () {
  let lastTrigger = null;

  function openDialog(dialog, trigger) {
    if (!dialog) { return; }
    lastTrigger = trigger || null;
    dialog.hidden = false;
    document.body.classList.add('no-scroll');
    const target = dialog.querySelector('[data-autofocus]') || dialog.querySelector('button, input, a');
    if (target) { target.focus(); }
  }

  function closeDialog(dialog) {
    if (!dialog) { return; }
    dialog.hidden = true;
    document.body.classList.remove('no-scroll');
    if (lastTrigger && document.body.contains(lastTrigger)) { lastTrigger.focus(); }
  }

  function confirmDialog(message, options) {
    const opts = options || {};
    return new Promise((resolve) => {
      const wrapper = document.createElement('div');
      wrapper.className = 'dialog';
      wrapper.innerHTML =
        '<div class="dialog__panel" role="dialog" aria-modal="true" aria-labelledby="confirm-title">' +
        '<h2 id="confirm-title"></h2><p id="confirm-message"></p>' +
        '<div class="dialog__actions">' +
        '<button class="btn" type="button" data-confirm="no" data-autofocus></button>' +
        '<button class="btn btn-danger" type="button" data-confirm="yes"></button>' +
        '</div></div>';

      wrapper.querySelector('#confirm-title').textContent = opts.title || '请确认';
      wrapper.querySelector('#confirm-message').textContent = message;
      wrapper.querySelector('[data-confirm="no"]').textContent = opts.cancelText || '取消';
      wrapper.querySelector('[data-confirm="yes"]').textContent = opts.confirmText || '确定';

      function finish(value) {
        wrapper.remove();
        document.body.classList.remove('no-scroll');
        resolve(value);
      }

      wrapper.querySelector('[data-confirm="no"]').addEventListener('click', () => finish(false));
      wrapper.querySelector('[data-confirm="yes"]').addEventListener('click', () => finish(true));
      wrapper.addEventListener('click', (event) => { if (event.target === wrapper) { finish(false); } });
      document.addEventListener('keydown', function onKey(event) {
        if (event.key === 'Escape') {
          document.removeEventListener('keydown', onKey);
          finish(false);
        }
      });

      document.body.appendChild(wrapper);
      document.body.classList.add('no-scroll');
      const first = wrapper.querySelector('[data-autofocus]');
      if (first) { first.focus(); }
    });
  }

  document.addEventListener('click', (event) => {
    const closer = event.target.closest('[data-dialog-close]');
    if (closer) {
      closeDialog(closer.closest('.dialog'));
    }
  });

  document.addEventListener('keydown', (event) => {
    if (event.key !== 'Escape') { return; }
    document.querySelectorAll('.dialog:not([hidden])').forEach((dialog) => closeDialog(dialog));
  });

  window.openDialog = openDialog;
  window.closeDialog = closeDialog;
  window.confirmDialog = confirmDialog;
})();
