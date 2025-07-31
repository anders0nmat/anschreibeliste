
import { _money, _set_money, HTMLIdentifierWrapper } from "./base.js"

interface Product {
	totalCost(member: boolean): number
}

export class Account extends HTMLIdentifierWrapper {
	static all_selector: string = '#accounts .item'
	static id_attribute: string = 'data-account-id'
	static deselectAll() { this.all().forEach(acc => acc.selected = false) }
	static enableAll() { this.all().forEach(acc => acc.disabled = false) }

	radio: HTMLInputElement
	constructor(element: HTMLElement) {
		super(element)

		this.radio = element.querySelector<HTMLInputElement>('input[name="account"]')!
	}

	get id(): string { return this.element.dataset.accountId ?? '' }
	get name(): string { return this.element.querySelector('.name')?.textContent ?? '' }
	get isMember(): boolean { return 'member' in this.element.dataset }
	get credit(): number { return parseInt(this.element.dataset.credit ?? '0') }
	get budget(): number { return this.balance + this.credit }
	
	get balance(): number { return parseInt(this.element.dataset.balance ?? '0') }
	set balance(value: number) {
		this.element.dataset.balance = value.toString()
        _set_money(this.element.querySelector('.money')!, value)
	}

	get disabled(): boolean { return this.radio.disabled }
	set disabled(value: boolean) { this.radio.disabled = value }
	
	get selected(): boolean { return this.element.hasAttribute('selected') }
	set selected(value: boolean) { this.element.toggleAttribute('selected', value) }
	select() { this.selected = true }
	canAfford(product: Product): boolean { return this.budget >= product.totalCost(this.isMember) }
}

