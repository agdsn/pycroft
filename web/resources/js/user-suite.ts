/*
 * Copyright (c) 2024. The Pycroft Authors. See the AUTHORS file.
 * This file is part of the Pycroft project and licensed under the terms of
 * the Apache License, Version 2.0. See the LICENSE file for details
 */

function waitForKeyPress(callback: (event: KeyboardEvent) => void): void {
  const handleKeyPress = (event: KeyboardEvent) => {
    // Call the callback function with the event when a key is pressed
    callback(event);
  };

  // Add the event listener to the document
  document.addEventListener('keydown', handleKeyPress);
}

waitForKeyPress((event) => {
    // checks rather the input was triggered in a text area then it is dismissed
    if(event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement) return;

    if (event.key === "ArrowRight" ){
        const navLinks = [...document.querySelectorAll<HTMLElement>(".user-nav-link")].filter(x => !x.classList.contains("disabled"));
        for (let i= 0; i < navLinks.length; i++){
            if(navLinks[i].classList.contains("active")) {
                let index = (i + 1) % navLinks.length;
                navLinks[index].click();
                break;
            }
        }
    }

    if (event.key === "ArrowLeft" ){
        const navLinks = [...document.querySelectorAll<HTMLElement>(".user-nav-link")].filter(x => !x.classList.contains("disabled"));
        for (let i= 0; i < navLinks.length; i++){
            if(navLinks[i].classList.contains("active")) {
                let index = i - 1;
                if (index < 0) index += (navLinks.length); // Ich hasse JS noch nicht mal mod kann das ordentlich
                navLinks[index].click();
                break;
            }
        }
    }
});
