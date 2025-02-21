
import { Transaction } from "./transaction.js"
import { Account } from "./accounts.js"

const selected_account = document.querySelector<HTMLElement>('#accounts .item[selected]')!
const deposit_amount = document.querySelector<HTMLInputElement>('#deposit-amount')!
const withdraw_amount = document.querySelector<HTMLInputElement>('#withdraw-amount')!

document.getElementById('confirm-deposit')!.addEventListener('click', _ => {
	const account_id = selected_account.dataset.accountId ?? ''
	const account_name = selected_account.querySelector<HTMLElement>('.name')?.textContent ?? ''
	const money = deposit_amount.value.padStart(3, '0')
	Transaction.submit({
		kind: 'deposit',
		account_id: account_id,
		account_name: account_name,
		balance: parseInt(deposit_amount.value),
		reason: `Deposit: ${money.slice(0, -2)},${money.slice(-2)}€`,
	})
	deposit_amount.value = '0'
})
document.getElementById('confirm-withdraw')!.addEventListener('click', _ => {
	const account_id = selected_account.dataset.accountId ?? ''
	const account_name = selected_account.querySelector<HTMLElement>('.name')?.textContent ?? ''
	const money = withdraw_amount.value.padStart(3, '0')
	Transaction.submit({
		kind: 'withdraw',
		account_id: account_id,
		account_name: account_name,
		balance: parseInt(withdraw_amount.value),
		reason: `Withdraw: ${money.slice(0, -2)},${money.slice(-2)}€`,
	})
	withdraw_amount.value = '0'
})

document.querySelectorAll<HTMLElement>('#deposit-transaction .button[data-amount]').forEach(element => {
	element.addEventListener('click', _ => {
		deposit_amount.value = (parseInt(deposit_amount.value) + parseInt(element.dataset.amount ?? '0')).toString()
	})
})
document.querySelectorAll<HTMLElement>('#withdraw-transaction .button[data-amount]').forEach(element => {
	element.addEventListener('click', _ => {
		withdraw_amount.value = (parseInt(withdraw_amount.value) + parseInt(element.dataset.amount ?? '0')).toString()
	})
})
document.querySelector<HTMLElement>('#withdraw-transaction #withdraw-all')!.addEventListener('click', _ => {
	withdraw_amount.value = Math.max(parseInt(selected_account.dataset.balance ?? '0'), 0).toString()
})

Transaction.listen(event => {
	const account = Account.objects.get(event.account.toString())
	if (!account) { return }
	account.balance = event.balance
	account.blocked = !event.is_liquid
})

