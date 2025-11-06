
const search_bar = document.querySelector<HTMLInputElement>('.toolbar input[type="search"]')!

function debounce<Args extends any[], F extends (...args: Args) => any>(func: F, wait: number, immediate: boolean = false) {
    var timeout: ReturnType<typeof setTimeout> | null
    return function(this: ThisParameterType<F>, ...args: Parameters<F>) {
		var context = this
        var later = function() {
            timeout = null
            if (!immediate) func.apply(context, args)
        }
        var callNow = immediate && !timeout
        clearTimeout(timeout ?? undefined)
        timeout = setTimeout(later, wait)
        if (callNow) func.apply(context, args)
    }
}

// An array of [name, element] pairs, for faster search
const search_items: [string, HTMLElement][] = [...document.querySelectorAll<HTMLElement>('#recipes a.item')].map(e => [e.textContent ?? '', e])

search_bar.addEventListener('input', debounce(_ => {
	const searchTerms = search_bar.value.toLowerCase().split(' ')

	search_items.forEach(([name, element]) => {
		const matches = searchTerms.every(term => name.toLocaleLowerCase().includes(term))
		element.style.display = matches ? '' : 'none'
	})
}, 50))
