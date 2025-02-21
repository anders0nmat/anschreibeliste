
/*
	Controls how long the confirmation/error overlay is shown after submitting a transaction.

	Unit: ms (milliseconds)
	Default value: 1_500
*/
const SUBMIT_OVERLAY_DURATION = 1_500

import { _money, _span } from './base.js'

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

interface TransactionResponse {
	id?: string,
	idempotency_key?: string,
	account_name: string,
	cost: number,
	reason: string,
	can_revert: boolean,
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

export class Transaction {
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

	private static _undo(can_revert: boolean): DocumentFragment {
		const result = this.undo_template.content.cloneNode(true) as DocumentFragment
		result.querySelector<HTMLButtonElement>('button')!.disabled = !can_revert
		return result
	}

	private static _status(): DocumentFragment {
		return this.status_template.content.cloneNode(true) as DocumentFragment
	}

	static add(response: TransactionResponse): Transaction {
		const account = _span(response.account_name, "account")
		const reason = _span(response.reason, "reason")
		const amount = _money(response.cost)
		const undo = this._undo(response.can_revert)

		let item: HTMLElement | null = null
		if (response.id) {
			item = response.idempotency_key !== undefined ? this.container.querySelector<HTMLElement>(`.transaction[data-pending-id="${response.idempotency_key}"]`) : null
			if (item) {
				delete item.dataset.pendingId
				item.querySelectorAll<HTMLElement>(':scope > :not(.status)').forEach(e => e.remove())
				item.prepend(account, reason, amount, undo)
			}
			else {
				item = document.createElement('li')
				item.classList.add('transaction')
				item.dataset.transactionId = response.id
	
				this.container.prepend(item)
				item.append(account, reason, amount, undo)
			}
		}
		else {
			item = document.createElement('li')
			item.classList.add('transaction')
			item.dataset.pendingId = response.idempotency_key!
			this.container.prepend(item)

			const status = this._status()
			item.append(account, reason, amount, undo, status)
		}

		if (response.id) {
			if (this.objects.has(response.id)) {
				return this.objects.get(response.id)!
			}
			else {
				const transaction = new this(item)
				this.objects.set(transaction.id, transaction)
				return transaction
			}
		}
		else {
			return new this(item)
		}
	}

	static async submit(request: TransactionRequest) {
		const idempotency_key = Date.now().valueOf().toString()

		const pending_transaction = Transaction.add({
			account_name: request.account_name,
			cost: request.kind == "withdraw" ? -request.balance : request.balance,
			reason: request.reason,
			idempotency_key: idempotency_key,
			can_revert: true,
		})

		let url = ''
		let body = {}
		if (request.kind === "product") {
			url = TRANSACTION_PRODUCT_URL
			body = {
				account: request.account_id,
				product: request.product_id,
				...(request.amount && {amount: request.amount})
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
			pending_transaction.status!.dataset.status = "failure"
			pending_transaction.element.toggleAttribute('error', true)
			return
		}

		const {transaction_id} = await response.json()
		
		pending_transaction.element.dataset.transactionId = transaction_id
		Transaction.objects.set(pending_transaction.id, pending_transaction)
		
		pending_transaction.status!.dataset.status = "success"
		await delay(SUBMIT_OVERLAY_DURATION)
		pending_transaction.status?.remove()
	}

	private static event_source: EventSource | undefined = undefined
	static listen(ontransaction?: (event: ServerEvent) => void) {
		this.event_source = new EventSource(TRANSACTION_EVENT_URL)
		this.event_source.addEventListener('create', event => {
			const data = JSON.parse(event.data) as ServerEvent
			console.log("received server event: ", data)

			Transaction.add({
				account_name: data.account_name,
				cost: data.amount,
				reason: data.reason,
				id: data.id.toString(),
				idempotency_key: data.idempotency_key,
				can_revert: data.related === undefined
			})
			if (data.related !== undefined && Transaction.objects.has(data.related.toString())) {
				Transaction.objects.get(data.related.toString())!.undo_button.disabled = true
			}

			if (ontransaction) {
				ontransaction(data)
			}
		})
	}

	private static status_template = document.getElementById('template-status')! as HTMLTemplateElement
	private static undo_template = document.getElementById('template-undo')! as HTMLTemplateElement
	private static csrf_token = document.querySelector<HTMLInputElement>('[name=csrfmiddlewaretoken]')!.value


	static container = document.getElementById('transactions')!
	static objects = new Map<string, Transaction>(
		Array.from(this.container.querySelectorAll<HTMLElement>('.transaction'), element => {
			const transaction = new this(element)
			return [transaction.id, transaction]
		}))


	element: HTMLElement
	constructor(element: HTMLElement) {
		this.element = element

		this.undo_button.addEventListener('click', _ => this.revert())
	}

	get id(): string { return this.element.dataset.transactionId ?? '' }
	get undo_button(): HTMLButtonElement { return this.element.querySelector<HTMLButtonElement>('.undo')! }
	get status(): HTMLElement | null { return this.element.querySelector<HTMLElement>('.status') }

	revert() {
		const id = parseInt(this.id)
		if (!id) { return }
		Transaction.post(TRANSACTION_REVERT_URL, {transaction: id})
	}
}

async function delay(time: number) { return new Promise<void>(resolve => setTimeout(resolve, time)) }

