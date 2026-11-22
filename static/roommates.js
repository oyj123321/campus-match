document.addEventListener('DOMContentLoaded', () => {
    const field = document.getElementById('housing-field');
    const catalogNode = document.getElementById('housing-catalog');
    const degree = document.querySelector('[name="degree"]');
    const gender = document.querySelector('select[name="my_gender"]');
    const wrap = document.getElementById('housing-select-wrap');
    const select = document.getElementById('housing-select');
    const fixed = document.getElementById('housing-fixed');
    const fixedName = document.getElementById('housing-fixed-name');
    const free = document.getElementById('housing-free');
    const freeInput = free ? free.querySelector('input') : null;
    if (!field || !catalogNode || !degree || !select) return;
    const catalog = JSON.parse(catalogNode.textContent);

    const sync = () => {
        const who = (gender && gender.value) || field.dataset.gender || 'female';
        const list = ((catalog[who] || {})[degree.value]) || [];
        const previous = select.value;
        select.replaceChildren(new Option('请选择', ''));
        list.forEach((name) => select.append(new Option(name, name)));
        if (list.includes(previous)) select.value = previous;
        const choosing = list.length > 1;
        const locked = list.length === 1;
        wrap.hidden = !choosing;
        select.disabled = !choosing;
        select.required = choosing;
        fixed.hidden = !locked;
        if (fixedName) fixedName.textContent = locked ? list[0] : '';
        free.hidden = list.length !== 0;
        if (freeInput) freeInput.disabled = list.length !== 0;
    };
    degree.addEventListener('change', sync);
    if (gender) gender.addEventListener('change', sync);
    sync();
});
