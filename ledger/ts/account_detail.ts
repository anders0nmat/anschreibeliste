
import { Transaction } from "./transaction.js"
import { Account } from "./accounts.js"

const selected_account = document.querySelector<HTMLElement>('#accounts .item[selected]')!
const deposit_amount = document.querySelector<HTMLInputElement>('#deposit-amount')!
const withdraw_amount = document.querySelector<HTMLInputElement>('#withdraw-amount')!

const decimalSeparator = Intl.NumberFormat()
	.formatToParts(0.5)
	.find(part => part.type == 'decimal')
	?.value ?? '.'

document.querySelectorAll<HTMLElement>('.button[data-amount]').forEach(element => {
	element.addEventListener('click', _ => {
		const form: HTMLFormElement = element.closest('form')!
		const input = form.elements.namedItem('amount')! as HTMLInputElement
		let [wholes, cents] = input.value.split(decimalSeparator, 2)

		cents = cents ? cents : '0'
		cents = cents.length > 2 ? cents.slice(0, 2) : cents
		let value = parseInt(wholes + cents)
		value += parseInt(element.dataset.amount ?? '0')

		let valueStr = value.toString()
		valueStr = valueStr.slice(0, -2) + decimalSeparator + valueStr.slice(-2)

		input.value = valueStr
	})
})
/*
document.querySelectorAll<HTMLElement>('#withdraw-transaction .button[data-amount]').forEach(element => {
	element.addEventListener('click', _ => {
		withdraw_amount.value = (parseInt(withdraw_amount.value) + parseInt(element.dataset.amount ?? '0')).toString()
	})
})*/
const withdraw_all = document.querySelector<HTMLElement>('#withdraw-all')!
withdraw_all.addEventListener('click', _ => {
	const form: HTMLFormElement = withdraw_all.closest('form')!
	const input = form.elements.namedItem('amount')! as HTMLInputElement

	const newValue = Math.max(parseInt(selected_account.dataset.balance ?? '0'), 0).toString().padStart(3, '0')

	input.value = newValue.slice(0, -2) + decimalSeparator + newValue.slice(-2)
})

Transaction.all() // Register undo buttons
Transaction.listen(event => {
	const account = Account.byId(event.account.toString())
	if (!account) { return }
	account.balance = event.balance
	account.blocked = !event.is_liquid
})

/* ===== Progressive Enhancement ===== */

// Submit without reload

function submit_custom_transaction(ev: SubmitEvent) {
	ev.preventDefault()
	const form = ev.target as HTMLFormElement
	const form_data = new FormData(form)

	const action = form_data.get('action') as ("deposit" | "withdraw")
	const account = form_data.get('account') as string
	const amount = parseInt(form_data.get('amount') as string)
	const reason = form_data.get('reason') as string ?? ''

	Transaction.submit({
		kind: action,
		account_id: account,
		account_name: Account.byId(account)?.name ?? 'Unknown',
		balance: amount,
		reason: reason,
	})

	form.reset()
}

document.getElementById('withdraw-transaction')!.addEventListener('submit', submit_custom_transaction)
document.getElementById('deposit-transaction')!.addEventListener('submit', submit_custom_transaction)


