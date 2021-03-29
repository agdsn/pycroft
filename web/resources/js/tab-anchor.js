// Show appropriate pill based on #anchor in URL
import {Tab} from 'bootstrap';

function navigateToAnchorTab() {
    const hash = window.location.hash;

    if (hash) {
        new Tab(document.querySelector(`ul.nav a[href="${hash}"]`)).show();
    }
}

document.addEventListener('DOMContentLoaded', () => {
    navigateToAnchorTab();

    for (const el of document.querySelectorAll('.nav-tabs a')) {
        el.addEventListener('click', (e) => {
                // XXX in the jQuery variant, was some scrolling mechanism. not sure what it did.
                // const scrollmem = $('body').scrollTop() || $('html').scrollTop();
                window.location.hash = e.currentTarget.hash;
                // $('html,body').scrollTop(scrollmem);
            }
        )
    }
});
