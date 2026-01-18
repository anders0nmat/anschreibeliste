import { _set_money, config, HTMLWrapper } from './base.js'

const SUBMIT_OVERLAY_DURATION = config().submit_overlay

interface ServerEvent {
	id: number,
	account: number,
	account_name: string,
	balance: number,
	amount: number,
	reason: string,
	related: number | undefined,
	idempotency_key: string | undefined,
}

interface Product {
	readonly id: string
	readonly name: string
	readonly cost: number
	readonly memberCost: number
}

interface Account {
	readonly id: string
	readonly name: string
	readonly budget: number
	readonly isMember: boolean
}

type TransactionKind = "product" | "deposit" | "withdraw"

interface TransactionRequestBase {
	kind: TransactionKind
	account_id: string
	account_name: string
	reason: string
	balance: string
}

interface TransactionProductRequest extends TransactionRequestBase {
	kind: "product",
	product_id: string
	amount?: number
	invert_member?: boolean
}

interface TransactionAmountRequest extends TransactionRequestBase {
	kind: "deposit" | "withdraw"
}

interface ProductRequest {
	account: Account
	product: Product
	amount: number
	/**
	Whether the member role of `account` should be inverted for product price
	*/
	invertMember: boolean
}

type TransactionRequest = TransactionAmountRequest | TransactionProductRequest

function getRadioGroup(formElements: HTMLFormControlsCollection, name: string): { elements: HTMLInputElement[], readonly value: string; } {
	const elements: RadioNodeList | HTMLInputElement | null = formElements[name]

	if (elements instanceof RadioNodeList) {
		return {
			elements: Array.from(elements) as HTMLInputElement[],
			get value(): string { return elements.value }
		}
	}

	if (elements instanceof HTMLInputElement) {
		return {
			elements: [elements],
			get value(): string { return elements.value }
		}
	}
	return {
		elements: [],
		get value(): string { return '' }
	}
}

function getIdempotencyKey(): string {
	return Date.now().valueOf().toString()
}

function productReason(account: Account | null, product: Product | null, amount: number, invert_member = false): string {
	let reason = ''
	if (invert_member) {
		reason += account?.isMember ? 'Für Extern: ' : 'Für Clubbi: '
	}
	if (amount > 1) {
		reason += `${amount}x `
	}
	if (product) {
		reason += product.name
	}

	return reason
}

function totalProductCost(request: ProductRequest): number {
	const useMemberCost = request.account.isMember != request.invertMember
	const singleProductCost = useMemberCost ? request.product.memberCost : request.product.cost
	return request.amount * singleProductCost
}


class Status extends HTMLWrapper {
	error() { this.element.dataset.status = "failure" }

	success() {
		this.element.dataset.status = "success"
		setTimeout(_ => this.element.remove(), SUBMIT_OVERLAY_DURATION)
	}
}

export class Transaction extends HTMLWrapper {
	static template: string = 'transaction-template'
	static all_selector: string = '#transactions .transaction'
	static api = config().transaction

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

	private static ping_nonce: number | undefined = undefined
	private static ping_eventsource() {
		try {
			this.ping_nonce = Date.now().valueOf()
			fetch(this.api.ping + `?nonce=${this.ping_nonce}`)

			setTimeout(_ => {
				if (this.ping_nonce !== undefined) {
					console.log("Transaction eventsource ping failed, reconnecting...")
					this.reconnect()
				}
				else {
					console.log(("Transaction eventsource ping succeded"))
				}
			}, 500)
		}
		catch {
			// No internet?
			// Server down?
		}
	}

	private static reconnect_interval?: number = undefined
	private static event_source: EventSource | undefined = undefined
	private static eventsource_handlers: {
		ontransaction?: (event: ServerEvent) => void
	} = {}
	private static async reconnect() {
		this.event_source?.close()
		await this.listen(this.eventsource_handlers.ontransaction, true)
	}
	static attachPing() {
		document.addEventListener('visibilitychange', ev => {
			if (document.visibilityState == "visible") {
				this.ping_eventsource()
			}
		})
	}
	static async listen(ontransaction?: (event: ServerEvent) => void, reconnect: boolean = false, account?: number) {
		const url = new URL(this.api.events, document.location.origin)

		this.eventsource_handlers.ontransaction = ontransaction
		
		const all_transaction_ids = this.all().map(t => parseInt(t.id))
		if (reconnect && all_transaction_ids.length > 0) {
			const max_transaction_id = Math.max(...all_transaction_ids).toString()
			url.searchParams.set('last_transaction', max_transaction_id)
		}
		
		this.event_source = new EventSource(url)

		this.event_source.addEventListener('ping', event => {
			const nonce = parseInt(event.data)
			if (nonce == this.ping_nonce) {
				this.ping_nonce = undefined
			}
		})
		this.event_source.addEventListener('reload', _ => { location.reload() })
		this.event_source.addEventListener('create', event => {
			const data = JSON.parse(event.data) as ServerEvent
			console.log("received server event:", data)

			const confirmed_transaction = data.idempotency_key && Transaction.fromQuery(`.transaction[data-pending-id="${data.idempotency_key}"]`)
			if (confirmed_transaction) {
				confirmed_transaction.applyServerEvent(data)
			}
			else {
                if (account !== undefined && data.account != account) {
                    // Ignore transactions by other accounts than the one specified
                    return
                }
				const new_transaction = Transaction.create()
				new_transaction.applyServerEvent(data)
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
			console.log('Eventsource connected')
			clearInterval(this.reconnect_interval)
			this.reconnect_interval = undefined	
		})
		
		this.event_source.addEventListener('error', _ => {
			this.ping_nonce = undefined
			if (this.event_source?.readyState == EventSource.CLOSED) {
				// Browser will not retry on its own
				// Retry every 10s
				if (this.reconnect_interval === undefined) {
					this.reconnect_interval = setInterval(() => {
						this.listen(ontransaction, true)
					}, 10_000);
				}
			}
		})
	}

	static async submit(request: TransactionRequest) {
		const idempotency_key = Date.now().valueOf().toString()

		const pending_transaction = Transaction.create()
		pending_transaction.account = request.account_name
		pending_transaction.amount = (request.kind == 'withdraw' ? -1 : 1) * parseInt(request.balance.replace('.', '').padEnd(3, '0'))
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
				...(request.invert_member && {invert_member: request.invert_member})
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

	static async submitProduct(request: ProductRequest) {
		const idempotency_key = getIdempotencyKey()
		const useMemberPrice = request.account.isMember != request.invertMember
		
		const pending_transaction = Transaction.create()
		pending_transaction.account = request.account.name
		pending_transaction.amount = -totalProductCost(request)
		pending_transaction.reason = productReason(request.account, request.product, request.amount, request.invertMember)
		pending_transaction.can_revert = true
		pending_transaction.pendingId = idempotency_key
		document.getElementById('transactions')!.prepend(pending_transaction.element)

		const response = await Transaction.post(this.api.order, {
			account: request.account.id,
			product: request.product.id,
			amount: request.amount,
			invert_member: request.invertMember,
		}, idempotency_key)

		if (!response.ok) {
			pending_transaction.status!.error()
			pending_transaction.element.toggleAttribute('error', true)
			console.error(`Failed to submit product: Server returned ${response.status} ${response.statusText}`, await response.json())
			return
		}

		const {transaction_id} = await response.json()

		pending_transaction.id = transaction_id
		pending_transaction.status!.success()
	}

	static attachNew({
		form: form_element,
		getAccount,
		getProduct,
		onInputChange,
		onReset,
		accountLocked,
		timeout: timeout_duration,
	}: {
		form?: HTMLFormElement,
		getAccount: (_: string) => Account | null,
		getProduct: (_: string) => Product | null,
		onInputChange?: (_: HTMLInputElement) => void,
		onReset?: (_: HTMLFormElement) => void,
		accountLocked?: () => boolean,
		timeout?: number,
	}): ({
		form: HTMLFormElement,
		updateSelection: () => void,
	}) {
		form_element ??= document.getElementById('new-transaction') as HTMLFormElement
		const timeout = timeout_duration ? {
			handler: undefined as number | undefined,

			set() {
				timeout!.clear()
				timeout!.handler = setTimeout(_ => form_element.reset(), timeout_duration)
				form_element.classList.add('timeout')
			},
			clear() {
				clearTimeout(timeout!.handler)
				timeout!.handler = undefined
				form_element.classList.remove('timeout')
				form_element.offsetWidth
			}
		} : undefined

		if (timeout_duration) {
			form_element.style.animationDuration = timeout_duration.toString() + 'ms'
		}

		const account_radios = getRadioGroup(form_element.elements, 'account')
		const product_radios = getRadioGroup(form_element.elements, 'product')
		const amount_input = form_element.elements['amount'] as HTMLInputElement
		const invert_input = form_element.elements['invert_member'] as HTMLInputElement

		const selected_account = form_element.elements['selected_account'] as HTMLOutputElement
		const selected_product = form_element.elements['selected_product'] as HTMLOutputElement

		const submit_button = form_element.querySelector('button[type="submit"]') as HTMLButtonElement
		submit_button.classList.add('css-hidden');

		const updateSelection = (selected_account: Account | null, selected_product: Product | null) => {
			// Disable products & accounts according to price/budget
			product_radios.elements.forEach((e: HTMLInputElement) => {
				const this_product = getProduct(e.value)
				if (this_product && selected_account) {
					e.disabled = selected_account.budget < totalProductCost({
						product: this_product,
						account: selected_account,
						amount: amount_input.valueAsNumber,
						invertMember: invert_input.checked,
					})
				}
				else {
					e.disabled = false
				}
			})

			account_radios.elements.forEach((e: HTMLInputElement) => {
				const this_account = getAccount(e.value)
				if (this_account && selected_product) {
					e.disabled = this_account.budget < totalProductCost({
						product: selected_product,
						account: this_account,
						amount: amount_input.valueAsNumber,
						invertMember: invert_input.checked,
					})
				}
				else {
					e.disabled = this_account ? this_account.budget <= 0 : false
				}
			})
		}

		const all_elements = [...account_radios.elements, ...product_radios.elements, amount_input, invert_input]
		all_elements.forEach((e: HTMLInputElement) => {
			e.addEventListener('change', _ => {
				const account = getAccount(account_radios.value)
				const product = getProduct(product_radios.value)

				// Update selection display
				selected_account.value = account?.name ?? ''
				selected_product.value = productReason(account, product, amount_input.valueAsNumber, invert_input.checked)

				updateSelection(account, product)

				onInputChange?.(e)

				if (account || product) {
					timeout?.set()
				}

				// Auto-submit if both are present
				if (account && product) {
					form_element.requestSubmit()
				}
			})
		})

		form_element.addEventListener('submit', ev => {
			ev.preventDefault()

			const account = getAccount(account_radios.value)
			const product = getProduct(product_radios.value)
			if (!account || !product) {
				// TODO : Should we reset the form here?
				return
			}

			Transaction.submitProduct({
				account: account,
				product: product,
				amount: amount_input.valueAsNumber,
				invertMember: invert_input.checked,
			})
			

			form_element.reset()

			if (accountLocked?.()) {
				account_radios.elements.find(e => e.value == account.id)?.click()
			}
		})

		form_element.addEventListener('reset', r => {
			timeout?.clear()

			updateSelection(null, null)

			onReset?.(form_element)
		})

		return {
			form: form_element,
			updateSelection() {
				const account = getAccount(account_radios.value)
				const product = getProduct(product_radios.value)

				updateSelection(account, product)
			},
		}
	}

	static attachRevert(form_element?: HTMLFormElement) {
		form_element ??= document.getElementById('transaction-revert') as HTMLFormElement

		form_element.addEventListener('submit', ev => {
			ev.preventDefault()
			const transaction = (ev.submitter as HTMLButtonElement).value
			Transaction.post(this.api.revert, {transaction: transaction})
		})
	}

	static attachCustom(form_element: HTMLFormElement) {

	}

	private applyServerEvent(data: ServerEvent) {
		this.id = data.id.toString()
		this.pendingId = null
		this.account = data.account_name
		this.amount = data.amount
		this.reason = data.reason
		this.can_revert = data.related === undefined
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
