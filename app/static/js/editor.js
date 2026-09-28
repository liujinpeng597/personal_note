/* 编辑器：预览防抖、存草稿、发布、脏数据提醒、插入图片、写作/预览切换。 */
(function () {
  const editor = document.getElementById('editor');
  if (!editor) { return; }

  const titleEl = document.getElementById('title');
  const tagsEl = document.getElementById('tags');
  const contentEl = document.getElementById('content-md');
  const previewEl = document.getElementById('preview');
  const previewStatus = document.getElementById('preview-status');
  const draftButton = document.getElementById('save-draft');
  const publishButton = document.getElementById('publish');
  const imageButton = document.getElementById('insert-image');
  const imageInput = document.getElementById('image-file');

  let noteId = (draftButton.dataset.noteId || '').trim() || null;
  let dirty = false;
  let previewTimer = null;

  function markDirty() { dirty = true; }

  [titleEl, tagsEl, contentEl].forEach((el) => {
    if (el) { el.addEventListener('input', markDirty); }
  });

  window.addEventListener('beforeunload', (event) => {
    if (!dirty) { return; }
    event.preventDefault();
    event.returnValue = '';
  });

  // ---- 预览 ----
  async function refreshPreview() {
    if (!contentEl) { return; }
    previewStatus.textContent = '正在渲染…';
    const result = await window.request('/api/preview', { method: 'POST', body: { content_md: contentEl.value } });
    if (result.code === 'OK') {
      previewEl.innerHTML = result.data.html || '<p class="text-meta">（还没有内容）</p>';
    }
    previewStatus.textContent = '';
  }

  if (contentEl) {
    contentEl.addEventListener('input', () => {
      window.clearTimeout(previewTimer);
      previewTimer = window.setTimeout(refreshPreview, 300);
    });
    if (contentEl.value.trim()) { refreshPreview(); }
  }

  // ---- 写作 / 预览切换（窄屏） ----
  document.querySelectorAll('[data-mode-btn]').forEach((button) => {
    button.addEventListener('click', () => {
      editor.dataset.mode = button.dataset.modeBtn;
      document.querySelectorAll('[data-mode-btn]').forEach((other) => {
        other.setAttribute('aria-pressed', other === button ? 'true' : 'false');
      });
    });
  });

  // ---- 保存 ----
  function payload() {
    return {
      title: titleEl.value,
      content_md: contentEl.value,
      tags: tagsEl ? tagsEl.value : ''
    };
  }

  function showFields(fields) {
    document.querySelectorAll('.field-error').forEach((el) => { el.hidden = true; });
    Object.keys(fields || {}).forEach((name) => {
      const el = document.getElementById(name + '-error');
      if (el) { el.textContent = fields[name]; el.hidden = false; }
    });
  }

  async function save(asDraft) {
    const button = asDraft ? draftButton : publishButton;
    const original = button.textContent;
    button.disabled = true;
    button.textContent = asDraft ? '保存中…' : '发布中…';

    let result;
    if (asDraft) {
      result = noteId
        ? await window.request('/notes/' + noteId, { method: 'PUT', body: payload() })
        : await window.request('/notes', { method: 'POST', body: payload() });
      if (result.code === 'OK') {
        noteId = String(result.data.id);
        draftButton.dataset.noteId = noteId;
        publishButton.dataset.noteId = noteId;
        dirty = false;
        window.history.replaceState({}, '', '/notes/' + noteId + '/edit');
        button.textContent = '已保存';
        window.setTimeout(() => { button.textContent = original; }, 1200);
        return;
      }
    } else {
      if (!noteId) {
        const created = await window.request('/notes', { method: 'POST', body: payload() });
        if (created.code !== 'OK') {
          showFields(created.data && created.data.fields);
          button.disabled = false; button.textContent = original;
          return;
        }
        noteId = String(created.data.id);
        draftButton.dataset.noteId = noteId;
        publishButton.dataset.noteId = noteId;
      }
      result = await window.request('/notes/' + noteId + '/publish', { method: 'POST', body: payload() });
      if (result.code === 'OK') {
        dirty = false;
        window.location.href = result.data.url;
        return;
      }
    }

    showFields(result.data && result.data.fields);
    button.disabled = false;
    button.textContent = original;
  }

  if (draftButton) { draftButton.addEventListener('click', () => save(true)); }
  if (publishButton) { publishButton.addEventListener('click', () => save(false)); }

  // ---- 插入图片 ----
  if (imageButton && imageInput) {
    imageButton.addEventListener('click', () => imageInput.click());
    imageInput.addEventListener('change', async () => {
      const file = imageInput.files[0];
      if (!file) { return; }
      const original = imageButton.textContent;
      imageButton.disabled = true;
      imageButton.textContent = '上传中…';

      const body = new FormData();
      body.append('file', file);
      const meta = document.querySelector('meta[name="csrf-token"]');
      let result;
      try {
        const response = await fetch('/api/upload', {
          method: 'POST',
          headers: meta ? { 'X-CSRF-Token': meta.content } : {},
          body: body
        });
        result = await response.json();
      } catch (err) {
        result = { code: 'ERR_NETWORK', message: '网络异常，请检查连接后重试', data: {} };
      }
      imageButton.disabled = false;
      imageButton.textContent = original;
      imageInput.value = '';

      if (result.code === 'OK') {
        const markdown = '![图片](' + result.data.url + ')';
        const start = contentEl.selectionStart || 0;
        contentEl.value = contentEl.value.slice(0, start) + markdown + contentEl.value.slice(start);
        markDirty();
        refreshPreview();
        window.toast('success', '图片已上传');
      } else {
        window.toast('error', result.message);
      }
    });
  }
})();
