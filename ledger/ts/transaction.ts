
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

export interface Product {
	readonly name: string
	totalCost(member: boolean): number
}

export interface Account {
	readonly name: string
	readonly blocked: boolean

	canAfford(_: Product): boolean
}

type TransactionKind = "product" | "deposit" | "withdraw"

interface TransactionApi {
	deposit: string
	withdraw: string
	order: string
	revert: string
	events: string
}

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
	static api = JSON.parse(document.getElementById('api')?.textContent ?? '') as TransactionApi

	private static csrf_token = document.querySelector<HTMLInputElement>('[name=csrfmiddlewaretoken]')!.value
	private static async post(url: RequestInfo | URL, body: any, idempotency_key: string | undefined = undefined): ReturnType<typeof fetch> {
		return fetch(
			url, {
			method: "POST",
			headers: {
				"Content-Type": "application/json",
				"X-CSRFToken": this.csrf_token,
				"Idempotency-Key": idempotency_key ?? Date.now().valueOf().toString(),
				"Accept": "application/json",
			},
			body: JSON.stringify(body),
		})
	}

	private static reconnect_interval?: number = undefined
	private static event_source: EventSource | undefined = undefined
	static listen(ontransaction?: (event: ServerEvent) => void, reconnect: boolean = false) {
		const url = new URL(this.api.events, document.location.origin)
		
		const all_transaction_ids = this.all().map(t => parseInt(t.id))
		if (reconnect && all_transaction_ids) {
			const max_transaction_id = Math.max(...all_transaction_ids).toString()
			url.searchParams.set('last_transaction', max_transaction_id)
		}

		this.event_source = new EventSource(url)
		this.event_source.addEventListener('reload', _ => { location.reload() })
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

			const related_transaction = data.related !== undefined && Transaction.from(document.querySelector<HTMLElement>(`.transaction:has([name="transaction"][value="${data.related}"])`))
			if (related_transaction) {
				related_transaction.can_revert = false
			}

			if (ontransaction) {
				ontransaction(data)
			}
		})

		this.event_source.addEventListener('open', _ => {
			// Successful connection, do not try to reconnect anymore
			clearInterval(this.reconnect_interval)
			this.reconnect_interval = undefined	
		})
		
		this.event_source.addEventListener('error', _ => {
			if (this.event_source?.readyState == EventSource.CLOSED) {
				// Browser will not retry on its own
				// Retry every 10s
				if (this.reconnect_interval === undefined) {
					this.reconnect_interval = setInterval(() => {
						this.listen(ontransaction)
					}, 10_000);
				}
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
			url = this.api.order
			body = {
				account: request.account_id,
				product: request.product_id,
				...(request.amount && {amount: request.amount}),
			}
		}
		else {
			url = request.kind == 'deposit' ? this.api.deposit : this.api.withdraw
			body = {
				account: request.account_id,
				amount: request.balance,
				reason: request.reason,
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


	static attachNew(
	form_element: HTMLFormElement,
	account_getter: (_: string) => Account | null,
	product_getter: (_: string) => Product | null,
	onInputChange?: (_: HTMLInputElement) => void) {
		const account_radios = form_element.elements['account'] as RadioNodeList
		const product_radios = form_element.elements['product'] as RadioNodeList
		const amount_input = form_element.elements['amount'] as HTMLInputElement

		const selected_account = form_element.elements['selected_account'] as HTMLOutputElement
		const selected_product = form_element.elements['selected_product'] as HTMLOutputElement

		[...account_radios, ...product_radios, amount_input].forEach((e: HTMLInputElement) => {
			e.addEventListener('change', _ => {
				const account = account_getter(account_radios.value)
				const product = product_getter(product_radios.value)

				// Update selection display
				selected_account.value = account?.name ?? ''
				
				const amount_string = amount_input.valueAsNumber > 1 ? amount_input.value + 'x ' : ''
				selected_product.value = product ? amount_string + product.name : ''

				// Disable products & accounts according to price/budget
				product_radios.forEach((e: HTMLInputElement) => {
					const product = product_getter(e.value)
					e.disabled = account && product ? !account.canAfford(product) : false
				})

				account_radios.forEach((e: HTMLInputElement) => {
					const account = account_getter(e.value)
					if (account) {
						e.disabled = account.blocked || (product ? !account.canAfford(product) : false)
					}
					else {
						e.disabled = false
					}
				})

				if (onInputChange) {
					onInputChange(e)
				}

				// Auto-submit if both are present
				if (account && product) {
					form_element.requestSubmit()
				}
			})
		})
	}

	static attachRevert(form_element?: HTMLFormElement) {
		if (!form_element) {
			form_element = document.getElementById('transaction-revert') as HTMLFormElement
		}

		form_element.addEventListener('submit', ev => {
			ev.preventDefault()
			const transaction = (ev.submitter as HTMLButtonElement).value
			Transaction.post(this.api.revert, {transaction: transaction})
		})
	}

	static attachCustom(form_element: HTMLFormElement) {

	}

	get id(): string { return this.element.querySelector<HTMLInputElement>('button[name="transaction"]')!.value }
	get pendingId(): string { return this.element.dataset.pendingId ?? '' }

	set id(value: string | null) {
		if (value === null) {
			this.element.querySelector<HTMLInputElement>('button[name="transaction"]')!.value = ""
		}
		else {
			this.element.querySelector<HTMLInputElement>('button[name="transaction"]')!.value = value
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
}
