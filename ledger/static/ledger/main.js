import { config, HTMLIdentifierWrapper } from './base.js';
import { Transaction } from './transaction.js';
import { Account } from './accounts.js';
const TRANSACTION_TIMEOUT = config().transaction_timeout;
const SEARCH_DEBOUNCE_DELAY = 50;
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
function changeSlide(name) {
    document.querySelector(`.slide[data-slide="${name}"]`)?.scrollIntoView({ block: "nearest" });
    clearSearch();
}
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
Transaction.attachNew({
    getAccount: id => Account.byId(id),
    getProduct: id => Product.byId(id),
    timeout: TRANSACTION_TIMEOUT,
    onInputChange: e => {
        const next_slide = {
            'account': 'products',
            'product': 'accounts',
        };
        if (next_slide[e.name] && e.checked) {
            changeSlide(next_slide[e.name]);
        }
    },
    onReset: _ => {
        multiplier.value = 1;
        clearSearch();
    }
});
Transaction.attachRevert();
// Horizontal Items
document.querySelector('.slideshow').classList.add('horizontal');
// Activate search bar
document.querySelector('div[hidden]').hidden = false;
const search_bar = document.querySelector('#item-search');
function debounce(func, wait, immediate = false) {
    var timeout;
    return function (...args) {
        var context = this;
        var later = function () {
            timeout = null;
            if (!immediate)
                func.apply(context, args);
        };
        var callNow = immediate && !timeout;
        clearTimeout(timeout ?? undefined);
        timeout = setTimeout(later, wait);
        if (callNow)
            func.apply(context, args);
    };
}
// An array of [name, element] pairs, for faster search
const search_items = [...Account.all(), ...Product.all()].map(e => [e.name, e.element]);
search_bar.addEventListener('input', debounce(_ => {
    const searchTerms = search_bar.value.toLowerCase().split(' ');
    search_items.forEach(([name, element]) => {
        const matches = searchTerms.every(term => name.toLocaleLowerCase().includes(term));
        element.style.display = matches ? '' : 'none';
    });
}, SEARCH_DEBOUNCE_DELAY));
function clearSearch() {
    search_bar.value = '';
    search_bar.dispatchEvent(new Event('input'));
}
document.querySelector('#item-search ~ button').addEventListener('click', clearSearch);
