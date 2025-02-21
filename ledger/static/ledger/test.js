class DrunkMoney extends HTMLElement {
    static observedAttributes = ['amount'];
    connectedCallback() {
        const money_template = document.getElementById(`${this.tagName.toLowerCase()}-template`).content.cloneNode(true);
        this.appendChild(money_template);
        this._update();
    }
    attributeChangedCallback(_name, _oldValue, _newValue) {
        if (this.childElementCount == 0) {
            return;
        }
        this._update();
    }
    _update() {
        const amount = parseInt(this.getAttribute('amount') ?? '0');
        const padded = Math.abs(amount).toString().padStart(3, '0');
        this.toggleAttribute('negative', amount < 0);
        this.querySelector('.wholes').textContent = padded.slice(0, -2);
        this.querySelector('.cents').textContent = padded.slice(-2);
    }
    get amount() { return parseInt(this.getAttribute('amount') ?? '0') ?? 0; }
    set amount(value) { this.setAttribute('amount', value.toString()); }
}
window.customElements.define('drunk-money', DrunkMoney);
class DrunkTransaction extends HTMLElement {
    constructor() {
        super();
        //const drunk_template: HTMLElement = (document.getElementById(`${this.tagName.toLowerCase()}-template`) as HTMLTemplateElement).content.cloneNode(true) as HTMLElement
        //if (this.childElementCount == 0) {
        //	this.appendChild(drunk_template)
        //}
    }
    connectedCallback() {
        console.log("DrunkTransaction is connected");
    }
    get account() { return this.querySelector('.name').textContent ?? ''; }
    set account(value) { this.querySelector('.name').textContent = value; }
    get reason() { return this.querySelector('.reason').textContent ?? ''; }
    set reason(value) { this.querySelector('.reason').textContent = value; }
    get money() { return this.querySelector('drunk-money'); }
    get transaction_id() { return this.getAttribute('transaction-id'); }
    set transaction_id(value) {
        if (value === null) {
            this.removeAttribute('transaction-id');
        }
        else {
            this.setAttribute('transaction-id', value);
        }
    }
    get pending_id() { return this.getAttribute('pending-id'); }
    set pending_id(value) {
        if (value === null) {
            this.removeAttribute('pending-id');
        }
        else {
            this.setAttribute('pending-id', value);
        }
    }
    revert() {
        console.log("reverting", this);
    }
}
window.customElements.define('drunk-transaction', DrunkTransaction);
