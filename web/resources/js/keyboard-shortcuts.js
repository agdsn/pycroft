import hotkeys from 'hotkeys-js';

hotkeys('option+c', function (event) {
    window.location = "/user/create";
});
hotkeys('shift+option+c', function (event) {
    window.open("/user/create");
});
hotkeys('option+f', function (event) {
    window.location = "/user/search";
});
hotkeys('shift+option+f', function (event) {
    window.open("/user/search");
});
hotkeys('option+h', function (event) {
    window.open("https://www.youtube.com/embed/Ita6WyQ3SFQ?autoplay=1&controls=0");
});

