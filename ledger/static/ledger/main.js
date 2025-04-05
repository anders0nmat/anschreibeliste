import { config, HTMLIdentifierWrapper } from './base.js';
import { Transaction } from './transaction.js';
import { Account } from './accounts.js';
const TRANSACTION_TIMEOUT = config().transaction_timeout;
class Product extends HTMLIdentifierWrapper {
    static all_selector = '#products .item';
    static id_attribute = 'data-product-id';
    get id() { return this.element.dataset.productId ?? ''; }
    get name() { return this.element.querySelector('.name')?.textContent ?? ''; }
    get cost() { return parseInt(this.element.dataset.cost ?? '0'); }
    get memberCost() { return parseInt(this.element.dataset.memberCost ?? '0'); }
    totalCost(member) {
        const cost = member ? this.memberCost : this.cost;
        const amount = multiplier.value;
        return cost * amount;
    }
}
// Working slide indicators
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
// Hook up to server events for new transactions
Transaction.listen(event => {
    const account = Account.byId(event.account.toString());
    if (!account) {
        return;
    }
    account.balance = event.balance;
    account.disabled = account.budget <= 0;
}, true);
// Better transaction multiplier
const multiplier = {
    element: document.querySelector('#transaction-multiplier > span'),
    input: document.querySelector('#transaction-multiplier input'),
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
    multiplier.input.value = multiplier.value.toString();
    multiplier.input.dispatchEvent(new Event('change'));
});
multiplier.element.closest('div')?.addEventListener('click', _ => { multiplier.selectAll(); });
multiplier.input.parentElement?.classList.add('visually-hidden');
multiplier.element.classList.remove('css-hidden');
// Attach to transaction form
const new_transaction = {
    form: document.getElementById('new-transaction'),
    timeout: undefined,
    set_timeout() {
        new_transaction.clear_timeout();
        new_transaction.timeout = setTimeout(_ => new_transaction.form.reset(), TRANSACTION_TIMEOUT);
        new_transaction.form.classList.add('timeout');
    },
    clear_timeout() {
        clearTimeout(new_transaction.timeout);
        new_transaction.timeout = undefined;
        new_transaction.form.classList.remove('timeout');
        // force animation stop in case it gets started immediately again
        new_transaction.form.offsetWidth;
    },
    change(e) {
        const account = new_transaction.form.elements['account'].value;
        const product = new_transaction.form.elements['product'].value;
        if (account || product) {
            new_transaction.set_timeout();
        }
        const next_slide = {
            'account': 'products',
            'product': 'accounts',
        };
        if (e.checked) {
            changeSlide(next_slide[e.name]);
        }
    },
};
Transaction.attachNew(new_transaction.form, id => Account.byId(id), id => Product.byId(id), new_transaction.change);
Transaction.attachRevert();
new_transaction.form.addEventListener('reset', _ => {
    new_transaction.clear_timeout();
    multiplier.value = 1;
});
new_transaction.form.addEventListener('submit', ev => {
    ev.preventDefault();
    const account = Account.byId(new_transaction.form.elements['account'].value);
    const product = Product.byId(new_transaction.form.elements['product'].value);
    if (!account || !product) {
        return;
    }
    const amount = new_transaction.form.elements['amount'].valueAsNumber;
    Transaction.submit({
        kind: "product",
        account_id: account.id,
        account_name: account.name,
        balance: -product.totalCost(account.isMember),
        product_id: product.id,
        reason: `${amount > 1 ? `${amount}x ` : ''}${product.name}`,
        amount: amount,
    });
    new_transaction.form.reset();
});
// Hide submit button (because of auto-submit)
new_transaction.form.querySelector('button[type="submit"').classList.add('css-hidden');
// Adjust timeout animation to actual timeout
new_transaction.form.style.animationDuration = TRANSACTION_TIMEOUT.toString();
// Horizontal Items
document.querySelector('.slideshow').classList.add('horizontal');
