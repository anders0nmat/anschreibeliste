/*
let c = 0
document.getElementById('send-event')!.addEventListener('click', _ => {
    fetch(`/test/send_event/?message=server_message_${c}`)
    c += 1
})

// document.getElementById('event-status')!.addEventListener('click', _ => {
// 	const li = document.createElement('li')
// 	li.append(`status. EventSource.readyState=${STATES[events?.readyState ?? 3]}`)
// 	document.getElementById('event-list')!.append(li)
// })

// document.getElementById('event-close')!.addEventListener('click', _ => {
// 	events?.close()
// })


const STATES = ['CONNECTING', 'OPEN', 'CLOSED', 'null']

let events = new EventSource('/test/events/')
events = new EventSource('/test/events/')
events = new EventSource('/test/events/')

events.onopen = ev => {
    const li = document.createElement('li')
    li.append(`open event.`)
    document.getElementById('event-list')!.append(li)
}

events.onmessage = ev => {
    const li = document.createElement('li')
    li.append(`message event. ${ev.data}`)
    document.getElementById('event-list')!.append(li)
}

events.onerror = (ev: Event) => {
    const li = document.createElement('li')
    li.append(`error event. EventSource.readyState=${STATES[(ev.target as EventSource).readyState ?? 3]}`)
    document.getElementById('event-list')!.append(li)
    }*/
function list_item(text) {
    const li = document.createElement("li");
    li.textContent = text;
    document.getElementById('event-list').append(li);
}
let server = undefined;
let server_reconnect = undefined;
function connect_ws() {
    server = new WebSocket("/ws/test");
    server.onopen = ev => {
        clearTimeout(server_reconnect);
        server_reconnect = undefined;
        list_item("WS Server connected");
    };
    server.onclose = ev => {
        list_item("WS Server closed");
    };
    server.onerror = ev => {
        list_item("WS Server errored, attempting reconnect");
        clearTimeout(server_reconnect);
        server_reconnect = setTimeout(() => {
            server = connect_ws();
        }, 2000);
    };
    server.onmessage = ev => list_item("WS Server recieved message: " + ev.data);
    return server;
}
server = connect_ws();
let c = 0;
document.getElementById('send-event').addEventListener('click', _ => {
    server?.send(JSON.stringify({ message: `Counter is ${c}` }));
    c += 1;
});
/*
let events1 = new EventSource('/test/events/')
let events2 = new EventSource('/test/events/')
let events3 = new EventSource('/test/events/')

function _onopen(tag) {
    return ev => {
        const li = document.createElement('li')
        li.append(`open event. tag=${tag}`)
        document.getElementById('event-list')!.append(li)
    }
}

function _onmessage(tag) {
    return ev => {
        const li = document.createElement('li')
        li.append(`message event. tag=${tag} ${ev.data}`)
        document.getElementById('event-list')!.append(li)
    }
}

function _onerror(tag) {
    return (ev: Event) => {
        const li = document.createElement('li')
        li.append(`error event. tag=${tag} EventSource.readyState=${STATES[(ev.target as EventSource).readyState ?? 3]}`)
        document.getElementById('event-list')!.append(li)
    }
}

//events = new EventSource('/test/events/')
events1.onopen = _onopen(1)
events2.onopen = _onopen(2)
events3.onopen = _onopen(3)
events1.onmessage = _onmessage(1)
events2.onmessage = _onmessage(2)
events3.onmessage = _onmessage(3)
events1.onerror = _onerror(1)
events2.onerror = _onerror(2)
events3.onerror = _onerror(3)*/
// document.getElementById('event-open')!.addEventListener('click', _ => {
// 	events = new EventSource('/test/events/')
// })
document.addEventListener('visibilitychange', ev => {
    const li = document.createElement('li');
    li.append(`page visibility changed to ${document.visibilityState}`);
    document.getElementById('event-list').append(li);
});
