/* Interactive tasklists */
const csrf_token = document.querySelector('input[name="csrfmiddlewaretoken"]').value;
document.querySelectorAll('.task-list-item > input[type="checkbox"]:first-of-type').forEach((e, index) => {
    e.disabled = false;
    e.addEventListener('change', _ => {
        const newState = e.checked;
        const data = new FormData();
        data.append('index', index.toString());
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
