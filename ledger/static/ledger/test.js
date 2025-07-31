function list_item(text) {
    const li = document.createElement("li");
    li.textContent = text;
    document.getElementById('event-list').append(li);
}
document.addEventListener('visibilitychange', ev => {
    const li = document.createElement('li');
    li.append(`page visibility changed to ${document.visibilityState}`);
    document.getElementById('event-list').append(li);
});
