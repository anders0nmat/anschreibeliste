import { Transaction } from "./transaction.js";
import { Account } from "./accounts.js";
import { API, debounce } from "./base.js";
const selected_account = document.querySelector('#accounts .item[selected]');
const decimalSeparator = Intl.NumberFormat()
    .formatToParts(0.5)
    .find(part => part.type == 'decimal')
    ?.value ?? '.';
document.querySelectorAll('.button[data-amount]').forEach(element => {
    element.addEventListener('click', _ => {
        const form = element.closest('form');
        const input = form.elements.namedItem('amount');
        let [wholes, cents] = input.value.split(decimalSeparator, 2);
        cents = (cents ?? '').padStart(2, '0').slice(0, 2);
        let value = parseInt(wholes + cents);
        value += parseInt(element.dataset.amount ?? '0');
        let valueStr = value.toString();
        valueStr = valueStr.slice(0, -2) + decimalSeparator + valueStr.slice(-2);
        input.value = valueStr;
        input.dispatchEvent(new InputEvent("input"));
    });
});
const withdraw_all = document.querySelector('#withdraw-all');
withdraw_all?.addEventListener('click', _ => {
    const form = withdraw_all.closest('form');
    const input = form.elements.namedItem('amount');
    const newValue = Math.max(parseInt(selected_account.dataset.balance ?? '0'), 0).toString().padStart(3, '0');
    input.value = newValue.slice(0, -2) + decimalSeparator + newValue.slice(-2);
});
const account_id = parseInt(document.getElementById('deposit-transaction').elements.namedItem('account').value);
Transaction.all(); // Register undo buttons
Transaction.listen(event => {
    const account = Account.byId(event.account.toString());
    if (!account) {
        return;
    }
    account.balance = event.balance;
    account.disabled = account.budget <= 0;
}, false, account_id);
const deposit_amount = document.querySelector('#deposit-transaction #id_amount');
deposit_amount.addEventListener("input", debounce(async (_) => {
    const rsp = await fetch(API.endpoints.qr + '?' + new URLSearchParams({
        'account': account_id.toString(),
        'amount': deposit_amount.value,
    }));
    if (!rsp.ok) {
        return;
    }
    const xml = await rsp.text();
    const svg = document.querySelector('#banking-details svg');
    svg.outerHTML = xml;
}, 100));
