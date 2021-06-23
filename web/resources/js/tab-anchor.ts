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

    window.location.hash = this.hash;
}

document.addEventListener('DOMContentLoaded', () => {
    navigateToAnchorTab();

    for (const el of document.querySelectorAll<HTMLAnchorElement>('.nav-tabs a')) {
        // `new Tab(element)` already implicitly happens due to the respective
        // `data-` attributes being present
        el.addEventListener('click', updateLocationHash, false)
    }
});
