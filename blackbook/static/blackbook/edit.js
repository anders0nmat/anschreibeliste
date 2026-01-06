const formCount = document.getElementById('id_steps-TOTAL_FORMS');
const stepFormHtml = (() => {
    const fragment = document.getElementById('step-template').content;
    const dummy = document.createElement('div');
    dummy.append(fragment);
    return dummy.innerHTML;
})();
function incForms() {
    formCount.value = (parseInt(formCount.value) + 1).toString();
}
function decForms() {
    formCount.value = (parseInt(formCount.value) - 1).toString();
}
/* Remove extra initial attachments */
/* These are no longer required as we can dynamically attach new ones */
document.querySelectorAll('tr:has([id^="id_steps-"][id$="-id"]:not([value]))').forEach(e => {
    e.remove();
    decForms();
});
const add_button = document.querySelector('#add-step');
function addStep() {
    const html = stepFormHtml.replaceAll('__prefix__', formCount.value);
    const dummy = document.createElement('tbody');
    dummy.innerHTML = html;
    const newElement = dummy.firstElementChild;
    registerHandlers(newElement);
    const rows = document.querySelector('#steps tbody');
    rows.append(newElement);
    incForms();
    updateOrder();
}
add_button.addEventListener('click', addStep);
document.querySelectorAll('tr[draggable]').forEach(registerHandlers);
const stepList = document.querySelector('#steps');
stepList?.addEventListener('dragover', ev => {
    if (ev.dataTransfer?.types.includes('recipe-step')) {
        ev.preventDefault();
        const dragged = document.getElementById('dragged-element');
        let placed = false;
        const tbody = stepList.tBodies[0];
        for (let e of tbody.rows) {
            if (e.id == 'dragged-element') {
                continue;
            }
            const middle = e.getBoundingClientRect().bottom - e.clientHeight / 2;
            if (middle > ev.clientY) {
                dragged.remove();
                e.insertAdjacentElement("beforebegin", dragged);
                placed = true;
                break;
            }
        }
        if (!placed) {
            dragged.remove();
            tbody.append(dragged);
        }
    }
});
stepList?.addEventListener('drop', ev => {
    ev.preventDefault();
    updateOrder();
});
function updateOrder() {
    stepList.querySelectorAll('input[id$="-order"]').forEach((e, idx) => {
        e.value = (idx + 1).toString();
    });
}
function registerHandlers(step) {
    step.addEventListener('dragstart', ev => {
        ev.dataTransfer.effectAllowed = "move";
        ev.dataTransfer.setData("recipe-step", "");
        step.id = 'dragged-element';
    });
    step.addEventListener('dragend', _ => step.removeAttribute('id'));
    step.querySelectorAll('[data-dir]').forEach(e => {
        e.addEventListener('click', _ => {
            let sibling = null;
            let insert = "beforebegin";
            if (e.dataset.dir == "up") {
                [sibling, insert] = [step.previousElementSibling, "beforebegin"];
            }
            else if (e.dataset.dir == "down") {
                [sibling, insert] = [step.nextElementSibling, "afterend"];
            }
            if (sibling && sibling.matches('tr[draggable]')) {
                step.remove();
                sibling.insertAdjacentElement(insert, step);
            }
            updateOrder();
        });
    });
}
