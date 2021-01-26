import $ from "jquery";

document.addEventListener('DOMContentLoaded', () => {console.log("This is running TypeScript!")})

$(function () {
    $('[data-toggle="tooltip"]').tooltip()
});
