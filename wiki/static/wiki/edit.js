const textarea = document.getElementById('id_raw_content');
/* Show uploaded image immediately */
/* Image list can insert image at current selection */
class Attachment {
    static attachments = new Map();
    static createQuickAccess(attachment) {
        const template = document.getElementById('quick-access-file');
        const node = template.content.cloneNode(true);
        const li = node.querySelector('li');
        li.dataset.name = attachment.name;
        li.classList.add('transparent', 'button');
        node.querySelector('img').src = attachment.imageUrl;
        node.querySelector('span:last-of-type').textContent = attachment.name;
        return li;
    }
    static new(element) {
        const name = element.querySelector('input[name$="-name"]').value;
        const quickAccess = document.querySelector(`#attachment-list li[data-name="${name}"]`);
        const attachment = new Attachment(element, quickAccess ?? undefined);
        Attachment.attachments.set(name, attachment);
        return attachment;
    }
    element;
    quickAccess;
    constructor(element, quickAccess) {
        this.element = element;
        this.quickAccess = quickAccess ?? null;
        if (this.quickAccess && !this.quickAccess.classList.contains('button')) {
            this.quickAccess.classList.add('transparent', 'button');
            this.quickAccess.addEventListener('click', _ => {
                textarea.focus();
                document.execCommand('insertText', false, `![](${this.name})`);
            });
        }
        this.element.querySelectorAll('input').forEach(e => e.addEventListener('change', ev => {
            this.updateElement();
        }));
    }
    updateQuickAccess() {
        if (this.quickAccess) {
            this.quickAccess.querySelector('img').src = this.imageUrl;
            this.quickAccess.dataset.name = this.name;
            this.quickAccess.querySelector('span:last-of-type').textContent = this.name;
        }
        else {
            this.quickAccess = Attachment.createQuickAccess(this);
            document.querySelector('#attachment-list ul').appendChild(this.quickAccess);
            this.quickAccess.addEventListener('click', _ => {
                textarea.focus();
                document.execCommand('insertText', false, `![](${this.name})`);
            });
        }
    }
    updateElement() {
        this.element.querySelector('img').src = this.imageUrl;
        if (!this.name) {
            let fileName = this.element.querySelector('input[type="file"]')?.files?.item(0)?.name ?? '';
            if (Attachment.attachments.has(fileName) && Attachment.attachments.get(fileName) !== this) {
                // Need to attach copy number to file name
                const extensionSeparator = fileName.lastIndexOf('.');
                const name = fileName.slice(0, extensionSeparator);
                const extension = fileName.slice(extensionSeparator);
                let copySuffix = 2;
                do {
                    fileName = `${name}-${copySuffix}${extension}`;
                    copySuffix += 1;
                } while (Attachment.attachments.has(fileName));
            }
            this.name = fileName;
            Attachment.attachments.set(this.name, this);
        }
        this.updateQuickAccess();
    }
    get name() {
        return this.element.querySelector('input[name$="-name"]').value;
    }
    set name(value) {
        this.element.querySelector('input[name$="-name"]').value = value;
        this.updateQuickAccess();
    }
    get imageUrl() {
        const [file] = this.element.querySelector('input[name$="-content"]').files ?? [];
        if (file) {
            return URL.createObjectURL(file);
        }
        else {
            return this.element.querySelector('img').src;
        }
    }
    set file(value) {
        const fileTransfer = new DataTransfer();
        fileTransfer.items.add(value);
        this.element.querySelector('input[name$="-content"]').files = fileTransfer.files;
        this.element.querySelector('input[name$="-content"]').dispatchEvent(new Event("change"));
    }
}
document.querySelectorAll('#attachments li:has(input[type="file"])').forEach(Attachment.new);
/* Add extra attachments */
const formCount = document.getElementById('id_attachment_set-TOTAL_FORMS');
const attachmentFormHtml = (() => {
    const fragment = document.getElementById('file-upload-template').content;
    const dummy = document.createElement('div');
    dummy.append(fragment);
    return dummy.innerHTML;
})();
const attachmentFormList = document.querySelector('#attachments > ul');
function incForms() {
    formCount.value = (parseInt(formCount.value) + 1).toString();
}
function decForms() {
    formCount.value = (parseInt(formCount.value) - 1).toString();
}
function addAttachment(file) {
    const lastForm = attachmentFormList.querySelector(':scope > li:last-of-type');
    const form_id = formCount.value;
    const html = attachmentFormHtml.replaceAll('__prefix__', form_id);
    lastForm.insertAdjacentHTML('afterend', html);
    const attachment = Attachment.new(lastForm.nextElementSibling);
    if (file) {
        attachment.file = file;
    }
    incForms();
    return attachment.name;
}
document.getElementById('attachment-add')?.addEventListener('click', _ => addAttachment());
/* Remove extra initial attachments */
/* These are no longer required as we can dynamically attach new ones */
document.querySelectorAll('li:has([id^="id_attachment_set-"][id$="-id"]:not([value]))').forEach(e => {
    e.remove();
    decForms();
});
/* Add Drag'n'Drop */
let dragCounter = 0;
const DRAG_CLASS = "drag";
function startDrag() {
    dragCounter += 1;
    if (!document.body.classList.contains(DRAG_CLASS)) {
        console.log('Starting drag');
        document.body.classList.add(DRAG_CLASS);
    }
}
function endDrag() {
    dragCounter -= 1;
    if (dragCounter == 0) {
        console.log('Ending drag');
        document.body.classList.remove(DRAG_CLASS);
    }
}
function forceEndDrag() {
    dragCounter = 0;
    console.log('Force ending drag');
    document.body.classList.remove(DRAG_CLASS);
}
document.addEventListener('dragenter', startDrag);
document.addEventListener('dragleave', endDrag);
document.addEventListener('dragend', endDrag);
function getFilename(disposition) {
    /*
    Input: inline; filename="<filename>"; filename*=<charset>'<language>'<filename*>
    Return <filename*> if exists, otherwise <filename> if exists otherwise ''
    */
    const parts = disposition.split(';').map(e => e.trim());
    let result = undefined;
    for (const part of parts) {
        const [_key, value] = part.split('=', 2);
        const key = _key.trim().toLowerCase();
        if (key === 'format' && !result) {
            result = value.replace(/^"(.*)"$/, "$1");
        }
        else if (key === 'format*') {
            const [_charset, _lang, name] = value.split("'", 3);
            result = decodeURIComponent(name);
        }
    }
    return result ?? '';
}
async function urlToFile(url) {
    const response = await fetch(url, {
        headers: {
            'Access-Control-Allow-Origin': '*',
        }
    });
    const body = await response.blob();
    const filename = getFilename(response.headers.get('Content-Disposition') ?? '');
    const file = new File([body], filename, {
        type: body.type
    });
    return file;
}
document.querySelectorAll('.drop-zone').forEach(e => {
    // Allow dropping (maybe show info about attachment e.g. "Cannot drop non-images")
    e.addEventListener('dragover', ev => ev.preventDefault());
    const textareaDrop = e.parentElement?.querySelector('textarea') !== null;
    e.addEventListener('drop', ev => {
        ev.preventDefault();
        forceEndDrag();
        console.log(ev);
        if (ev.dataTransfer?.files.length) {
            if (textareaDrop) {
                textarea.focus();
                const name = addAttachment(ev.dataTransfer.files[0]);
                document.execCommand('insertText', false, `![](${name})`);
            }
            else {
                // Take files whenever possible
                for (const file of ev.dataTransfer.files) {
                    addAttachment(file);
                }
            }
        }
        else {
            console.log(`Received non-file drop`, ev);
        }
    });
});
/* Paste pictures */
textarea.addEventListener('paste', ev => {
    if (ev.clipboardData.files.length) {
        const file = ev.clipboardData.files[0];
        const name = addAttachment(file);
        textarea.focus();
        document.execCommand('insertText', false, `![](${name})`);
        ev.preventDefault();
    }
});
/* Live preview */
const previewContainer = document.getElementById('preview');
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
const previewContainerStyle = window.getComputedStyle(previewContainer);
async function _updatePreview() {
    if (previewContainerStyle.display == 'none') {
        return;
    }
    const content = textarea.value;
    const response = await fetch('/wiki/:/edit/preview', {
        method: 'POST',
        body: content,
        headers: {
            'Content-Type': 'text/markdown',
        }
    });
    if (!response.ok) {
        return;
    }
    const dummy = document.createElement('div');
    dummy.innerHTML = await response.text();
    _updatePreviewImages(dummy);
    previewContainer.replaceChildren(...dummy.childNodes);
}
const updatePreview = debounce(_updatePreview, 1000);
_updatePreview(); // initial preview
function _updatePreviewImages(root) {
    root.querySelectorAll('img').forEach(e => {
        // Find out if its a relative image
        const imgSrc = URL.parse(e.src);
        if (imgSrc && imgSrc.origin == location.origin && imgSrc.pathname.startsWith(location.pathname)) {
            // relative url
            const fileName = imgSrc.pathname.substring(location.pathname.length);
            if (Attachment.attachments.has(fileName)) {
                e.src = Attachment.attachments.get(fileName).imageUrl;
            }
        }
    });
}
textarea.addEventListener('input', updatePreview);
document.querySelectorAll('input[data-preview]').forEach(e => e.addEventListener('change', _ => {
    _updatePreview();
}));
/* === Quality of life typing === */
/* Auto-Close brackets */
const enable_autoclose_brackets = document.querySelector('input[data-typing="brackets"]');
const enable_auto_indent = document.querySelector('input[data-typing="indent"]');
textarea.addEventListener('input', (ev) => {
    if (enable_autoclose_brackets.checked) {
        const BRACKETS = {
            '(': ')',
            '[': ']',
            '{': '}',
            '"': '"',
            "'": "'",
            '`': '`',
        };
        if (ev.data && ev.data in BRACKETS) {
            const cursorPos = textarea.selectionStart;
            document.execCommand('insertText', false, BRACKETS[ev.data]);
            textarea.selectionStart = cursorPos;
            textarea.selectionEnd = cursorPos;
        }
    }
    if (enable_auto_indent.checked) {
        if (ev.inputType == 'insertLineBreak') {
            const endOfLine = textarea.selectionStart - 2;
            const startOfLine = textarea.value.lastIndexOf('\n', endOfLine) + 1;
            const lastLine = textarea.value.substring(startOfLine, endOfLine + 1);
            console.log(`Last line is: (${startOfLine}, ${endOfLine}) "${lastLine}"`);
            const re = /^(?:[ \t]+|[ \t]*-[ \t]|[ \t]*\d+\.[ \t]|(?:[ \t]*>[ \t])+)/;
            const prefix = lastLine.match(re)?.[0];
            if (prefix) {
                document.execCommand('insertText', false, prefix);
            }
        }
    }
});
