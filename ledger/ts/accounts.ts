
import { _money } from "./base.js"

export class Account {
	static deselectAll() { this.objects.forEach(e => e.selected = false) }
	static enableAll() { this.objects.forEach(e => e.disabled = false) }

	static container = document.getElementById('accounts')!
	static objects = new Map<string, Account>(
		Array.from(this.container.querySelectorAll<HTMLElement>('.item'), element => {
			const account = new this(element)
			return [account.id, account]
		}))

	element: HTMLElement
	constructor(element: HTMLElement) {
		this.element = element
	}

	get id(): string { return this.element.dataset.accountId ?? '' }
	get name(): string { return this.element.querySelector('.name')?.textContent ?? '' }
	get isMember(): boolean { return 'member' in this.element.dataset }
	get credit(): number { return parseInt(this.element.dataset.credit ?? '0') }
	get budget(): number { return this.balance + this.credit }
	
	get balance(): number { return parseInt(this.element.dataset.balance ?? '0') }
	set balance(value: number) {
		this.element.dataset.balance = value.toString()
		this.element.querySelector<HTMLElement>('.money')!.replaceWith(_money(value))
	}
	
	get blocked(): boolean { return this.element.hasAttribute('blocked') }
	set blocked(value: boolean) { this.element.toggleAttribute('blocked', value) }

	get disabled(): boolean { return this.element.hasAttribute('disabled') }
	set disabled(value: boolean) { this.element.toggleAttribute('disabled', value) }
	
	get selected(): boolean { return this.element.hasAttribute('selected') }
	set selected(value: boolean) { this.element.toggleAttribute('selected', value) }
	select() { this.selected = true }

	//canAfford(product: Product): boolean { return this.budget >= product.totalCost(this) }
}

