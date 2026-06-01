import { debounce } from "./base.js";
document.querySelectorAll('[data-action]').forEach(button => {
    switch (button.dataset.action) {
        case 'select-all':
        case 'select-none':
        case 'select-invert':
            const checkboxes = button.closest('details')?.querySelectorAll('input[type="checkbox"]');
            const nextValueCallbacks = {
                'select-all': () => true,
                'select-none': () => false,
                'select-invert': (cb) => !cb.checked,
            };
            const nextValue = nextValueCallbacks[button.dataset.action];
            button.addEventListener('click', _ => {
                checkboxes?.forEach(cb => {
                    const prevValue = cb.checked;
                    cb.checked = nextValue?.(cb) ?? false;
                    if (prevValue != cb.checked) {
                        cb.dispatchEvent(new Event('input'));
                    }
                });
            });
            break;
        case 'input-clear':
            const adjacentInput = button.parentElement?.querySelector('input');
            button.addEventListener('click', _ => {
                adjacentInput.value = '';
                adjacentInput.dispatchEvent(new Event('input'));
            });
            break;
    }
});
function getElements(formElement, names) {
    return Array.from(formElement.elements)
        .filter((item) => names.includes(item.name));
}
let updateCount = 0;
const updateTable = debounce(async () => {
    updateCount += 1;
    const thisUpdateCount = updateCount;
    const formData = new FormData(filterForm);
    const searchParams = new URLSearchParams();
    formData.forEach((value, key) => {
        if (value !== '') {
            searchParams.append(key, value.toString());
        }
    });
    const response = await fetch('./results/?' + searchParams.toString());
    if (!response.ok) {
        return;
    }
    const response_html = await response.text();
    if (updateCount != thisUpdateCount) {
        return;
    }
    const parser = new DOMParser();
    const doc = parser.parseFromString('<table>' + response_html + "</table>", "text/html");
    const newTable = doc.querySelector("tbody");
    tableBody.innerHTML = newTable.innerHTML;
    const newResult = doc.querySelector("#result-count");
    resultCount.innerHTML = newResult.innerHTML;
    const pagination = doc.querySelector(".pagination");
    document.querySelectorAll(".pagination").forEach(e => e.innerHTML = pagination.innerHTML);
    window.history.replaceState(null, "", window.location.origin + window.location.pathname + '?' + searchParams.toString());
}, 250);
const filterForm = document.getElementById('filters');
const tableBody = document.querySelector('tbody');
const resultCount = document.getElementById('result-count');
const formInputs = getElements(filterForm, [
    "account",
    "type",
    "start",
    "end",
    "hide_reverted",
]);
formInputs.forEach(element => element.addEventListener('input', _ => updateTable()));
