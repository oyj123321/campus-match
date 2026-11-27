document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('form.community-filters').forEach((form) => {
        form.classList.add('is-live');
        form.addEventListener('change', () => form.requestSubmit());
    });
    const flex = document.querySelector('input[name="flexible"]');
    const ongoing = document.querySelector('input[name="ongoing"]');
    const start = document.querySelector('input[name="starts_at"]');
    const audience = document.querySelector('select[name="audience"]');
    const mine = document.querySelector('#my-gender-field');
    const mineSelect = mine ? mine.querySelector('select') : null;
    const syncTime = () => {
        if (!start) return;
        const skip = (ongoing && ongoing.checked) || (flex && flex.checked);
        start.disabled = skip;
        start.required = !skip;
        if (skip) start.value = '';
    };
    const syncGender = () => {
        if (!audience || !mine || !mineSelect) return;
        const limited = audience.value === 'male' || audience.value === 'female';
        mine.hidden = !limited;
        mineSelect.required = limited;
        if (!limited) mineSelect.value = '';
    };
    if (flex) flex.addEventListener('change', () => {
        if (flex.checked && ongoing) ongoing.checked = false;
        syncTime();
    });
    if (ongoing) ongoing.addEventListener('change', () => {
        if (ongoing.checked && flex) flex.checked = false;
        syncTime();
    });
    if (audience) audience.addEventListener('change', syncGender);
    syncTime();
    syncGender();
});

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
            if (kind === 'save') {
                const key = data.enabled ? 'cm.unsave' : 'cm.save';
                button.setAttribute('data-i18n', key);
                button.textContent = window.t ? window.t(key) : (data.enabled ? '取消收藏' : '收藏');
            } else {
                button.textContent = (data.enabled ? '取消' : '') + '赞 · ' + data.likes;
            }
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
