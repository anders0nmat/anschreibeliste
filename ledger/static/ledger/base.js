function _applyClassList(element, classes) {
    if (!Array.isArray(classes)) {
        classes = [classes];
    }
    classes.forEach(e => { if (typeof e === "string") {
        element.classList.add(e);
    } });
}
function _applyAttributes(element, attributes) {
    Object.entries(attributes).forEach(([k, v]) => {
        if (typeof v === "string") {
            element.setAttribute(k, v);
        }
        else {
            element.toggleAttribute(k, v);
        }
    });
}
export function _span(textContent, classList = [], attributes = {}) {
    const span = document.createElement("span");
    _applyClassList(span, classList);
    _applyAttributes(span, attributes);
    span.textContent = textContent;
    return span;
}
export function _money(balance) {
    const amount_string = Math.abs(balance).toString().padStart(3, '0');
    const money = _span('', ['money'], { negative: balance < 0 });
    const wholes = _span(amount_string.slice(0, -2), 'wholes');
    const cents = _span(amount_string.slice(-2), 'cents');
    money.append(wholes, cents);
    return money;
}
export function _cloneTemplate(id) {
    const template = document.getElementById(id);
    return template.content.cloneNode(true);
}
