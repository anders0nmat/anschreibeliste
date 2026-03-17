const search_bar = document.querySelector('input[type="search"]');
function debounce(func, wait, immediate = false) {
    var timeout;
    return function (...args) {
        var context = this;
        var later = function () {
            timeout = null;
            if (!immediate)
                func.apply(context, args);
        };
        var callNow = immediate && !timeout;
        clearTimeout(timeout ?? undefined);
        timeout = setTimeout(later, wait);
        if (callNow)
            func.apply(context, args);
    };
}
function splitQuoted(str) {
    return [...str.matchAll(/([^'"\s]+)|"(.*?)"|'(.*?)'/g)]
        .map(match => match.slice(1).find(e => e !== undefined))
        .filter(e => e !== undefined);
}
// An array of [name, element] pairs, for faster search
const search_items = [...document.querySelectorAll('#recipes a.recipe')]
    .map(e => [JSON.parse(e.querySelector('script')?.textContent ?? '{}'), e]);
search_bar.addEventListener('input', debounce(_ => {
    search_items.forEach(([_, e]) => delete e.dataset.selected);
    const searchTerms = splitQuoted(search_bar.value.toLowerCase());
    const matches = (metadata) => {
        return searchTerms.every(term => {
            const invert = term.startsWith('-');
            if (invert) {
                term = term.slice(1);
            }
            const [value, op] = [...term.split(':', 2).reverse(), 'name'];
            let metavalue = metadata[op];
            if (!Array.isArray(metavalue)) {
                metavalue = [metavalue];
            }
            return invert != metavalue.some(e => e.includes(value));
        });
    };
    search_items.forEach(([metadata, element]) => {
        element.style.display = matches(metadata) ? '' : 'none';
    });
}, 50));
async function selectWithAnimation(list, index) {
    return new Promise(resolve => {
        const DURATION = 2500;
        const MIN_ELEMENTS = 50;
        let start;
        list.forEach(e => delete e.dataset.selected);
        function animate(timestamp) {
            if (start === undefined) {
                start = timestamp;
            }
            const ease = x => 1 - (1 - x) * (1 - x);
            const progress = (timestamp - start) / DURATION;
            const progressInt = index + list.length * Math.ceil(MIN_ELEMENTS / list.length);
            if (progress < 1) {
                const elementIndex = Math.floor(ease(progress) * progressInt) % list.length;
                list.forEach(e => delete e.dataset.highlight);
                list[elementIndex].dataset.highlight = "";
                list[elementIndex].scrollIntoView({
                    //behavior: "smooth",
                    block: "center"
                });
                requestAnimationFrame(animate);
            }
            else {
                list.forEach(e => delete e.dataset.highlight);
                list[index].dataset.selected = "";
                list[index].scrollIntoView({
                    //behavior: "smooth",
                    block: "center"
                });
                resolve();
            }
        }
        requestAnimationFrame(animate);
    });
}
const random_button = document.querySelector('#random');
random_button.addEventListener("click", _ => {
    document.querySelectorAll('.recipe[data-selected]').forEach(e => delete e.dataset.selected);
    const visible_recipes = search_items.map(e => e[1]).filter(e => e.style.display !== "none");
    const selected_index = Math.floor(Math.random() * visible_recipes.length);
    random_button.disabled = true;
    selectWithAnimation(visible_recipes, selected_index)
        .then(_ => random_button.disabled = false);
});
