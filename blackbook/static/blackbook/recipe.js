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
// An array of [name, element] pairs, for faster search
const search_items = [...document.querySelectorAll('#recipes a.recipe')].map(e => [e.textContent ?? '', e]);
search_bar.addEventListener('input', debounce(_ => {
    const searchTerms = search_bar.value.toLowerCase().split(' ');
    search_items.forEach(([name, element]) => {
        const matches = searchTerms.every(term => name.toLocaleLowerCase().includes(term));
        element.style.display = matches ? '' : 'none';
    });
}, 50));
