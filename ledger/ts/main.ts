
/*
	How long a unfinished transaction will exist before being discarded.

	Unit: ms (milliseconds)
	Default value: 10_000
*/
const TRANSACTION_TIMEOUT = 10_000

import { _money, HTMLIdentifierWrapper } from './base.js'
import { Transaction } from './transaction.js'
import { Account } from './accounts.js'

class Product extends HTMLIdentifierWrapper {
	static all_selector: string = '#products .item'
	static id_attribute: string = 'data-product-id'
	
	get id(): string { return this.element.dataset.productId ?? '' }
	get name(): string { return this.element.querySelector('.name')?.textContent ?? '' }
	get cost(): number { return parseInt(this.element.dataset.cost ?? '0') }
	get memberCost(): number { return parseInt(this.element.dataset.memberCost ?? '0') }

	get disabled(): boolean { return this.element.hasAttribute('disabled') }
	set disabled(value: boolean) { this.element.toggleAttribute('disabled', value) }

	get selected(): boolean { return this.element.hasAttribute('selected') }
	set selected(value: boolean) { this.element.toggleAttribute('selected', value) }
	select() { this.selected = true }
	
	totalCost(member: boolean): number {
		const cost = member ? this.memberCost : this.cost
		const amount = multiplier.value
		return cost * amount
	}
}

const current_transaction = {
	element: document.getElementById("new-transaction")!,
	account_name: document.querySelector<HTMLElement>('#new-transaction .account')!,
	product_name: document.querySelector<HTMLElement>('#new-transaction .product')!,
	placeholder_account_name: "",
	placeholder_product_name: "",
	timeout: undefined as number | undefined,
	
	get account_id(): string | null { return current_transaction.element.dataset.accountId ?? null },
	get product_id(): string | null { return current_transaction.element.dataset.productId ?? null },

	get account(): Account | null { return Account.byId(current_transaction.account_id) },

	set account(account: Account | null) {
		Account.deselectAll(); account?.select()
		current_transaction.account_name.textContent = account?.name ?? current_transaction.placeholder_account_name
		current_transaction.account_name.toggleAttribute('empty', account === null)

		if (account) {
			current_transaction.element.dataset.accountId = account.id
			Product.all().forEach(product => { product.disabled = !account.canAfford(product) })
			current_transaction.set_timeout()
		}
		else {
			delete current_transaction.element.dataset.accountId
			Product.all().forEach(e => e.disabled = false)
			current_transaction.clear_timeout()
		}
		current_transaction.try_submit()
	},

	get product(): Product | null { return Product.byId(current_transaction.product_id) },
	
	set product(product: Product | null) {
		Product.all().forEach(e => e.selected = false); product?.select()
		current_transaction.product_name.textContent = product?.name ?? current_transaction.placeholder_product_name
		current_transaction.product_name.toggleAttribute('empty', product === null)

		if (product) {
			current_transaction.element.dataset.productId = product.id
			Account.all().forEach(account => { account.disabled = !account.canAfford(product) })
			current_transaction.set_timeout()
		}
		else {
			delete current_transaction.element.dataset.productId
			Account.enableAll()
			current_transaction.clear_timeout()
		}
		current_transaction.try_submit()
	},

	try_submit() {
		const account = current_transaction.account
		const product = current_transaction.product
		if (!account || !product) { return }

		const amount = multiplier.value

		Transaction.submit({
			kind: "product",
			account_id: account.id,
			account_name: account.name,
			balance: -product.totalCost(account.isMember),
			product_id: product.id,
			reason: `${amount > 1 ? `${amount}x ` : ''}${product.name}`,
			amount: amount,
		})

		current_transaction.reset()
		current_transaction.clear_timeout()
	},

	reset() {
		current_transaction.account = null
		current_transaction.product = null
		multiplier.value = 1
	},

	clear_timeout() {
		clearTimeout(current_transaction.timeout)
		current_transaction.timeout = undefined
		current_transaction.element.classList.remove('timeout')
		current_transaction.element.offsetWidth // trigger recalc to restart animation
	},

	set_timeout() {
		current_transaction.clear_timeout()
		current_transaction.timeout = setTimeout(current_transaction.reset, TRANSACTION_TIMEOUT)
		current_transaction.element.classList.add('timeout')
	},
}

current_transaction.placeholder_account_name = current_transaction.account_name.textContent ?? ""
current_transaction.placeholder_product_name = current_transaction.product_name.textContent ?? ""

function changeSlide(name: string) { document.querySelector<HTMLElement>(`.slide[data-slide="${name}"]`)?.scrollIntoView({block: "nearest"}) }

const slideshow = document.querySelector<HTMLElement>('.slideshow')
const observer = new IntersectionObserver((entries) => {
	let activated = entries.reduce((max, entry) => {
		return (entry.intersectionRatio > max.intersectionRatio) ? entry : max
	})
	if (activated.intersectionRatio > 0) {
		slideshow!.parentElement!.dataset.activeSlide = (activated.target as HTMLElement).dataset.slide
	}
}, {
	root: slideshow,
	threshold: 0.5,
})
slideshow?.querySelectorAll('.slide').forEach(e => observer.observe(e))
document.querySelectorAll<HTMLElement>('.slide-indicator').forEach(e => {
	e.addEventListener('click', _ => { changeSlide(e.dataset.slide ?? '') })
})

document.querySelector<HTMLButtonElement>('#new-transaction .undo')?.addEventListener('click', _ => {
	current_transaction.reset()
	current_transaction.clear_timeout()
})

current_transaction.element.style.animationDuration = TRANSACTION_TIMEOUT.toString()

const multiplier = {
	element: document.getElementById('transaction-multiplier')! as HTMLElement,

	get value(): number {
		const amount = parseInt(multiplier.element.textContent ?? '1')
		if (!amount) { return 1 }
		return amount
	},
	set value(value: number) {
		multiplier.element.textContent = value.toString()
	},

	selectAll() {
		const selection = document.getSelection()
		selection?.removeAllRanges()
		const range = document.createRange()
		range.selectNodeContents(multiplier.element)
		selection?.addRange(range)

		multiplier.element.focus()
	}
}
multiplier.element.addEventListener('beforeinput', (e: InputEvent) => {
	console.log(e)
	if (e.inputType.startsWith('format')) {
		e.preventDefault()
	}
	if (e.inputType.startsWith('insert')) {
		switch (e.inputType) {
			case "insertText":
			case "insertReplacementText":
				if (!e.data?.match(/^\d+$/i)) {
					e.preventDefault()
				}
				break
			case "insertLineBreak":
			case "insertParagraph":
				multiplier.element.blur()
				e.preventDefault()
				break
			case "insertFromYank":
			case "insertFromDrop":
			case "insertFromPaste":
			case "insertFromPasteAsQuotation":
				const data = e.dataTransfer?.getData('text/plain')
				if (!data?.match(/^\d+$/i)) {
					e.preventDefault()
				}
				break
			default:
				e.preventDefault()
				break	
		}	
	}
})
multiplier.element.addEventListener('input', _ => {
	if (current_transaction.account) {
		current_transaction.account = current_transaction.account
	}
	if (current_transaction.product) {
		current_transaction.product = current_transaction.product
	}
})
multiplier.element.closest('div')?.addEventListener('click', _ => {multiplier.selectAll()})

Transaction.all() // registers undo buttons
Transaction.listen(event => {
	const account = Account.byId(event.account.toString())
	if (!account) { return }
	account.balance = event.balance
	account.blocked = !event.is_liquid
})

Account.all().forEach(account => account.element.addEventListener('click', _ => {
	if (account.blocked || account.disabled) { return }
	const alreadySelected = current_transaction.account_id === account.id
	current_transaction.account = !alreadySelected ? account : null
	if (!alreadySelected) { changeSlide('products') }
}))

Product.all().forEach(product => product.element.addEventListener('click', _ => {
	if (product.disabled) { return }
	const alreadySelected = current_transaction.product_id === product.id
	current_transaction.product = !alreadySelected ? product : null
	if (!alreadySelected) { changeSlide('accounts') }
}))
