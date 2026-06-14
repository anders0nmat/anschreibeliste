
const search_bar = document.querySelector<HTMLInputElement>('input[type="search"]')!

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

type StringOrArray = string | string[]

type StringArrayMap = {
    [key: string]: StringOrArray
}

function splitQuoted(str: string): string[] {
    return [...str.matchAll(/([^'"\s]+)|"(.*?)"|'(.*?)'/g)]
        .map(match => match.slice(1).find(e => e !== undefined))
        .filter(e => e !== undefined)
}

// An array of [name, element] pairs, for faster search
const search_items: [StringArrayMap, HTMLElement][] = [...document.querySelectorAll<HTMLElement>('#recipes a.recipe')]
    .map(e => [JSON.parse(e.querySelector('script')?.textContent ?? '{}'), e])

function search() {
    search_items.forEach(([_, e]) => delete e.dataset.selected)

    const searchTerms = splitQuoted(search_bar.value.toLowerCase())

    const matches = (metadata: StringArrayMap): boolean => {
        return searchTerms.every(term => {
            const invert = term.startsWith('-')
            if (invert) {
                term = term.slice(1)
            }
            const [value, op] = [...term.split(':', 2).reverse(), 'name']

            let metavalue = metadata[op]
            if (!Array.isArray(metavalue)) {
                metavalue = [metavalue]
            }

            return invert != metavalue.some(e => e.includes(value))
        })
    }

	search_items.forEach(([metadata, element]) => {        
        element.style.display = matches(metadata) ? '' : 'none'
	})
}

search_bar.addEventListener('input', debounce(_ => {
    updateFilters()
    search()
}, 50))

async function selectWithAnimation(list: HTMLElement[], index: number): Promise<void> {
    return new Promise<void>(resolve => {
        const DURATION = 2500
        const MIN_ELEMENTS = 50
        let start: number
        list.forEach(e => delete e.dataset.selected)
        function animate(timestamp: number) {
            if (start === undefined) {
                start = timestamp
            }

            const ease = x => 1 - (1 - x) * (1 - x)

            const progress = (timestamp - start) / DURATION
            const progressInt = index + list.length * Math.ceil(MIN_ELEMENTS / list.length)
            if (progress < 1) {
                const elementIndex = Math.floor(ease(progress) * progressInt) % list.length

                list.forEach(e => delete e.dataset.highlight)
                list[elementIndex].dataset.highlight = ""
                list[elementIndex].scrollIntoView({
                    block: "center"
                })
                requestAnimationFrame(animate)
            }
            else {
                list.forEach(e => delete e.dataset.highlight)
                list[index].dataset.selected = ""
                list[index].scrollIntoView({
                    block: "center"
                })
                resolve()
            }
        }

        requestAnimationFrame(animate)
    })
}


const random_button = document.querySelector<HTMLButtonElement>('#random')!
random_button.addEventListener("click", _ => {
    document.querySelectorAll<HTMLElement>('.recipe[data-selected]').forEach(e => delete e.dataset.selected)
    const visible_recipes = search_items.map(e => e[1]).filter(e => e.style.display !== "none")

    const selected_index = Math.floor(Math.random() * visible_recipes.length)
    
    random_button.disabled = true
    selectWithAnimation(visible_recipes, selected_index)
        .then(_ => random_button.disabled = false)
})


function updateFilters() {
    document.querySelectorAll<HTMLInputElement>('#filters input[type="checkbox"]').forEach(e => {
        const value = search_bar.value
        const terms = splitQuoted(value)
        const filter = e.dataset.filter!.toLowerCase()
        e.checked = terms.some(v => v.toLowerCase() == filter)
    })
}

document.querySelectorAll<HTMLInputElement>('#filters input[type="checkbox"]').forEach(e => {
    e.addEventListener('change', _ => {
        const old_value = search_bar.value
        const terms = splitQuoted(old_value)
        const filter = e.dataset.filter!.toLowerCase()
        if (e.checked) {
            if (!terms.some(v => v.toLowerCase() == filter)) {
                const quote = filter.includes(' ') ? '"' : ''
                search_bar.value += (search_bar.value ? ' ' : '') + quote + filter + quote
            }
        }
        else {
            search_bar.value = terms.filter(v => v.toLowerCase() != filter).map(e => e.includes(' ') ? '"' + e + '"' : e).join(' ')
        }
        search()
    })
})


search()
