import $ from 'jquery';

document.addEventListener('DOMContentLoaded', () => {
    const toggleButton = document.getElementById('rooms-toggle-all-users');
    console.assert(toggleButton !== null, "no element of id `rooms-toggle-all-users`")
    toggleButton!
        .addEventListener('click', ev => {
            console.assert(ev.currentTarget !== undefined, "Undefined event target in current scope!");
            (ev.currentTarget! as HTMLElement).classList?.toggle('active');
            $('#rooms').bootstrapTable('refresh');
        });
    $('#rooms').bootstrapTable('refresh');
});
