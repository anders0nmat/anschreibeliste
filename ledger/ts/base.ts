
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

export function _cloneTemplate(id: string): DocumentFragment {
	const template = document.getElementById(id) as HTMLTemplateElement
	return template.content.cloneNode(true) as DocumentFragment
}
