document.addEventListener('submit', async (event) => {
    const form = event.target;
    if (!form.matches('form[data-community-action]')) return;
    event.preventDefault();
    if (form.dataset.busy) return;
    const button = form.querySelector('button[type="submit"]');
    let status = form.querySelector('[role="status"]');
    if (!status) {
        status = document.createElement('span');
        status.setAttribute('role', 'status');
        form.append(status);
    }
    status.textContent = '';
    form.dataset.busy = '1';
    button.disabled = true;
    form.setAttribute('aria-busy', 'true');
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 15000);
    try {
        const response = await fetch(form.action, {
            method: 'POST', body: new FormData(form),
            headers: {Accept: 'application/json'}, signal: controller.signal
        });
        if (!response.headers.get('content-type')?.includes('application/json')) {
            throw new Error('暂时无法确认结果，请稍后重试。');
        }
        const data = await response.json();
        if (!response.ok) throw new Error(data.message || '操作失败，请稍后重试。');
        if (form.dataset.communityAction === 'reaction') {
            const kind = form.elements.kind.value;
            form.elements.enabled.value = data.enabled ? '0' : '1';
            button.textContent = (data.enabled ? '取消' : '') +
                (kind === 'like' ? '赞 · ' + data.likes : '收藏');
            button.setAttribute('aria-pressed', String(data.enabled));
        } else {
            status.textContent = data.message;
            form.reset();
        }
    } catch (error) {
        status.textContent = error.name === 'AbortError' ?
            '请求超时，结果尚未确认，请稍后重试。' :
            (error instanceof TypeError ? '网络连接失败，请检查网络后重试。' : error.message);
    } finally {
        clearTimeout(timeout);
        delete form.dataset.busy;
        button.disabled = false;
        form.removeAttribute('aria-busy');
    }
});
