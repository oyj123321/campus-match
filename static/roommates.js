document.addEventListener('DOMContentLoaded', () => {
    const degree = document.querySelector('select[name="degree"]');
    const college = document.getElementById('college-field');
    const grad = document.getElementById('grad-note');
    const input = college ? college.querySelector('select, input') : null;
    const sync = () => {
        const graduate = degree && degree.value !== 'bachelor';
        if (college) college.hidden = graduate;
        if (grad) grad.hidden = !graduate;
        if (input) input.required = !graduate;
    };
    if (degree) degree.addEventListener('change', sync);
    sync();
});
