/*
    Controls how long the confirmation/error overlay is shown after submitting a transaction.

    Unit: ms (milliseconds)
    Default value: 1_500
*/
const SUBMIT_OVERLAY_DURATION = 1_500;
import { _money, _span } from './base.js';
export class Transaction {
    static async post(url, body, idempotency_key = undefined) {
        return fetch(url, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": this.csrf_token,
                "Idempotency-Key": idempotency_key ?? Date.now().valueOf().toString(),
            },
            body: JSON.stringify(body),
        });
    }
    static _undo(can_revert) {
        const result = this.undo_template.content.cloneNode(true);
        result.querySelector('button').disabled = !can_revert;
        return result;
    }
    static _status() {
        return this.status_template.content.cloneNode(true);
    }
    static add(response) {
        const account = _span(response.account_name, "account");
        const reason = _span(response.reason, "reason");
        const amount = _money(response.cost);
        const undo = this._undo(response.can_revert);
        let item = null;
        if (response.id) {
            item = response.idempotency_key !== undefined ? this.container.querySelector(`.transaction[data-pending-id="${response.idempotency_key}"]`) : null;
            if (item) {
                delete item.dataset.pendingId;
                item.querySelectorAll(':scope > :not(.status)').forEach(e => e.remove());
                item.prepend(account, reason, amount, undo);
            }
            else {
                item = document.createElement('li');
                item.classList.add('transaction');
                item.dataset.transactionId = response.id;
                this.container.prepend(item);
                item.append(account, reason, amount, undo);
            }
        }
        else {
            item = document.createElement('li');
            item.classList.add('transaction');
            item.dataset.pendingId = response.idempotency_key;
            this.container.prepend(item);
            const status = this._status();
            item.append(account, reason, amount, undo, status);
        }
        if (response.id) {
            if (this.objects.has(response.id)) {
                return this.objects.get(response.id);
            }
            else {
                const transaction = new this(item);
                this.objects.set(transaction.id, transaction);
                return transaction;
            }
        }
        else {
            return new this(item);
        }
    }
    static async submit(request) {
        const idempotency_key = Date.now().valueOf().toString();
        const pending_transaction = Transaction.add({
            account_name: request.account_name,
            cost: request.kind == "withdraw" ? -request.balance : request.balance,
            reason: request.reason,
            idempotency_key: idempotency_key,
            can_revert: true,
        });
        let url = '';
        let body = {};
        if (request.kind === "product") {
            url = TRANSACTION_PRODUCT_URL;
            body = {
                account: request.account_id,
                product: request.product_id,
                ...(request.amount && { amount: request.amount })
            };
        }
        else {
            url = TRANSACTION_CUSTOM_URL;
            body = {
                account: request.account_id,
                amount: request.balance,
                type: request.kind,
            };
        }
        const response = await Transaction.post(url, body, idempotency_key);
        if (!response.ok) {
            pending_transaction.status.dataset.status = "failure";
            pending_transaction.element.toggleAttribute('error', true);
            return;
        }
        const { transaction_id } = await response.json();
        pending_transaction.element.dataset.transactionId = transaction_id;
        Transaction.objects.set(pending_transaction.id, pending_transaction);
        pending_transaction.status.dataset.status = "success";
        await delay(SUBMIT_OVERLAY_DURATION);
        pending_transaction.status?.remove();
    }
    static event_source = undefined;
    static listen(ontransaction) {
        this.event_source = new EventSource(TRANSACTION_EVENT_URL);
        this.event_source.addEventListener('create', event => {
            const data = JSON.parse(event.data);
            console.log("received server event: ", data);
            Transaction.add({
                account_name: data.account_name,
                cost: data.amount,
                reason: data.reason,
                id: data.id.toString(),
                idempotency_key: data.idempotency_key,
                can_revert: data.related === undefined
            });
            if (data.related !== undefined && Transaction.objects.has(data.related.toString())) {
                Transaction.objects.get(data.related.toString()).undo_button.disabled = true;
            }
            if (ontransaction) {
                ontransaction(data);
            }
        });
    }
    static status_template = document.getElementById('template-status');
    static undo_template = document.getElementById('template-undo');
    static csrf_token = document.querySelector('[name=csrfmiddlewaretoken]').value;
    static container = document.getElementById('transactions');
    static objects = new Map(Array.from(this.container.querySelectorAll('.transaction'), element => {
        const transaction = new this(element);
        return [transaction.id, transaction];
    }));
    element;
    constructor(element) {
        this.element = element;
        this.undo_button.addEventListener('click', _ => this.revert());
    }
    get id() { return this.element.dataset.transactionId ?? ''; }
    get undo_button() { return this.element.querySelector('.undo'); }
    get status() { return this.element.querySelector('.status'); }
    revert() {
        const id = parseInt(this.id);
        if (!id) {
            return;
        }
        Transaction.post(TRANSACTION_REVERT_URL, { transaction: id });
    }
}
async function delay(time) { return new Promise(resolve => setTimeout(resolve, time)); }
