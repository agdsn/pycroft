// Show appropriate pill based on #anchor in URL
import {Tab} from 'bootstrap';

function navigateToAnchorTab() {
    const hash = window.location.hash;
    if (!hash) return;

    const selector = `ul.nav [href="${hash}"], ul.nav [data-bs-target="${hash}"]`;
    const element = document.querySelector<HTMLElement>(selector);
    if (element === null) return;
    new Tab(element).show();
}

function updateLocationHash(this: HTMLElement, _: MouseEvent){
    if (this instanceof HTMLAnchorElement) {
        if (this.hash === null) {
         // console.warn('Selected tab does not have an id. Cannot update')
            return null;
        }

        window.location.hash = this.hash;
    } else {
        const bsTarget = this.dataset.bsTarget || null;
        if (bsTarget === null) return;
        window.location.href = bsTarget;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    navigateToAnchorTab();

    for (const el of document.querySelectorAll<HTMLElement>('.nav-tabs [role="tab"]')) {
        // `new Tab(element)` already implicitly happens due to the respective
        // `data-` attributes being present
        el.addEventListener('click', updateLocationHash, false)
    }
});
