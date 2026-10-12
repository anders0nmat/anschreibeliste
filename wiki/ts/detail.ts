/* Interactive tasklists */

const csrf_token = document.querySelector<HTMLInputElement>('input[name="csrfmiddlewaretoken"]')!.value
document.querySelectorAll<HTMLInputElement>('.task-list-item > input[type="checkbox"][data-line]').forEach(e => {
    e.addEventListener('change', _ => {
        const newState = e.checked
        const data = new FormData()
        data.append('line', e.dataset.line ?? '')
        data.append('value', newState ? 'true' : 'false')
        fetch('taskitem/', {
            method: 'POST',
            body: data,
            headers: {
                "X-CSRFToken": csrf_token,
            }
        })
    })
})

const checklist_toolbar = document.querySelector<HTMLTemplateElement>('#clear-checklist')!.content.firstElementChild!
document.querySelectorAll<HTMLElement>('.task-list').forEach(e => {
    const bar = checklist_toolbar.cloneNode(true) as HTMLElement
    bar.querySelector<HTMLButtonElement>('button')!.addEventListener('click', _ => {
        const linenos: string[] = []
        e.querySelectorAll<HTMLInputElement>('input[type="checkbox"]:not([disabled])').forEach(cb => {
            cb.checked = false
            linenos.push(cb.dataset.line ?? '')
        })

        const newState = false
        const data = new FormData()
        linenos.forEach(e => data.append('line', e))
        data.append('value', newState ? 'true' : 'false')
        fetch('taskitem/', {
            method: 'POST',
            body: data,
            headers: {
                "X-CSRFToken": csrf_token,
            }
        })
    })
    e.insertAdjacentElement("afterbegin", bar)
})
