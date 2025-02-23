
class DrunkMoney extends HTMLElement {
	static observedAttributes = ['amount']

	connectedCallback() {
		const money_template = (document.getElementById(`${this.tagName.toLowerCase()}-template`)! as HTMLTemplateElement).content.cloneNode(true) as DocumentFragment
		this.appendChild(money_template)
		this._update()
	}
	attributeChangedCallback(_name, _oldValue, _newValue: string) {
		if (this.childElementCount == 0) { return }
		this._update()
	}
	_update() {
		const amount = parseInt(this.getAttribute('amount') ?? '0')
		const padded = Math.abs(amount).toString().padStart(3, '0')
		this.toggleAttribute('negative', amount < 0)
		this.querySelector('.wholes')!.textContent = padded.slice(0, -2)
		this.querySelector('.cents')!.textContent = padded.slice(-2)
	}

	get amount(): number { return parseInt(this.getAttribute('amount') ?? '0') ?? 0 }
	set amount(value: number) { this.setAttribute('amount', value.toString()) }
}
window.customElements.define('drunk-money', DrunkMoney)

class DrunkTransaction extends HTMLElement {
	constructor() {
		super()

		//const drunk_template: HTMLElement = (document.getElementById(`${this.tagName.toLowerCase()}-template`) as HTMLTemplateElement).content.cloneNode(true) as HTMLElement
		//if (this.childElementCount == 0) {
		//	this.appendChild(drunk_template)
		//}
	}

	connectedCallback() {
		console.log("DrunkTransaction is connected")
	}

	get account(): string { return this.querySelector('.name')!.textContent ?? '' }
	set account(value: string) { this.querySelector('.name')!.textContent = value }

	get reason(): string { return this.querySelector('.reason')!.textContent ?? '' }
	set reason(value: string) { this.querySelector('.reason')!.textContent = value }

	get money(): DrunkMoney { return this.querySelector<DrunkMoney>('drunk-money')! }

	get transaction_id(): string | null { return this.getAttribute('transaction-id') }
	set transaction_id(value: string | null) {
		if (value === null) {
			this.removeAttribute('transaction-id')
		}
		else {
			this.setAttribute('transaction-id', value)
		}
	}

	get pending_id(): string | null { return this.getAttribute('pending-id') }
	set pending_id(value: string | null) {
		if (value === null) {
			this.removeAttribute('pending-id')
		}
		else {
			this.setAttribute('pending-id', value)
		}
	}

	revert() {
		console.log("reverting", this)
	}
}
window.customElements.define('drunk-transaction', DrunkTransaction)


let c = 0
document.getElementById('send-event')!.addEventListener('click', _ => {
	fetch(`/test/send_event/?counter=${c}`)
	c += 1
})

let events = new EventSource('/test/events/')
events.onmessage = ev => {
	console.log(ev.data)
	const li = document.createElement('li')
	li.append(ev.data)
	document.getElementById('event-list')!.append(li)
}


