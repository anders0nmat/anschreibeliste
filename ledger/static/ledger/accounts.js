import { _money, HTMLIdentifierWrapper } from "./base.js";
export class Account extends HTMLIdentifierWrapper {
    static all_selector = '#accounts .item';
    static id_attribute = 'data-account-id';
    static deselectAll() { this.all().forEach(acc => acc.selected = false); }
    static enableAll() { this.all().forEach(acc => acc.disabled = false); }
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
    get blocked() { return this.element.hasAttribute('blocked'); }
    set blocked(value) { this.element.toggleAttribute('blocked', value); }
    get disabled() { return this.element.hasAttribute('disabled'); }
    set disabled(value) { this.element.toggleAttribute('disabled', value); }
    get selected() { return this.element.hasAttribute('selected'); }
    set selected(value) { this.element.toggleAttribute('selected', value); }
    select() { this.selected = true; }
    canAfford(product) { return this.budget >= product.totalCost(this.isMember); }
}
