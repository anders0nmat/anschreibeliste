
const textarea = document.getElementById('id_raw_content') as HTMLTextAreaElement

/* Show uploaded image immediately */
/* Image list can insert image at current selection */

class Attachment {
    static attachments = new Map<string, Attachment>()

    static createQuickAccess(attachment: Attachment): HTMLElement {
        const template = document.getElementById('quick-access-file') as HTMLTemplateElement
        const node = template.content.cloneNode(true) as DocumentFragment
        const li = node.querySelector<HTMLElement>('li')!
        li.dataset.name = attachment.name
        li.classList.add('transparent', 'button')
        node.querySelector<HTMLImageElement>('img')!.src = attachment.imageUrl
        node.querySelector<HTMLElement>('span:last-of-type')!.textContent = attachment.name

        return li
    }

    static new(element: HTMLElement): Attachment {
        const name = element.querySelector<HTMLInputElement>('input[name$="-name"]')!.value

        const quickAccess = document.querySelector<HTMLElement>(`#attachment-list li[data-name="${name}"]`)
        const attachment = new Attachment(element, quickAccess ?? undefined)
        Attachment.attachments.set(name, attachment)
        return attachment
    }

    element: HTMLElement
    quickAccess: HTMLElement | null

    constructor(element: HTMLElement, quickAccess?: HTMLElement) {
        this.element = element
        this.quickAccess = quickAccess ?? null

        if (this.quickAccess && !this.quickAccess.classList.contains('button')) {
            this.quickAccess.classList.add('transparent', 'button')
            this.quickAccess.addEventListener('click', _ => {
                textarea.focus()
                document.execCommand('insertText', false, `![](${this.name})`)
            })
        }

        this.element.querySelectorAll<HTMLInputElement>('input').forEach(e => e.addEventListener('change', ev => {
            this.updateElement()
        }))
    }

    private updateQuickAccess() {
        if (this.quickAccess) {
            this.quickAccess.querySelector<HTMLImageElement>('img')!.src = this.imageUrl
            this.quickAccess.dataset.name = this.name
            this.quickAccess.querySelector<HTMLElement>('span:last-of-type')!.textContent = this.name
        }
        else {
            this.quickAccess = Attachment.createQuickAccess(this)
            document.querySelector<HTMLElement>('#attachment-list ul')!.appendChild(this.quickAccess)
            this.quickAccess.addEventListener('click', _ => {
                textarea.focus()
                document.execCommand('insertText', false, `![](${this.name})`)
            })
        }
    }

    private updateElement() {
        this.element.querySelector<HTMLImageElement>('img')!.src = this.imageUrl

        if (!this.name) {
            let fileName = this.element.querySelector<HTMLInputElement>('input[type="file"]')?.files?.item(0)?.name ?? ''
            
            if (Attachment.attachments.has(fileName) && Attachment.attachments.get(fileName) !== this) {
                // Need to attach copy number to file name
                const extensionSeparator = fileName.lastIndexOf('.')
                const name = fileName.slice(0, extensionSeparator)
                const extension = fileName.slice(extensionSeparator)

                let copySuffix = 2
                do {
                    fileName = `${name}-${copySuffix}${extension}`
                    copySuffix += 1
                } while (Attachment.attachments.has(fileName))       
            }
            
            this.name = fileName
            Attachment.attachments.set(this.name, this)
        }

        this.updateQuickAccess()
    }

    get name(): string {
        return this.element.querySelector<HTMLInputElement>('input[name$="-name"]')!.value
    }

    set name(value: string) {
        this.element.querySelector<HTMLInputElement>('input[name$="-name"]')!.value = value

        this.updateQuickAccess()
    }

    get imageUrl(): string {
        const [file] = this.element.querySelector<HTMLInputElement>('input[name$="-content"]')!.files ?? []

        if (file) {
            return URL.createObjectURL(file)
        }
        else {
            return this.element.querySelector<HTMLImageElement>('img')!.src
        }
    }

    set file(value: File) {
        const fileTransfer = new DataTransfer()
        fileTransfer.items.add(value)

        this.element.querySelector<HTMLInputElement>('input[name$="-content"]')!.files = fileTransfer.files
        this.element.querySelector<HTMLInputElement>('input[name$="-content"]')!.dispatchEvent(new Event("change"))
    }
}

document.querySelectorAll<HTMLElement>('#attachments li:has(input[type="file"])').forEach(Attachment.new)

/* Add extra attachments */

const formCount = document.getElementById('id_attachment_set-TOTAL_FORMS') as HTMLInputElement
const attachmentFormHtml = (() => {
    const fragment = (document.getElementById('file-upload-template') as HTMLTemplateElement).content
    const dummy = document.createElement('div')
    dummy.append(fragment)
    return dummy.innerHTML
})()
const attachmentFormList = document.querySelector<HTMLElement>('#attachments > ul')!

function incForms() {
    formCount.value = (parseInt(formCount.value) + 1).toString()
}

function decForms() {
    formCount.value = (parseInt(formCount.value) - 1).toString()
}

function addAttachment(file?: File): string {
    const lastForm = attachmentFormList.querySelector<HTMLElement>(':scope > li:last-of-type')!
    const form_id = formCount.value
    const html = attachmentFormHtml.replaceAll('__prefix__', form_id)
    lastForm.insertAdjacentHTML('afterend', html)
    
    const attachment = Attachment.new(lastForm.nextElementSibling as HTMLElement)
    if (file) {
        attachment.file = file
    }

    incForms()
    return attachment.name
}

document.getElementById('attachment-add')?.addEventListener('click', _ => addAttachment())

/* Remove extra initial attachments */
/* These are no longer required as we can dynamically attach new ones */

document.querySelectorAll<HTMLElement>('li:has([id^="id_attachment_set-"][id$="-id"]:not([value]))').forEach(e => {
    e.remove()
    decForms()
})

/* Add Drag'n'Drop */

let dragCounter = 0
const DRAG_CLASS = "drag"

function startDrag() {
    dragCounter += 1
    if (!document.body.classList.contains(DRAG_CLASS)) {
        console.log('Starting drag')
        document.body.classList.add(DRAG_CLASS)
    }
}

function endDrag() {
    dragCounter -= 1
    if (dragCounter == 0) {
        console.log('Ending drag')
        document.body.classList.remove(DRAG_CLASS)
    }
}

function forceEndDrag() {
    dragCounter = 0
    console.log('Force ending drag')
    document.body.classList.remove(DRAG_CLASS)
}

document.addEventListener('dragenter', startDrag)
document.addEventListener('dragleave', endDrag)
document.addEventListener('dragend', endDrag)

function getFilename(disposition: string): string {
    /*
    Input: inline; filename="<filename>"; filename*=<charset>'<language>'<filename*>
    Return <filename*> if exists, otherwise <filename> if exists otherwise ''
    */
    const parts = disposition.split(';').map(e => e.trim())
    let result: string | undefined = undefined
    for (const part of parts) {
        const [_key, value] = part.split('=', 2)
        const key = _key.trim().toLowerCase()
        if (key === 'format' && !result) {
            result = value.replace(/^"(.*)"$/, "$1")
        }
        else if (key === 'format*') {
            const [_charset, _lang, name] = value.split("'", 3)
            result = decodeURIComponent(name)
        }
    }
    return result ?? ''
}

async function urlToFile(url: URL | string): Promise<File> {
    const response = await fetch(url, {
        headers: {
            'Access-Control-Allow-Origin': '*',
        }
    })
    const body = await response.blob()

    const filename = getFilename(response.headers.get('Content-Disposition') ?? '')

    const file = new File([body], filename, {
        type: body.type
    })

    return file
}

document.querySelectorAll<HTMLElement>('.drop-zone').forEach(e => {
    // Allow dropping (maybe show info about attachment e.g. "Cannot drop non-images")
    e.addEventListener('dragover', ev => ev.preventDefault())

    const textareaDrop = e.parentElement?.querySelector('textarea') !== null

    e.addEventListener('drop', ev => {
        ev.preventDefault()

        forceEndDrag()

        console.log(ev)

        if (ev.dataTransfer?.files.length) {
            if (textareaDrop) {
                textarea.focus()
                const name = addAttachment(ev.dataTransfer.files[0])
                document.execCommand('insertText', false, `![](${name})`)
            }
            else {
                // Take files whenever possible
                for (const file of ev.dataTransfer.files) {
                    addAttachment(file)
                }
            }
        }
        else {
            console.log(`Received non-file drop`, ev)
        }
    })
})

/* Paste pictures */

textarea.addEventListener('paste', ev => {
    if (ev.clipboardData!.files.length) {
        const file = ev.clipboardData!.files[0]
        const name = addAttachment(file)
        textarea.focus()
        document.execCommand('insertText', false, `![](${name})`)
        ev.preventDefault()
    }
})

/* Live preview */

const previewContainer = document.getElementById('preview')!

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
const previewContainerStyle = window.getComputedStyle(previewContainer)
async function _updatePreview() {
    if (previewContainerStyle.display == 'none') { return }
    const content = textarea.value
    const response = await fetch('/wiki/:/edit/preview', {
        method: 'POST',
        body: content,
        headers: {
            'Content-Type': 'text/markdown',
        }
    })

    if (!response.ok) { return }
    
    const dummy = document.createElement('div')
    dummy.innerHTML = await response.text()
    _updatePreviewImages(dummy)
    previewContainer.replaceChildren(...dummy.childNodes)
}

const updatePreview = debounce(_updatePreview, 1000)
_updatePreview() // initial preview

function _updatePreviewImages(root: HTMLElement) {
    root.querySelectorAll<HTMLImageElement>('img').forEach(e => {
        // Find out if its a relative image
        
        const imgSrc = URL.parse(e.src)
        if (imgSrc && imgSrc.origin == location.origin && imgSrc.pathname.startsWith(location.pathname)) {
            // relative url
            const fileName = imgSrc.pathname.substring(location.pathname.length)
            if (Attachment.attachments.has(fileName)) {
                e.src = Attachment.attachments.get(fileName)!.imageUrl
            }
        }
    })
}

textarea.addEventListener('input', updatePreview)
document.querySelectorAll<HTMLInputElement>('input[data-preview]').forEach(e => e.addEventListener('change', _ => {
    _updatePreview()
}))

/* === Quality of life typing === */

/* Auto-Close brackets */
const enable_autoclose_brackets = document.querySelector<HTMLInputElement>('input[data-typing="brackets"]')!
const enable_auto_indent = document.querySelector<HTMLInputElement>('input[data-typing="indent"]')!

textarea.addEventListener('input', (ev: InputEvent) => {
    if (enable_autoclose_brackets.checked) {
        const BRACKETS = {
            '(': ')',
            '[': ']',
            '{': '}',
            '"': '"',
            "'": "'",
            '`': '`',
        }
        if (ev.data && ev.data in BRACKETS) {
            const cursorPos = textarea.selectionStart
            document.execCommand('insertText', false, BRACKETS[ev.data])
            textarea.selectionStart = cursorPos
            textarea.selectionEnd = cursorPos
        }
    }
    
    if (enable_auto_indent.checked) {
        if (ev.inputType == 'insertLineBreak') {
            const endOfLine = textarea.selectionStart - 2
            const startOfLine = textarea.value.lastIndexOf('\n', endOfLine) + 1
            const lastLine = textarea.value.substring(startOfLine, endOfLine + 1)
            console.log(`Last line is: (${startOfLine}, ${endOfLine}) "${lastLine}"`)
            
            const re = /^(?:[ \t]+|[ \t]*-[ \t]|[ \t]*\d+\.[ \t]|(?:[ \t]*>[ \t])+)/
            const prefix = lastLine.match(re)?.[0]
            if (prefix) {
                document.execCommand('insertText', false, prefix)
            }
        }
    }
})
