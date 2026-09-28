/* 移动端导航抽屉与头像菜单。 */
(function () {
  const toggle = document.querySelector('.nav-toggle');
  const nav = document.getElementById('site-nav');
  if (toggle && nav) {
    toggle.addEventListener('click', () => {
      const open = nav.classList.toggle('is-open');
      toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
      document.body.classList.toggle('no-scroll', open);
    });
  }

  const trigger = document.querySelector('.user-menu__trigger');
  const panel = document.querySelector('.user-menu__panel');
  if (trigger && panel) {
    const close = () => {
      panel.hidden = true;
      trigger.setAttribute('aria-expanded', 'false');
    };
    trigger.addEventListener('click', (event) => {
      event.stopPropagation();
      const willOpen = panel.hidden;
      panel.hidden = !willOpen;
      trigger.setAttribute('aria-expanded', willOpen ? 'true' : 'false');
    });
    document.addEventListener('click', (event) => {
      if (!panel.hidden && !panel.contains(event.target)) { close(); }
    });
    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape' && !panel.hidden) {
        close();
        trigger.focus();
      }
    });
  }
})();
