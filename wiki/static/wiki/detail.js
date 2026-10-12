"use strict";
/* Interactive tasklists */
const csrf_token = document.querySelector('input[name="csrfmiddlewaretoken"]').value;
document.querySelectorAll('.task-list-item > input[type="checkbox"][data-line]').forEach(e => {
    e.addEventListener('change', _ => {
        const newState = e.checked;
        const data = new FormData();
        data.append('line', e.dataset.line ?? '');
        data.append('value', newState ? 'true' : 'false');
        fetch('taskitem/', {
            method: 'POST',
            body: data,
            headers: {
                "X-CSRFToken": csrf_token,
            }
        });
    });
});
const checklist_clear = document.querySelector('#clear-checklist').content.firstElementChild;
document.querySelectorAll('.task-list').forEach(e => {
    const btn = checklist_clear.cloneNode(true);
    btn.addEventListener('click', _ => {
        const linenos = [];
        e.querySelectorAll('input[type="checkbox"]:not([disabled])').forEach(cb => {
            cb.checked = false;
            linenos.push(cb.dataset.line ?? '');
        });
        const newState = false;
        const data = new FormData();
        linenos.forEach(e => data.append('line', e));
        data.append('value', newState ? 'true' : 'false');
        fetch('taskitem/', {
            method: 'POST',
            body: data,
            headers: {
                "X-CSRFToken": csrf_token,
            }
        });
    });
    e.insertAdjacentElement("afterbegin", btn);
});
