/*
 * Copyright (c) 2024. The Pycroft Authors. See the AUTHORS file.
 * This file is part of the Pycroft project and licensed under the terms of
 * the Apache License, Version 2.0. See the LICENSE file for details
 */

function handleKeyPress(event: KeyboardEvent) {
    // Dismiss event in case it was triggered in a text area or the shift key was (already) pressed
    if (event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement || event.shiftKey) return;

    if !(event.key === "ArrowRight" || event.key === "ArrowLeft") return;

    const navLinks = [...document.querySelectorAll<HTMLElement>(".user-nav-link")].filter(x => !x.classList.contains("disabled"));
    const currentIndex = navLinks.findIndex(link => link.classList.contains("active"));

    const indexChange = (() => {
        switch (event.key) {
            case "ArrowRight":
                return +1;
            case "ArrowLeft":
                return -1;
        }
    })();

    navLinks[(navLinks.length + currentIndex + indexChange) % navLinks.length].click();
}

document.addEventListener('keydown', handleKeyPress);
