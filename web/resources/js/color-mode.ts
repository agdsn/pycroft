/*!
 * Color mode toggler for Bootstrap's docs (https://getbootstrap.com/)
 * Copyright 2011-2023 The Bootstrap Authors
 * Licensed under the Creative Commons Attribution 3.0 Unported License.
 */

console.error("test!");
const getStoredTheme = () => localStorage.getItem('theme')
const setStoredTheme = (theme: string) => localStorage.setItem('theme', theme)

const getPreferredTheme = () => {
    const storedTheme = getStoredTheme()
    if (storedTheme) {
        return storedTheme
    }

    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

const setTheme = (theme: string) => {
    if (theme === 'auto' && window.matchMedia('(prefers-color-scheme: dark)').matches) {
        document.documentElement.setAttribute('data-bs-theme', 'dark')
    } else {
        document.documentElement.setAttribute('data-bs-theme', theme)
    }
}

setTheme(getPreferredTheme())

const showActiveTheme = (theme: string, focus = false) => {
    console.debug("showing active theme: " + theme)
    const themeSwitcher: HTMLElement | null = document.querySelector('#bd-theme');
    if (!themeSwitcher) return;

    const activeThemeIcon = document.querySelector('.theme-icon-active');
    if (!activeThemeIcon) throw new Error('.theme-icon-active not found');

    const btnToActivate: HTMLElement | null = document.querySelector(`[data-bs-theme-value="${theme}"]`);
    if (!btnToActivate) throw new Error(`[data-bs-theme-value="${theme}"] not found`);

    const iconInActiveBtn = btnToActivate.querySelector('span.theme-icon');
    if (!iconInActiveBtn) throw new Error(`icon in active button not found`);

    document.querySelectorAll('[data-bs-theme-value]').forEach(element => {
        element.classList.remove('active')
        element.setAttribute('aria-pressed', 'false')
    })

    btnToActivate.classList.add('active')
    btnToActivate.setAttribute('aria-pressed', 'true')
    activeThemeIcon.innerHTML = iconInActiveBtn.innerHTML;

    if (focus) themeSwitcher.focus();
}

window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
    const storedTheme = getStoredTheme()
    if (storedTheme !== 'light' && storedTheme !== 'dark') {
        setTheme(getPreferredTheme())
    }
})

window.addEventListener('DOMContentLoaded', () => {
    showActiveTheme(getPreferredTheme())

    document.querySelectorAll('[data-bs-theme-value]')
        .forEach(toggle => {
            toggle.addEventListener('click', () => {
                const theme = toggle.getAttribute('data-bs-theme-value')!;
                setStoredTheme(theme)
                setTheme(theme)
                showActiveTheme(theme, true)
            })
        })
})
