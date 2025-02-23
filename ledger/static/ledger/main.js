/*
    How long a unfinished transaction will exist before being discarded.

    Unit: ms (milliseconds)
    Default value: 10_000
*/
const TRANSACTION_TIMEOUT = 10_000;
import { Transaction } from './transaction.js';
import { Account } from './accounts.js';
class Item {
    static addItem(element) {
        const item = new this(element);
        this.objects.set(item.id, item);
    }
    static objectsFrom(selector) {
        let result = new Map();
        document.querySelectorAll(selector).forEach(element => {
            const item = new this(element);
            result.set(item.id, item);
        });
        return result;
    }
    element;
    constructor(element) {
        this.element = element;
        this.registerEvents();
    }
    get id() { return ''; }
    get isDisabled() { return this.element.getAttribute('disabled') !== null; }
    get isSelected() { return this.element.getAttribute('selected') !== null; }
    registerEvents() { return; }
    select(value = true) { this.element.toggleAttribute('selected', value); }
    deselect() { this.select(false); }
    static deselectAll() { this.objects.forEach(e => e.deselect()); }
    enable(value = true) { this.element.toggleAttribute('disabled', !value); }
    disable() { this.enable(false); }
    static enableAll() { this.objects.forEach(e => e.enable()); }
}
class Product extends Item {
    static objects = this.objectsFrom('#products .item');
    get id() { return this.element.dataset.productId ?? ''; }
    get name() { return this.element.querySelector('.name')?.textContent ?? ''; }
    get cost() { return parseInt(this.element.dataset.cost ?? '0'); }
    get memberCost() { return parseInt(this.element.dataset.memberCost ?? '0'); }
    totalCost(member) {
        const cost = member ? this.memberCost : this.cost;
        const amount = multiplier.value;
        return cost * amount;
    }
    registerEvents() {
        this.element.addEventListener("click", _ => {
            if (this.isDisabled) {
                return;
            }
            const alreadySelected = current_transaction.product_id === this.id;
            current_transaction.product = !alreadySelected ? this : null;
            if (!alreadySelected) {
                changeSlide('accounts');
            }
        });
    }
}
/*
class Account extends Item {
    static objects = this.objectsFrom('#accounts .item')

    get id(): string { return this.element.dataset.accountId ?? '' }
    get name(): string { return this.element.querySelector('.name')?.textContent ?? '' }
    get isMember(): boolean { return 'member' in this.element.dataset }
    get credit(): number { return parseInt(this.element.dataset.credit ?? '0') }
    get balance(): number { return parseInt(this.element.dataset.balance ?? '0') }
    set balance(value: number) {
        this.element.dataset.balance = value.toString()
        this.element.querySelector<HTMLElement>('.money')!.replaceWith(_money(value))
    }
    get budget(): number { return this.balance + this.credit }
    set blocked(value: boolean) { this.element.toggleAttribute('blocked', value) }
    get blocked(): boolean { return this.element.getAttribute('blocked') !== null }

    canAfford(product: Product): boolean { return this.budget >= product.totalCost(this) }

    override registerEvents() {
        this.element.addEventListener("click", _ => {
            if (this.blocked || this.isDisabled) { return }
            const alreadySelected = current_transaction.account_id === this.id
            current_transaction.account = !alreadySelected ? this : null
            if (!alreadySelected) { changeSlide('products') }
        })
    }
}
*/
const current_transaction = {
    element: document.getElementById("new-transaction"),
    overlay: document.querySelector('#new-transaction .overlay'),
    account_name: document.querySelector('#new-transaction .account'),
    product_name: document.querySelector('#new-transaction .product'),
    timeout: undefined,
    get account_id() { return current_transaction.element.dataset.accountId ?? null; },
    get product_id() { return current_transaction.element.dataset.productId ?? null; },
    get account() {
        return Account.objects.get(current_transaction.element.dataset.accountId ?? '') ?? null;
    },
    set account(account) {
        Account.deselectAll();
        account?.select();
        current_transaction.account_name.textContent = account?.name ?? 'Select an account';
        current_transaction.account_name.toggleAttribute('empty', account === null);
        if (account) {
            current_transaction.element.dataset.accountId = account.id;
            Product.objects.forEach(product => { product.enable(account.budget >= product.totalCost(account.isMember)); });
            current_transaction.set_timeout();
        }
        else {
            delete current_transaction.element.dataset.accountId;
            Product.enableAll();
            current_transaction.clear_timeout();
        }
        current_transaction.try_submit();
    },
    get product() {
        return Product.objects.get(current_transaction.element.dataset.productId ?? '') ?? null;
    },
    set product(product) {
        Product.deselectAll();
        product?.select();
        current_transaction.product_name.textContent = product?.name ?? 'Select a product';
        current_transaction.product_name.toggleAttribute('empty', product === null);
        if (product) {
            current_transaction.element.dataset.productId = product.id;
            Account.objects.forEach(account => { account.disabled = account.budget < product.totalCost(account.isMember); });
            current_transaction.set_timeout();
        }
        else {
            delete current_transaction.element.dataset.productId;
            Account.enableAll();
            current_transaction.clear_timeout();
        }
        current_transaction.try_submit();
    },
    show_overlay(value) {
        current_transaction.overlay.dataset.status = value;
        current_transaction.overlay.toggleAttribute('visible', true);
    },
    hide_overlay() { current_transaction.overlay.toggleAttribute('visible', false); },
    try_submit() {
        const account_id = parseInt(current_transaction.account_id ?? '0');
        const product_id = parseInt(current_transaction.product_id ?? '0');
        const account = current_transaction.account;
        const product = current_transaction.product;
        if (!account || !product) {
            return;
        }
        const amount = multiplier.value;
        Transaction.submit({
            kind: "product",
            account_id: account.id,
            account_name: account.name,
            balance: -product.totalCost(account.isMember),
            product_id: product.id,
            reason: `${amount > 1 ? `${amount}x ` : ''}${product.name}`,
            amount: amount,
        });
        /*const idempotency_key = Date.now().valueOf().toString()
        const pending_transaction = document.createElement("li")
        pending_transaction.classList.add("transaction")
        pending_transaction.dataset.pendingId = idempotency_key

        const amount = multiplier.value

        const account_name = _span(account.name, "account")
        const transaction_reason = _span(`${amount > 1 ? `${amount}x ` : ''}${product.name}`, "reason")
        const money = _money(product.totalCost(account))
        const status = (document.getElementById('template-status')! as HTMLTemplateElement).content.cloneNode(true) as DocumentFragment
        const status_item = status.querySelector<HTMLElement>('.status')!
        const undo_template = (document.getElementById('template-undo')! as HTMLTemplateElement).content.cloneNode(true) as DocumentFragment

        pending_transaction.append(account_name, transaction_reason, money, status, undo_template)

        document.getElementById("transactions")?.prepend(pending_transaction)

        //current_transaction.show_overlay('pending')

        Transaction.post("/transaction/", {
            account: account_id,
            product: product_id,
            ...(amount > 1 ? {amount: amount} : {})
        }, idempotency_key)
        .then(response => {
            switch (response.status) {
                case 200:
                    response.json()
                        .then(({transaction_id}) => {
                            pending_transaction.dataset.transactionId = transaction_id
                            Transaction.addItem(pending_transaction)

                            status_item.dataset.status = "success"
                            delay(SUBMIT_OVERLAY_DURATION)
                                .then(_ => {
                                    status_item.remove()
                                })
                        })
                    break
                default:
                    status_item.dataset.status = "failure"
                    pending_transaction.toggleAttribute('error', true)
                    break
            }
        })*/
        current_transaction.reset();
        current_transaction.clear_timeout();
    },
    reset() {
        current_transaction.account = null;
        current_transaction.product = null;
        multiplier.value = 1;
    },
    clear_timeout() {
        clearTimeout(current_transaction.timeout);
        current_transaction.timeout = undefined;
    },
    set_timeout() {
        current_transaction.clear_timeout();
        current_transaction.timeout = setTimeout(current_transaction.reset, TRANSACTION_TIMEOUT);
    },
};
function changeSlide(name) { document.querySelector(`.slide[data-slide="${name}"]`)?.scrollIntoView({ block: "nearest" }); }
const slideshow = document.querySelector('.slideshow');
const observer = new IntersectionObserver((entries) => {
    let activated = entries.reduce((max, entry) => {
        return (entry.intersectionRatio > max.intersectionRatio) ? entry : max;
    });
    if (activated.intersectionRatio > 0) {
        slideshow.parentElement.dataset.activeSlide = activated.target.dataset.slide;
    }
}, {
    root: slideshow,
    threshold: 0.5,
});
slideshow?.querySelectorAll('.slide').forEach(e => observer.observe(e));
document.querySelectorAll('.slide-indicator').forEach(e => {
    e.addEventListener('click', _ => { changeSlide(e.dataset.slide ?? ''); });
});
document.querySelector('#new-transaction .undo')?.addEventListener('click', _ => {
    current_transaction.reset();
    current_transaction.clear_timeout();
});
const multiplier = {
    element: document.getElementById('transaction-multiplier'),
    get value() {
        const amount = parseInt(multiplier.element.textContent ?? '1');
        if (!amount) {
            return 1;
        }
        return amount;
    },
    set value(value) {
        multiplier.element.textContent = value.toString();
    },
    selectAll() {
        const selection = document.getSelection();
        selection?.removeAllRanges();
        const range = document.createRange();
        range.selectNodeContents(multiplier.element);
        selection?.addRange(range);
        multiplier.element.focus();
    }
};
multiplier.element.addEventListener('beforeinput', (e) => {
    console.log(e);
    if (e.inputType.startsWith('format')) {
        e.preventDefault();
    }
    if (e.inputType.startsWith('insert')) {
        switch (e.inputType) {
            case "insertText":
            case "insertReplacementText":
                if (!e.data?.match(/^\d+$/i)) {
                    e.preventDefault();
                }
                break;
            case "insertLineBreak":
            case "insertParagraph":
                multiplier.element.blur();
                e.preventDefault();
                break;
            case "insertFromYank":
            case "insertFromDrop":
            case "insertFromPaste":
            case "insertFromPasteAsQuotation":
                const data = e.dataTransfer?.getData('text/plain');
                if (!data?.match(/^\d+$/i)) {
                    e.preventDefault();
                }
                break;
            default:
                e.preventDefault();
                break;
        }
    }
});
multiplier.element.addEventListener('input', _ => {
    if (current_transaction.account) {
        current_transaction.account = current_transaction.account;
    }
    if (current_transaction.product) {
        current_transaction.product = current_transaction.product;
    }
});
multiplier.element.closest('div')?.addEventListener('click', e => { multiplier.selectAll(); });
Transaction.listen(event => {
    const account = Account.objects.get(event.account.toString());
    if (!account) {
        return;
    }
    account.balance = event.balance;
    account.blocked = !event.is_liquid;
});
/*
const server_events = new EventSource("/transaction/events/")
server_events.addEventListener("create", ev => {
    try {
        const {id, account: account_id, balance, is_liquid, amount, reason, related, idempotency_key: key} = JSON.parse(ev.data) as ServerEvent
        const account = Account.objects.get(account_id.toString())
        if (!account) { return }

        console.log("server event: ", JSON.parse(ev.data))

        account.balance = balance
        account.blocked = !is_liquid
        //Transaction.accept(key, id.toString(), account.name, amount, reason ?? '', related === undefined)
        Transaction.add({
            account_name: account.name,
            cost: amount,
            reason: reason,
            id: id.toString(),
            idempotency_key: key,
            can_revert: related === undefined
        })
        if (related !== undefined && Transaction.objects.has(related.toString())) {
            Transaction.objects.get(related.toString())!.undo_button.disabled = true
        }
    }
    catch (e) {
        // Do not do anything on message errors because what should happen anyways
    }
})
*/
Account.objects.forEach(account => {
    account.element.addEventListener("click", _ => {
        if (account.blocked || account.disabled) {
            return;
        }
        const alreadySelected = current_transaction.account_id === account.id;
        current_transaction.account = !alreadySelected ? account : null;
        if (!alreadySelected) {
            changeSlide('products');
        }
    });
});
