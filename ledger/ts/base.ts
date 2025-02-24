/*
	Allows for conditional classes like
	`amount > 0 && "positive"`

	if `amount > 0` evaluates to false, `false` is passed down and ignored.
	if `amount > 0` evaluates to true, `"positive"` is passed down and added to the class list
*/
type HTMLClass = string | boolean
type HTMLClassList = HTMLClass | HTMLClass[]

/*
	Set attribute `key` to `value`.
	If `value` is boolean, set/remove `key` depending on boolean value
*/
type HTMLAttributeList = Record<string, string | boolean>

function _applyClassList(element: HTMLElement, classes: HTMLClassList) {
	if (!Array.isArray(classes)) { classes = [classes] }
	classes.forEach(e => { if (typeof e === "string") { element.classList.add(e) } })
}

function _applyAttributes(element: HTMLElement, attributes: HTMLAttributeList) {
	Object.entries(attributes).forEach(([k, v]) => {
		if (typeof v === "string") { element.setAttribute(k, v) }
		else { element.toggleAttribute(k, v) }
	})
}

export function _span(textContent: string, classList: HTMLClassList = [], attributes: HTMLAttributeList = {}): HTMLSpanElement {
	const span = document.createElement("span")
	_applyClassList(span, classList)
	_applyAttributes(span, attributes)
	span.textContent = textContent
	return span
}

export function _money(balance: number): HTMLElement {
	const amount_string = Math.abs(balance).toString().padStart(3, '0')

	const money = _span('', ['money'], {negative: balance < 0})
	const wholes = _span(amount_string.slice(0, -2), 'wholes')
	const cents = _span(amount_string.slice(-2), 'cents')
	
	money.append(wholes, cents)		
	return money
}

export function _set_money(element: HTMLElement, amount: number) {
	element.toggleAttribute('negative', amount < 0)

	const amount_string = Math.abs(amount).toString().padStart(3, '0')
	element.querySelector('.wholes')!.textContent = amount_string.slice(0, -2)
	element.querySelector('.cents')!.textContent = amount_string.slice(-2)
}

export function _cloneTemplate(id: string): DocumentFragment {
	const template = document.getElementById(id) as HTMLTemplateElement
	return template.content.cloneNode(true) as DocumentFragment
}

interface GenericHTMLWrapper<T> {
	new (_: HTMLElement): T
	template: string
	all_selector: string

	from(element: null): null
	from<T extends HTMLWrapper>(this: GenericHTMLWrapper<T>, element: HTMLElement): T
	from<T extends HTMLWrapper>(this: GenericHTMLWrapper<T>, element: HTMLElement | null): T | null
	create<T extends HTMLWrapper>(this: GenericHTMLWrapper<T>): T
	all<T extends HTMLWrapper>(this: GenericHTMLWrapper<T>): T[]
	get<T extends HTMLWrapper>(this: GenericHTMLWrapper<T>, selector: string): T | null
}

interface GenericIdentifierWrapper<T> extends GenericHTMLWrapper<T> {
	id_attribute: string
}

export class HTMLWrapper {
	static from(element: null): null;
	static from<T extends HTMLWrapper>(this: GenericHTMLWrapper<T>, element: HTMLElement): T;
	static from<T extends HTMLWrapper>(this: GenericHTMLWrapper<T>, element: HTMLElement | null): T | null;
	static from<T extends HTMLWrapper>(this: GenericHTMLWrapper<T>, element: HTMLElement | null): T | null {
		return element !== null ? new this(element) : null
	}

	static template: string
	static create<T extends HTMLWrapper>(this: GenericHTMLWrapper<T>): T {
		const element = _cloneTemplate(this.template).firstElementChild as HTMLElement
		return new this(element)
	}

	static all_selector: string
	static all<T extends HTMLWrapper>(this: GenericHTMLWrapper<T>): T[] {
		return Array.from(document.querySelectorAll<HTMLElement>(this.all_selector)).map(e => new this(e))
	}

	static get<T extends HTMLWrapper>(this: GenericHTMLWrapper<T>, selector: string): T | null {
		const element = document.querySelector<HTMLElement>(selector)
		return element !== null ? new this(element) : null
	}

	element: HTMLElement
	constructor(element: HTMLElement) {
		this.element = element
	}
}

export class HTMLIdentifierWrapper extends HTMLWrapper {
	static id_attribute: string
	static byId<T extends HTMLIdentifierWrapper>(this: GenericIdentifierWrapper<T>, id: string | null): T | null {
		return id !== null
			? this.get(`${this.all_selector}[${this.id_attribute}="${id}"]`)
			: null
	}
}
