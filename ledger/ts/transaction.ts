
/*
	Controls how long the confirmation/error overlay is shown after submitting a transaction.

	Unit: ms (milliseconds)
	Default value: 1_500
*/
const SUBMIT_OVERLAY_DURATION = 1_500

import { _set_money, HTMLWrapper } from './base.js'

interface ServerEvent {
	id: number,
	account: number,
	account_name: string,
	balance: number,
	is_liquid: boolean,
	amount: number,
	reason: string,
	related: number | undefined,
	idempotency_key: string | undefined,
}

type TransactionKind = "product" | "deposit" | "withdraw"
declare const TRANSACTION_PRODUCT_URL: string
declare const TRANSACTION_CUSTOM_URL: string
declare const TRANSACTION_REVERT_URL: string
declare const TRANSACTION_EVENT_URL: string

interface TransactionRequestBase {
	kind: TransactionKind
	account_id: string
	account_name: string
	reason: string
	balance: number
}

interface TransactionProductRequest extends TransactionRequestBase {
	kind: "product",
	product_id: string
	amount?: number
}

interface TransactionAmountRequest extends TransactionRequestBase {
	kind: "deposit" | "withdraw"
}

type TransactionRequest = TransactionAmountRequest | TransactionProductRequest

class Status extends HTMLWrapper {
	error() {
		this.element.dataset.status = "failure"
	}

	success() {
		this.element.dataset.status = "success"
		setTimeout(_ => this.element.remove(), SUBMIT_OVERLAY_DURATION)
	}
}

export class Transaction extends HTMLWrapper {
	static template: string = 'transaction-template'
	static all_selector: string = '#transactions .transaction'

	private static csrf_token = document.querySelector<HTMLInputElement>('[name=csrfmiddlewaretoken]')!.value
	private static async post(url: RequestInfo | URL, body: any, idempotency_key: string | undefined = undefined): ReturnType<typeof fetch> {
		return fetch(
			url, {
			method: "POST",
			headers: {
				"Content-Type": "application/json",
				"X-CSRFToken": this.csrf_token,
				"Idempotency-Key": idempotency_key ?? Date.now().valueOf().toString(),
			},
			body: JSON.stringify(body),
		})
	}

	private static onUndoTransaction(ev: MouseEvent) {
		Transaction.from((ev.target as HTMLElement).closest<HTMLElement>('.transaction'))?.revert()
	}

	private static event_source: EventSource | undefined = undefined
	static listen(ontransaction?: (event: ServerEvent) => void) {
		this.event_source = new EventSource(TRANSACTION_EVENT_URL)
		this.event_source.addEventListener('create', event => {
			const data = JSON.parse(event.data) as ServerEvent
			console.log("received server event:", data)

			const confirmed_transaction = data.idempotency_key !== undefined && Transaction.from(document.querySelector<HTMLElement>(`.transaction[data-pending-id="${data.idempotency_key}"]`))
			if (confirmed_transaction) {
				confirmed_transaction.pendingId = null
				confirmed_transaction.account = data.account_name
				confirmed_transaction.amount = data.amount
				confirmed_transaction.reason = data.reason
				confirmed_transaction.can_revert = data.related === undefined
			}
			else {
				const new_transaction = Transaction.create()
				new_transaction.id = data.id.toString()
				new_transaction.account = data.account_name
				new_transaction.amount = data.amount
				new_transaction.reason = data.reason
				new_transaction.can_revert = data.related === undefined
				new_transaction.status?.element.remove()
				document.getElementById('transactions')!.prepend(new_transaction.element)
			}

			const related_transaction = data.related !== undefined && Transaction.from(document.querySelector<HTMLElement>(`.transaction[data-transaction-id="${data.related}"]`))
			if (related_transaction) {
				related_transaction.can_revert = false
			}

			if (ontransaction) {
				ontransaction(data)
			}
		})
	}

	static async submit(request: TransactionRequest) {
		const idempotency_key = Date.now().valueOf().toString()

		const pending_transaction = Transaction.create()
		pending_transaction.account = request.account_name
		pending_transaction.amount = request.kind == "withdraw" ? -request.balance : request.balance
		pending_transaction.reason = request.reason
		pending_transaction.can_revert = true
		pending_transaction.pendingId = idempotency_key
		document.getElementById('transactions')!.prepend(pending_transaction.element)

		let url = ''
		let body = {}
		if (request.kind == "product") {
			url = TRANSACTION_PRODUCT_URL
			body = {
				account: request.account_id,
				product: request.product_id,
				...(request.amount && {amount: request.amount}),
			}
		}
		else {
			url = TRANSACTION_CUSTOM_URL
			body = {
				account: request.account_id,
				amount: request.balance,
				type: request.kind,
			}
		}

		const response = await Transaction.post(url, body, idempotency_key)

		if (!response.ok) {
			pending_transaction.status!.error()
			pending_transaction.element.toggleAttribute("error", true)
			return
		}

		const {transaction_id} = await response.json()

		pending_transaction.id = transaction_id
		pending_transaction.status!.success()
	}

	constructor(element: HTMLElement) {
		super(element)

		this.element.querySelector<HTMLElement>('.undo')!.addEventListener('click', Transaction.onUndoTransaction)
	}

	get id(): string { return this.element.dataset.transactionId ?? '' }
	get pendingId(): string { return this.element.dataset.pendingId ?? '' }

	set id(value: string | null) {
		if (value === null) {
			delete this.element.dataset.transactionId
		}
		else {
			this.element.dataset.transactionId = value
		}
	}
	set pendingId(value: string | null) {
		if (value === null) {
			delete this.element.dataset.pendingId
		}
		else {
			this.element.dataset.pendingId = value
		}
	}

	set account(value: string) {
		const accountElement = this.element.querySelector<HTMLElement>('.account')!
		accountElement.textContent = value
	}

	set reason(value: string) {
		const reasonElement = this.element.querySelector<HTMLElement>('.reason')!
		reasonElement.textContent = value
	}

	set amount(value: number) {
		_set_money(this.element.querySelector('.money')!, value)
	}

	set can_revert(value: boolean) {
		this.element.querySelector<HTMLButtonElement>('.undo')!.disabled = !value
	}

	get status(): Status | null { return Status.from(this.element.querySelector<HTMLElement>('.status')) }

	revert() {
		const id = parseInt(this.id)
		if (!id) { return }
		Transaction.post(TRANSACTION_REVERT_URL, {transaction: id})
	}
}
