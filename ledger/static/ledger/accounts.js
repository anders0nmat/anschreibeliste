import { _money } from "./base.js";
export class Account {
    static deselectAll() { this.objects.forEach(e => e.selected = false); }
    static enableAll() { this.objects.forEach(e => e.disabled = false); }
    static container = document.getElementById('accounts');
    static objects = new Map(Array.from(this.container.querySelectorAll('.item'), element => {
        const account = new this(element);
        return [account.id, account];
    }));
    element;
    constructor(element) {
        this.element = element;
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
    get blocked() { return this.element.hasAttribute('blocked'); }
    set blocked(value) { this.element.toggleAttribute('blocked', value); }
    get disabled() { return this.element.hasAttribute('disabled'); }
    set disabled(value) { this.element.toggleAttribute('disabled', value); }
    get selected() { return this.element.hasAttribute('selected'); }
    set selected(value) { this.element.toggleAttribute('selected', value); }
    select() { this.selected = true; }
}
