const calculator = document.querySelector('#calculator-dialog');
const calculatorOpen = document.querySelector('#calculator-open');
const calculatorClose = document.querySelector('#calculator-close');
const calculatorClear = document.querySelector('.calculator-clear');
const calculatorTotal = document.querySelector('#calculator-total');
const calculatorSelections = document.querySelector('#calculator-selections');
const calculatorModeButtons = document.querySelectorAll('[data-calculator-mode]');
const calculatorProducts = document.querySelectorAll('[data-calculator-product]');
const calculatorTimeoutProgress = document.querySelector('.calculator-timeout-progress');
const calculatorItems = new Map();
const formatCalculatorMoney = cents => new Intl.NumberFormat('de-DE', {
    style: 'currency',
    currency: 'EUR',
}).format(cents / 100);
let calculatorMode = 'external';
let calculatorTimeout;

function resetCalculator() {
    calculatorItems.clear();
    calculatorMode = 'external';
    calculatorModeButtons.forEach(button => {
        button.classList.toggle('is-active', button.dataset.calculatorMode === 'external');
    });
    renderCalculator();
    if (calculatorTimeoutProgress) {
        calculatorTimeoutProgress.classList.add('is-paused');
        calculatorTimeoutProgress.style.animation = 'none';
    }
}

function resetCalculatorTimeout() {
    clearTimeout(calculatorTimeout);
    calculatorTimeout = setTimeout(() => calculator?.close(), 30000);
    if (calculatorTimeoutProgress) {
        calculatorTimeoutProgress.classList.remove('is-paused');
        calculatorTimeoutProgress.style.animation = 'none';
        calculatorTimeoutProgress.offsetHeight; // force reflow
        calculatorTimeoutProgress.style.animation = '';
    }
}

function renderCalculator() {
    let total = 0;
    calculatorSelections.replaceChildren();
    for (const item of calculatorItems.values()) {
        const price = item.mode === 'member' ? item.memberCost : item.cost;
        total += item.amount * price;
        const row = document.createElement('li');
        row.className = 'calculator-selection';
        const name = document.createElement('span');
        name.className = 'calculator-selection-name';
        name.textContent = `${item.amount}x ${item.name}`;
        if (item.mode === 'external') {
            const badge = document.createElement('span');
            badge.className = 'tag';
            badge.textContent = 'Extern';
            name.append(' ', badge);
        }
        const itemPrice = document.createElement('span');
        itemPrice.className = 'calculator-selection-price';
        itemPrice.textContent = formatCalculatorMoney(item.amount * price);
        row.append(name, itemPrice);
        calculatorSelections.append(row);
    }
    calculatorTotal.textContent = formatCalculatorMoney(total);
}

calculatorModeButtons.forEach(button => button.addEventListener('click', () => {
    calculatorMode = button.dataset.calculatorMode;
    calculatorModeButtons.forEach(other => other.classList.toggle('is-active', other === button));
    resetCalculatorTimeout();
}));

calculatorProducts.forEach(product => product.addEventListener('click', () => {
    const key = `${product.dataset.productId}:${calculatorMode}`;
    const item = calculatorItems.get(key) ?? {
        name: product.dataset.name,
        cost: parseInt(product.dataset.cost ?? '0'),
        memberCost: parseInt(product.dataset.memberCost ?? '0'),
        mode: calculatorMode,
        amount: 0,
    };
    item.amount += 1;
    calculatorItems.set(key, item);
    renderCalculator();
    resetCalculatorTimeout();
}));

calculatorClear?.addEventListener('click', () => {
    calculatorItems.clear();
    renderCalculator();
    resetCalculatorTimeout();
});

calculatorOpen?.addEventListener('click', () => {
    calculator?.showModal();
    resetCalculatorTimeout();
});

calculatorClose?.addEventListener('click', () => calculator?.close());
calculator?.addEventListener('click', event => {
    if (event.target === calculator) {
        calculator.close();
    }
});
calculator?.addEventListener('pointerdown', resetCalculatorTimeout);
calculator?.addEventListener('keydown', resetCalculatorTimeout);
calculator?.addEventListener('scroll', resetCalculatorTimeout, true);
calculator?.addEventListener('close', () => {
    clearTimeout(calculatorTimeout);
    resetCalculator();
});

resetCalculator();
