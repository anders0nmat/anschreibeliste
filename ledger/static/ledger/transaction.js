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
function getIdempotencyKey() {
    return Date.now().valueOf().toString();
}
function productReason(account, product, amount, invert_member = false) {
    let reason = '';
    if (invert_member) {
        reason += account?.isMember ? 'Für Extern: ' : 'Für Clubbi: ';
    }
    if (amount > 1) {
        reason += `${amount}x `;
    }
    if (product) {
        reason += product.name;
    }
    return reason;
}
function totalProductCost(request) {
    const useMemberCost = request.account.isMember != request.invertMember;
    const singleProductCost = useMemberCost ? request.product.memberCost : request.product.cost;
    return request.amount * singleProductCost;
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
    static ping_nonce = undefined;
    static ping_eventsource() {
        try {
            this.ping_nonce = Date.now().valueOf();
            fetch(this.api.ping + `?nonce=${this.ping_nonce}`);
            setTimeout(_ => {
                if (this.ping_nonce !== undefined) {
                    console.log("Transaction eventsource ping failed, reconnecting...");
                    this.reconnect();
                }
                else {
                    console.log(("Transaction eventsource ping succeded"));
                }
            }, 500);
        }
        catch {
            // No internet?
            // Server down?
        }
    }
    static reconnect_interval = undefined;
    static event_source = undefined;
    static eventsource_handlers = {};
    static async reconnect() {
        this.event_source?.close();
        await this.listen(this.eventsource_handlers.ontransaction, true);
    }
    static attachPing() {
        document.addEventListener('visibilitychange', ev => {
            if (document.visibilityState == "visible") {
                this.ping_eventsource();
            }
        });
    }
    static async listen(ontransaction, reconnect = false) {
        const url = new URL(this.api.events, document.location.origin);
        this.eventsource_handlers.ontransaction = ontransaction;
        const all_transaction_ids = this.all().map(t => parseInt(t.id));
        if (reconnect && all_transaction_ids.length > 0) {
            const max_transaction_id = Math.max(...all_transaction_ids).toString();
            url.searchParams.set('last_transaction', max_transaction_id);
        }
        this.event_source = new EventSource(url);
        this.event_source.addEventListener('ping', event => {
            const nonce = parseInt(event.data);
            if (nonce == this.ping_nonce) {
                this.ping_nonce = undefined;
            }
        });
        this.event_source.addEventListener('reload', _ => { location.reload(); });
        this.event_source.addEventListener('create', event => {
            const data = JSON.parse(event.data);
            console.log("received server event:", data);
            const confirmed_transaction = data.idempotency_key && Transaction.fromQuery(`.transaction[data-pending-id="${data.idempotency_key}"]`);
            if (confirmed_transaction) {
                confirmed_transaction.applyServerEvent(data);
            }
            else {
                const new_transaction = Transaction.create();
                new_transaction.applyServerEvent(data);
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
            console.log('Eventsource connected');
            clearInterval(this.reconnect_interval);
            this.reconnect_interval = undefined;
        });
        this.event_source.addEventListener('error', _ => {
            this.ping_nonce = undefined;
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
        pending_transaction.amount = (request.kind == 'withdraw' ? -1 : 1) * parseInt(request.balance.replace('.', '').padEnd(3, '0'));
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
    static async submitProduct(request) {
        const idempotency_key = getIdempotencyKey();
        const useMemberPrice = request.account.isMember != request.invertMember;
        const pending_transaction = Transaction.create();
        pending_transaction.account = request.account.name;
        pending_transaction.amount = -totalProductCost(request);
        pending_transaction.reason = productReason(request.account, request.product, request.amount, request.invertMember);
        pending_transaction.can_revert = true;
        pending_transaction.pendingId = idempotency_key;
        document.getElementById('transactions').prepend(pending_transaction.element);
        const response = await Transaction.post(this.api.order, {
            account: request.account.id,
            product: request.product.id,
            amount: request.amount,
            invert_member: request.invertMember,
        }, idempotency_key);
        if (!response.ok) {
            pending_transaction.status.error();
            pending_transaction.element.toggleAttribute('error', true);
            console.error(`Failed to submit product: Server returned ${response.status} ${response.statusText}`, await response.json());
            return;
        }
        const { transaction_id } = await response.json();
        pending_transaction.id = transaction_id;
        pending_transaction.status.success();
    }
    static attachNew({ form: form_element, getAccount, getProduct, onInputChange, onReset, accountLocked, timeout: timeout_duration, }) {
        form_element ??= document.getElementById('new-transaction');
        const timeout = timeout_duration ? {
            handler: undefined,
            set() {
                timeout.clear();
                timeout.handler = setTimeout(_ => form_element.reset(), timeout_duration);
                form_element.classList.add('timeout');
            },
            clear() {
                clearTimeout(timeout.handler);
                timeout.handler = undefined;
                form_element.classList.remove('timeout');
                form_element.offsetWidth;
            }
        } : undefined;
        if (timeout_duration) {
            form_element.style.animationDuration = timeout_duration.toString() + 'ms';
        }
        const account_radios = getRadioGroup(form_element.elements, 'account');
        const product_radios = getRadioGroup(form_element.elements, 'product');
        const amount_input = form_element.elements['amount'];
        const invert_input = form_element.elements['invert_member'];
        const selected_account = form_element.elements['selected_account'];
        const selected_product = form_element.elements['selected_product'];
        const submit_button = form_element.querySelector('button[type="submit"]');
        submit_button.classList.add('css-hidden');
        const updateSelection = (selected_account, selected_product) => {
            // Disable products & accounts according to price/budget
            product_radios.elements.forEach((e) => {
                const this_product = getProduct(e.value);
                if (this_product && selected_account) {
                    e.disabled = selected_account.budget < totalProductCost({
                        product: this_product,
                        account: selected_account,
                        amount: amount_input.valueAsNumber,
                        invertMember: invert_input.checked,
                    });
                }
                else {
                    e.disabled = false;
                }
            });
            account_radios.elements.forEach((e) => {
                const this_account = getAccount(e.value);
                if (this_account && selected_product) {
                    e.disabled = this_account.budget < totalProductCost({
                        product: selected_product,
                        account: this_account,
                        amount: amount_input.valueAsNumber,
                        invertMember: invert_input.checked,
                    });
                }
                else {
                    e.disabled = this_account ? this_account.budget <= 0 : false;
                }
            });
        };
        const all_elements = [...account_radios.elements, ...product_radios.elements, amount_input, invert_input];
        all_elements.forEach((e) => {
            e.addEventListener('change', _ => {
                const account = getAccount(account_radios.value);
                const product = getProduct(product_radios.value);
                // Update selection display
                selected_account.value = account?.name ?? '';
                selected_product.value = productReason(account, product, amount_input.valueAsNumber, invert_input.checked);
                updateSelection(account, product);
                onInputChange?.(e);
                if (account || product) {
                    timeout?.set();
                }
                // Auto-submit if both are present
                if (account && product) {
                    form_element.requestSubmit();
                }
            });
        });
        form_element.addEventListener('submit', ev => {
            ev.preventDefault();
            const account = getAccount(account_radios.value);
            const product = getProduct(product_radios.value);
            if (!account || !product) {
                // TODO : Should we reset the form here?
                return;
            }
            Transaction.submitProduct({
                account: account,
                product: product,
                amount: amount_input.valueAsNumber,
                invertMember: invert_input.checked,
            });
            form_element.reset();
            if (accountLocked?.()) {
                account_radios.elements.find(e => e.value == account.id)?.click();
            }
        });
        form_element.addEventListener('reset', r => {
            timeout?.clear();
            updateSelection(null, null);
            onReset?.(form_element);
        });
        return {
            form: form_element,
            updateSelection() {
                const account = getAccount(account_radios.value);
                const product = getProduct(product_radios.value);
                updateSelection(account, product);
            },
        };
    }
    static attachRevert(form_element) {
        form_element ??= document.getElementById('transaction-revert');
        form_element.addEventListener('submit', ev => {
            ev.preventDefault();
            const transaction = ev.submitter.value;
            Transaction.post(this.api.revert, { transaction: transaction });
        });
    }
    static attachCustom(form_element) {
    }
    applyServerEvent(data) {
        this.id = data.id.toString();
        this.pendingId = null;
        this.account = data.account_name;
        this.amount = data.amount;
        this.reason = data.reason;
        this.can_revert = data.related === undefined;
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
