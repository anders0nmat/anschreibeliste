import { _money, HTMLIdentifierWrapper } from "./base.js";
export class Account extends HTMLIdentifierWrapper {
    static all_selector = '#accounts .item';
    static id_attribute = 'data-account-id';
    static deselectAll() { this.all().forEach(acc => acc.selected = false); }
    static enableAll() { this.all().forEach(acc => acc.disabled = false); }
    radio;
    constructor(element) {
        super(element);
        this.radio = element.querySelector('input[name="account"]');
    }
    get id() { return this.element.dataset.accountId ?? ''; }
    get name() { return this.element.querySelector('.name')?.textContent ?? ''; }
    get isMember() { return 'member' in this.element.dataset; }
    get credit() { return parseInt(this.element.dataset.credit ?? '0'); }
    get budget() { return this.balance + this.credit; }
    get balance() { return parseInt(this.element.dataset.balance ?? '0'); }
    set balance(value) {
        this.element.dataset.balance = value.toString();
        this.element.querySelector('.money').replaceWith(_money(value));
    }
    get disabled() { return this.radio.disabled; }
    set disabled(value) { this.radio.disabled = value; }
    get selected() { return this.element.hasAttribute('selected'); }
    set selected(value) { this.element.toggleAttribute('selected', value); }
    select() { this.selected = true; }
    canAfford(product) { return this.budget >= product.totalCost(this.isMember); }
}
