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
    const searchTerms = splitQuoted(search_bar.value.toLowerCase());
    const matches = (metadata) => {
        return searchTerms.every(term => {
            const [value, op] = [...term.split(':', 2).reverse(), 'name'];
            let metavalue = metadata[op];
            if (!Array.isArray(metavalue)) {
                metavalue = [metavalue];
            }
            return metavalue.some(e => e.includes(value));
        });
    };
    search_items.forEach(([metadata, element]) => {
        element.style.display = matches(metadata) ? '' : 'none';
    });
}, 50));
