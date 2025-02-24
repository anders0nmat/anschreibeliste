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
export function _set_money(element, amount) {
    element.toggleAttribute('negative', amount < 0);
    const amount_string = Math.abs(amount).toString().padStart(3, '0');
    element.querySelector('.wholes').textContent = amount_string.slice(0, -2);
    element.querySelector('.cents').textContent = amount_string.slice(-2);
}
export function _cloneTemplate(id) {
    const template = document.getElementById(id);
    return template.content.cloneNode(true);
}
export class HTMLWrapper {
    static from(element) {
        return element !== null ? new this(element) : null;
    }
    static template;
    static create() {
        const element = _cloneTemplate(this.template).firstElementChild;
        return new this(element);
    }
    static all_selector;
    static all() {
        return Array.from(document.querySelectorAll(this.all_selector)).map(e => new this(e));
    }
    static get(selector) {
        const element = document.querySelector(selector);
        return element !== null ? new this(element) : null;
    }
    element;
    constructor(element) {
        this.element = element;
    }
}
export class HTMLIdentifierWrapper extends HTMLWrapper {
    static id_attribute;
    static byId(id) {
        return id !== null
            ? this.get(`${this.all_selector}[${this.id_attribute}="${id}"]`)
            : null;
    }
}
