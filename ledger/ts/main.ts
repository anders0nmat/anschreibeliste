
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
	form: document.getElementById('new-transaction')! as HTMLFormElement,
	account_name: document.querySelector<HTMLElement>('#new-transaction .account')!,
	product_name: document.querySelector<HTMLElement>('#new-transaction .product')!,
	placeholder_account_name: "",
	placeholder_product_name: "",
	timeout: undefined as number | undefined,
	/*
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
	},*/

	try_submit() {
		const account = Account.byId(current_transaction.form.elements['account'].value)
		const product = Product.byId(current_transaction.form.elements['product'].value)
		if (!account || !product) { return }
	
		const amount = parseInt(current_transaction.form.elements['amount'].value)

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
		current_transaction.form.reset()
		current_transaction.clear_timeout()
		multiplier.value = 1
		current_transaction.update()
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

	update() {
		const current_account = Account.byId(current_transaction.form.elements['account'].value)
		const current_product = Product.byId(current_transaction.form.elements['product'].value)
		
		const account_name = current_account?.name ?? current_transaction.placeholder_account_name
		const current_multiplier = current_transaction.form.elements['amount'].value
		const multiplier_text = current_multiplier !== "1" ? current_multiplier + 'x ' : ''

		const product_name = current_product ? multiplier_text + current_product.name : current_transaction.placeholder_product_name

		current_transaction.account_name.textContent = account_name
		current_transaction.product_name.textContent = product_name
		current_transaction.account_name.toggleAttribute('empty', current_account === null)
		current_transaction.product_name.toggleAttribute('empty', current_product === null)

		const products = current_transaction.form.elements['product'] as RadioNodeList
		products.forEach((e: HTMLInputElement) => {
			const product = Product.byId(e.value)
			if (product) {
				e.disabled = current_account ? !current_account.canAfford(product) : false
			}
		})

		const accounts = current_transaction.form.elements['account'] as RadioNodeList
		accounts.forEach((e: HTMLInputElement) => {
			const account = Account.byId(e.value)
			if (account) {
				e.disabled = account.blocked || (current_product ? !account.canAfford(current_product) : false)
			}
		})

		if (current_account || current_product) {
			current_transaction.set_timeout()
		}
		if (current_account && current_product) {
			current_transaction.try_submit()
		}
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

Transaction.all() // registers undo buttons
Transaction.listen(event => {
	const account = Account.byId(event.account.toString())
	if (!account) { return }
	account.balance = event.balance
	account.blocked = !event.is_liquid
})

Account.all().forEach(account => account.element.addEventListener('click', _ => {
	if (account.blocked || account.disabled) { return }
	if (current_transaction.form.elements['account'].value === account.id) {
		current_transaction.form.elements['account'].value = ""
	}
	else {
		changeSlide('products')
	}
}))

Product.all().forEach(product => product.element.addEventListener('click', _ => {
	if (product.disabled) { return }
	if (current_transaction.form.elements['product'].value === product.id) {
		current_transaction.form.elements['product'].value = ""
	}
	else {
		changeSlide('accounts')
	}
}))

/* ===== Progressive enhancement ===== */

// Better transaction multiplier

const multiplier = {
	element: document.querySelector('#transaction-multiplier > span')! as HTMLElement,
	input: document.querySelector('#transaction-multiplier input')! as HTMLInputElement,

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
	multiplier.input.value = multiplier.value.toString()
	current_transaction.update()
})
multiplier.element.closest('div')?.addEventListener('click', _ => {multiplier.selectAll()})
multiplier.input.parentElement?.classList.add('visually-hidden')
multiplier.element.classList.remove('css-hidden')

// Hide submit button (because of auto-submit)

current_transaction.element.querySelector('button[type="submit"]')!.classList.add('css-hidden')

// Show form selection & auto-submit

Array.from(current_transaction.form.elements)
	.filter((element: HTMLInputElement) => ['product', 'account', 'amount'].includes(element.name))
	.forEach((element: HTMLInputElement) => {
		element.addEventListener('change', ev => {
			current_transaction.update()
		})
	})

// Horizontal Items

document.querySelector('.slideshow')!.classList.add('horizontal')

// Dont preserve selection between page refresh

current_transaction.form.reset()
