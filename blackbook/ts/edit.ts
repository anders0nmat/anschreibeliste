
const formCount = document.getElementById('id_steps-TOTAL_FORMS') as HTMLInputElement
const stepFormHtml = (() => {
    const fragment = (document.getElementById('step-template') as HTMLTemplateElement).content
    const dummy = document.createElement('div')
    dummy.append(fragment)
    return dummy.innerHTML
})()

function incForms() {
    formCount.value = (parseInt(formCount.value) + 1).toString()
}

function decForms() {
    formCount.value = (parseInt(formCount.value) - 1).toString()
}

/* Remove extra initial attachments */
/* These are no longer required as we can dynamically attach new ones */

document.querySelectorAll<HTMLElement>('li:has([id^="id_steps-"][id$="-id"]:not([value]))').forEach(e => {
    e.remove()
    decForms()
})

const add_button = document.querySelector<HTMLButtonElement>('#add-step')!

function addStep() {
    const html = stepFormHtml.replaceAll('__prefix__', formCount.value)
    add_button.insertAdjacentHTML("beforebegin", html)
    incForms()
}

add_button.addEventListener('click', addStep)
