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
document.querySelectorAll('li:has([id^="id_steps-"][id$="-id"]:not([value]))').forEach(e => {
    e.remove();
    decForms();
});
const add_button = document.querySelector('#add-step');
function addStep() {
    const html = stepFormHtml.replaceAll('__prefix__', formCount.value);
    const dummy = document.createElement('div');
    dummy.innerHTML = html;
    const newElement = dummy.firstElementChild;
    newElement.addEventListener('dragstart', ev => {
        ev.dataTransfer.effectAllowed = "move";
        ev.dataTransfer.setData("recipe-step", "");
        newElement.id = 'dragged-element';
    });
    newElement.addEventListener('dragend', _ => {
        newElement.removeAttribute('id');
    });
    const lastStepOrder = Array.from(add_button.parentElement.querySelectorAll('li[draggable] input[id$="-order"]')).at(-1);
    if (lastStepOrder !== undefined) {
        newElement.querySelector('input[id$="-order"]').value = (parseInt(lastStepOrder.value) + 1).toString();
    }
    add_button.insertAdjacentElement("beforebegin", newElement);
    incForms();
}
add_button.addEventListener('click', addStep);
document.querySelectorAll('ol > li').forEach(e => {
    e.addEventListener('dragstart', ev => {
        ev.dataTransfer.effectAllowed = "move";
        ev.dataTransfer.setData("recipe-step", "");
        e.id = 'dragged-element';
        //document.querySelector<HTMLElement>('.drag-placeholder')!.style.height = e.clientHeight.toString() + 'px'
        //placePlaceholder(ev)
    });
    e.addEventListener('dragend', _ => {
        e.removeAttribute('id');
    });
});
const stepList = document.querySelector('#steps');
function placePlaceholder(event) {
    const placeholder = stepList.querySelector('.drag-placeholder');
    let placed = false;
    for (let e of stepList.querySelectorAll(':scope > li[draggable]')) {
        const middle = e.getBoundingClientRect().bottom - e.clientHeight / 2;
        if (middle > event.clientY) {
            placeholder.remove();
            e.insertAdjacentElement("beforebegin", placeholder);
            placed = true;
            break;
        }
    }
    if (!placed) {
        placeholder.remove();
        stepList.querySelector(':scope > li[draggable]:last-of-type')?.insertAdjacentElement("afterend", placeholder);
    }
}
stepList?.addEventListener('dragover', ev => {
    if (ev.dataTransfer?.types.includes('recipe-step')) {
        ev.preventDefault();
        //placePlaceholder(ev)
        //const placeholder = stepList.querySelector<HTMLElement>('.drag-placeholder')!
        const dragged = document.getElementById('dragged-element');
        let placed = false;
        const fixedItems = Array.from(stepList.querySelectorAll(':scope > li[draggable]:not(#dragged-element)'));
        for (let e of fixedItems) {
            const middle = e.getBoundingClientRect().bottom - e.clientHeight / 2;
            if (middle > ev.clientY) {
                //placeholder.remove()
                //e.insertAdjacentElement("beforebegin", placeholder)
                dragged.remove();
                e.insertAdjacentElement("beforebegin", dragged);
                placed = true;
                break;
            }
        }
        if (!placed) {
            //placeholder.remove()
            //stepList.querySelector(':scope > li[draggable]:last-of-type')?.insertAdjacentElement("afterend", placeholder)
            dragged.remove();
            fixedItems.at(-1)?.insertAdjacentElement("afterend", dragged);
        }
    }
});
stepList?.addEventListener('drop', ev => {
    ev.preventDefault();
    /*
    const draggedElement = document.getElementById('dragged-element')!
    const placeholder = stepList.querySelector<HTMLElement>('.drag-placeholder')!
    draggedElement?.remove()
    placeholder.replaceWith(draggedElement)
    stepList.querySelector<HTMLElement>(':scope > li[draggable]')?.insertAdjacentElement("beforebegin", placeholder)
    */
    let i = 1;
    for (let e of stepList.querySelectorAll('li[draggable]')) {
        e.querySelector('input[id$="-order"]').value = i.toString();
        i += 1;
    }
});
