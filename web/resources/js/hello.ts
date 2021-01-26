import $ from "jquery";

document.addEventListener('DOMContentLoaded', () => {console.log("This is running TypeScript!")})

$(function () {
    $('[data-toggle="tooltip"]').tooltip()
});

interface User {
    foo: string,
    bar: symbol,
}

export function foo(u: User): string | null {
    return document.getElementsByTagName('div').length % 2
        ? "fooo"
        : null;
}
