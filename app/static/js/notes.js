/* 收藏、删除、评论。 */
(function () {
  function setFavorite(button, data) {
    button.dataset.favorited = data.favorited ? 'true' : 'false';
    button.setAttribute('aria-pressed', data.favorited ? 'true' : 'false');
    button.setAttribute('aria-label', data.favorited ? '取消收藏' : '收藏这篇笔记');
    const count = button.querySelector('.favorite-btn__count');
    if (count) { count.textContent = data.count; }
  }

  function renderComment(comment, currentUserName) {
    const item = document.createElement('div');
    item.className = 'comment';
    item.dataset.commentId = comment.id;

    const head = document.createElement('div');
    head.className = 'comment__head';
    const name = document.createElement('strong');
    name.textContent = comment.user;
    const time = document.createElement('span');
    time.textContent = comment.created_at || '';
    head.appendChild(name);
    head.appendChild(time);
    if (currentUserName && comment.user === currentUserName) {
      const remove = document.createElement('button');
      remove.className = 'btn btn-sm btn-danger';
      remove.type = 'button';
      remove.dataset.commentDelete = comment.id;
      remove.textContent = '删除';
      head.appendChild(remove);
    }

    const body = document.createElement('p');
    body.className = 'comment__body';
    body.textContent = comment.content;

    item.appendChild(head);
    item.appendChild(body);
    return item;
  }

  document.addEventListener('click', async (event) => {
    const favorite = event.target.closest('.favorite-btn');
    if (favorite) {
      if (favorite.dataset.requiresLogin === 'true') {
        window.toast('error', '请先登录再收藏。');
        return;
      }
      const result = await window.request('/notes/' + favorite.dataset.noteId + '/favorite', { method: 'POST' });
      if (result.code === 'OK') { setFavorite(favorite, result.data); }
      return;
    }

    const deleteNote = event.target.closest('[data-note-delete]');
    if (deleteNote) {
      const confirmed = await window.confirmDialog(
        '删除后无法恢复，确定删除《' + deleteNote.dataset.noteTitle + '》吗？',
        { title: '删除笔记', confirmText: '删除' }
      );
      if (!confirmed) { return; }
      const result = await window.request('/notes/' + deleteNote.dataset.noteDelete, { method: 'DELETE' });
      if (result.code === 'OK') { window.location.href = '/notes'; }
      return;
    }

    const deleteComment = event.target.closest('[data-comment-delete]');
    if (deleteComment) {
      const confirmed = await window.confirmDialog('删除后无法恢复，确定删除这条评论吗？',
        { title: '删除评论', confirmText: '删除' });
      if (!confirmed) { return; }
      const result = await window.request('/comments/' + deleteComment.dataset.commentDelete, { method: 'DELETE' });
      if (result.code === 'OK') {
        const item = deleteComment.closest('.comment');
        if (item) { item.remove(); }
        const list = document.getElementById('comment-list');
        const empty = document.getElementById('comment-empty');
        if (empty && list && list.children.length === 0) { empty.hidden = false; }
      }
    }
  });

  const form = document.getElementById('comment-form');
  if (form) {
    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      const textarea = form.querySelector('#comment-content');
      const errorEl = form.querySelector('#content-error');
      if (errorEl) { errorEl.hidden = true; }
      const result = await window.request('/notes/' + form.dataset.noteId + '/comments', {
        method: 'POST',
        body: { content: textarea.value }
      });
      if (result.code === 'OK') {
        const list = document.getElementById('comment-list');
        const empty = document.getElementById('comment-empty');
        const nameEl = document.querySelector('.user-menu__name');
        list.appendChild(renderComment(result.data.comment, nameEl ? nameEl.textContent.trim() : null));
        if (empty) { empty.hidden = true; }
        textarea.value = '';
      } else if (result.data && result.data.fields && result.data.fields.content && errorEl) {
        errorEl.textContent = result.message;
        errorEl.hidden = false;
      }
    });
  }
})();
