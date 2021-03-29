// Show appropriate pill based on #anchor in URL
import {Tab} from 'bootstrap';

function navigateToAnchorTab() {
    const hash = window.location.hash;

    if (hash) {
        const element: Element | null = document.querySelector(`ul.nav a[href="${hash}"]`);
        if (element === null) return;
        new Tab(element).show();
    }
}

function updateLocationHash(this: HTMLAnchorElement, ev: MouseEvent){
    if (this.hash === null) {
        console.warn('Selected tab does not have an id. Cannot update')
        return null;
    }

    // XXX in the jQuery variant, was some scrolling mechanism. not sure what it did.
    // const scrollmem = $('body').scrollTop() || $('html').scrollTop();
    window.location.hash = this.hash;
    // $('html,body').scrollTop(scrollmem);
}

document.addEventListener('DOMContentLoaded', () => {
    navigateToAnchorTab();

    for (const el of document.querySelectorAll<HTMLAnchorElement>('.nav-tabs a')) {
        el.addEventListener('click', updateLocationHash, false)
    }
});
