/* 统一提示：同时最多一条，3 秒后自动消失。 */
(function () {
  function toast(type, message) {
    const root = document.getElementById('toast-root');
    if (!root) { return; }
    root.innerHTML = '';
    const box = document.createElement('div');
    box.className = 'toast toast--' + (type === 'success' ? 'success' : 'error');
    const text = document.createElement('span');
    text.className = 'toast__text';
    text.textContent = message;
    const close = document.createElement('button');
    close.type = 'button';
    close.className = 'toast__close';
    close.setAttribute('aria-label', '关闭提示');
    close.textContent = '×';
    close.addEventListener('click', () => box.remove());
    box.appendChild(text);
    box.appendChild(close);
    root.appendChild(box);
    window.setTimeout(() => box.remove(), 3000);
  }
  window.toast = toast;
})();
