import { _set_money, config, HTMLWrapper } from './base.js';
const SUBMIT_OVERLAY_DURATION = config().submit_overlay;
function getRadioGroup(formElements, name) {
    const elements = formElements[name];
    if (elements instanceof RadioNodeList) {
        return {
            elements: Array.from(elements),
            get value() { return elements.value; }
        };
    }
    if (elements instanceof HTMLInputElement) {
        return {
            elements: [elements],
            get value() { return elements.value; }
        };
    }
    return {
        elements: [],
        get value() { return ''; }
    };
}
class Status extends HTMLWrapper {
    error() { this.element.dataset.status = "failure"; }
    success() {
        this.element.dataset.status = "success";
        setTimeout(_ => this.element.remove(), SUBMIT_OVERLAY_DURATION);
    }
}
export class Transaction extends HTMLWrapper {
    static template = 'transaction-template';
    static all_selector = '#transactions .transaction';
    static api = config().transaction;
    static csrf_token = document.querySelector('[name=csrfmiddlewaretoken]').value;
    static async post(url, body, idempotency_key = undefined) {
        return fetch(url, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": this.csrf_token,
                "Idempotency-Key": idempotency_key ?? Date.now().valueOf().toString(),
                "Accept": "application/json",
            },
            body: JSON.stringify(body),
        });
    }
    static reconnect_interval = undefined;
    static event_source = undefined;
    static listen(ontransaction, reconnect = false) {
        const url = new URL(this.api.events, document.location.origin);
        const all_transaction_ids = this.all().map(t => parseInt(t.id));
        if (reconnect && all_transaction_ids.length > 0) {
            const max_transaction_id = Math.max(...all_transaction_ids).toString();
            url.searchParams.set('last_transaction', max_transaction_id);
        }
        this.event_source = new EventSource(url);
        this.event_source.addEventListener('reload', _ => { location.reload(); });
        this.event_source.addEventListener('create', event => {
            const data = JSON.parse(event.data);
            console.log("received server event:", data);
            const confirmed_transaction = data.idempotency_key !== undefined && Transaction.from(document.querySelector(`.transaction[data-pending-id="${data.idempotency_key}"]`));
            if (confirmed_transaction) {
                confirmed_transaction.pendingId = null;
                confirmed_transaction.account = data.account_name;
                confirmed_transaction.amount = data.amount;
                confirmed_transaction.reason = data.reason;
                confirmed_transaction.can_revert = data.related === undefined;
            }
            else {
                const new_transaction = Transaction.create();
                new_transaction.id = data.id.toString();
                new_transaction.account = data.account_name;
                new_transaction.amount = data.amount;
                new_transaction.reason = data.reason;
                new_transaction.can_revert = data.related === undefined;
                new_transaction.status?.element.remove();
                document.getElementById('transactions').prepend(new_transaction.element);
            }
            const related_transaction = data.related !== undefined && Transaction.from(document.querySelector(`.transaction:has([name="transaction"][value="${data.related}"])`));
            if (related_transaction) {
                related_transaction.can_revert = false;
            }
            if (ontransaction) {
                ontransaction(data);
            }
        });
        this.event_source.addEventListener('open', _ => {
            // Successful connection, do not try to reconnect anymore
            clearInterval(this.reconnect_interval);
            this.reconnect_interval = undefined;
        });
        this.event_source.addEventListener('error', _ => {
            if (this.event_source?.readyState == EventSource.CLOSED) {
                // Browser will not retry on its own
                // Retry every 10s
                if (this.reconnect_interval === undefined) {
                    this.reconnect_interval = setInterval(() => {
                        this.listen(ontransaction);
                    }, 10_000);
                }
            }
        });
    }
    static async submit(request) {
        const idempotency_key = Date.now().valueOf().toString();
        const pending_transaction = Transaction.create();
        pending_transaction.account = request.account_name;
        pending_transaction.amount = request.kind == "withdraw" ? -request.balance : request.balance;
        pending_transaction.reason = request.reason;
        pending_transaction.can_revert = true;
        pending_transaction.pendingId = idempotency_key;
        document.getElementById('transactions').prepend(pending_transaction.element);
        let url = '';
        let body = {};
        if (request.kind == "product") {
            url = this.api.order;
            body = {
                account: request.account_id,
                product: request.product_id,
                ...(request.amount && { amount: request.amount }),
                ...(request.invert_member && { invert_member: request.invert_member })
            };
        }
        else {
            url = request.kind == 'deposit' ? this.api.deposit : this.api.withdraw;
            body = {
                account: request.account_id,
                amount: request.balance,
                reason: request.reason,
            };
        }
        const response = await Transaction.post(url, body, idempotency_key);
        if (!response.ok) {
            pending_transaction.status.error();
            pending_transaction.element.toggleAttribute("error", true);
            return;
        }
        const { transaction_id } = await response.json();
        pending_transaction.id = transaction_id;
        pending_transaction.status.success();
    }
    static attachNew(form_element, account_getter, product_getter, onInputChange) {
        const account_radios = getRadioGroup(form_element.elements, 'account');
        const product_radios = getRadioGroup(form_element.elements, 'product');
        const amount_input = form_element.elements['amount'];
        const invert_input = form_element.elements['invert_member'];
        const selected_account = form_element.elements['selected_account'];
        const selected_product = form_element.elements['selected_product'];
        [...account_radios.elements, ...product_radios.elements, amount_input, invert_input].forEach((e) => {
            e.addEventListener('change', _ => {
                const account = account_getter(account_radios.value);
                const product = product_getter(product_radios.value);
                // Update selection display
                selected_account.value = account?.name ?? '';
                const amount_string = amount_input.valueAsNumber > 1 ? amount_input.value + 'x ' : '';
                const invert_string = invert_input.checked ? account?.isMember ? 'Für Extern: ' : 'Für Clubbi: ' : '';
                selected_product.value = product ? invert_string + amount_string + product.name : '';
                // Disable products & accounts according to price/budget
                product_radios.elements.forEach((e) => {
                    const product = product_getter(e.value);
                    if (product) {
                        e.disabled = account !== null && !account.canAfford(product);
                    }
                });
                account_radios.elements.forEach((e) => {
                    const account = account_getter(e.value);
                    if (account) {
                        e.disabled = product ? !account.canAfford(product) : account.budget <= 0;
                    }
                });
                if (onInputChange) {
                    onInputChange(e);
                }
                // Auto-submit if both are present
                if (account && product) {
                    form_element.requestSubmit();
                }
            });
        });
        form_element.addEventListener('reset', _ => {
            // Disable products & accounts according to price/budget
            product_radios.elements.forEach((e) => {
                const product = product_getter(e.value);
                if (product) {
                    e.disabled = false;
                }
            });
            account_radios.elements.forEach((e) => {
                const account = account_getter(e.value);
                if (account) {
                    e.disabled = account.budget <= 0;
                }
            });
        });
    }
    static attachRevert(form_element) {
        if (!form_element) {
            form_element = document.getElementById('transaction-revert');
        }
        form_element.addEventListener('submit', ev => {
            ev.preventDefault();
            const transaction = ev.submitter.value;
            Transaction.post(this.api.revert, { transaction: transaction });
        });
    }
    static attachCustom(form_element) {
    }
    get id() { return this.element.querySelector('button[name="transaction"]').value; }
    get pendingId() { return this.element.dataset.pendingId ?? ''; }
    set id(value) {
        if (value === null) {
            this.element.querySelector('button[name="transaction"]').value = "";
        }
        else {
            this.element.querySelector('button[name="transaction"]').value = value;
        }
    }
    set pendingId(value) {
        if (value === null) {
            delete this.element.dataset.pendingId;
        }
        else {
            this.element.dataset.pendingId = value;
        }
    }
    set account(value) {
        const accountElement = this.element.querySelector('.account');
        accountElement.textContent = value;
    }
    set reason(value) {
        const reasonElement = this.element.querySelector('.reason');
        reasonElement.textContent = value;
    }
    set amount(value) {
        _set_money(this.element.querySelector('.money'), value);
    }
    set can_revert(value) {
        this.element.querySelector('.undo').disabled = !value;
    }
    get status() { return Status.from(this.element.querySelector('.status')); }
}
