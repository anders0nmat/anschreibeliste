import { Transaction } from "./transaction.js";
import { Account } from "./accounts.js";
const selected_account = document.querySelector('#accounts .item[selected]');
const deposit_amount = document.querySelector('#deposit-amount');
const withdraw_amount = document.querySelector('#withdraw-amount');
const decimalSeparator = Intl.NumberFormat()
    .formatToParts(0.5)
    .find(part => part.type == 'decimal')
    ?.value ?? '.';
document.querySelectorAll('.button[data-amount]').forEach(element => {
    element.addEventListener('click', _ => {
        const form = element.closest('form');
        const input = form.elements.namedItem('amount');
        let [wholes, cents] = input.value.split(decimalSeparator, 2);
        cents = cents ? cents : '0';
        cents = cents.length > 2 ? cents.slice(0, 2) : cents;
        let value = parseInt(wholes + cents);
        value += parseInt(element.dataset.amount ?? '0');
        let valueStr = value.toString();
        valueStr = valueStr.slice(0, -2) + decimalSeparator + valueStr.slice(-2);
        input.value = valueStr;
    });
});
/*
document.querySelectorAll<HTMLElement>('#withdraw-transaction .button[data-amount]').forEach(element => {
    element.addEventListener('click', _ => {
        withdraw_amount.value = (parseInt(withdraw_amount.value) + parseInt(element.dataset.amount ?? '0')).toString()
    })
})*/
const withdraw_all = document.querySelector('#withdraw-all');
withdraw_all?.addEventListener('click', _ => {
    const form = withdraw_all.closest('form');
    const input = form.elements.namedItem('amount');
    const newValue = Math.max(parseInt(selected_account.dataset.balance ?? '0'), 0).toString().padStart(3, '0');
    input.value = newValue.slice(0, -2) + decimalSeparator + newValue.slice(-2);
});
Transaction.all(); // Register undo buttons
Transaction.listen(event => {
    const account = Account.byId(event.account.toString());
    if (!account) {
        return;
    }
    account.balance = event.balance;
    account.disabled = account.budget <= 0;
}, false);
/* ===== Progressive Enhancement ===== */
// Submit without reload
function submit_custom_transaction(action) {
    return (ev) => {
        ev.preventDefault();
        const form = ev.target;
        const form_data = new FormData(form);
        const account = form_data.get('account');
        const amount = form_data.get('amount');
        const reason = form_data.get('reason') ?? '';
        Transaction.submit({
            kind: action,
            account_id: account,
            account_name: Account.byId(account)?.name ?? 'Unknown',
            balance: amount.replace(decimalSeparator, '.'),
            reason: reason,
        });
        form.reset();
    };
}
document.getElementById('withdraw-transaction')?.addEventListener('submit', submit_custom_transaction("withdraw"));
document.getElementById('deposit-transaction')?.addEventListener('submit', submit_custom_transaction("deposit"));
