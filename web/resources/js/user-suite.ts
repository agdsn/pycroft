/*
 * Copyright (c) 2024. The Pycroft Authors. See the AUTHORS file.
 * This file is part of the Pycroft project and licensed under the terms of
 * the Apache License, Version 2.0. See the LICENSE file for details
 */

function waitForKeyPress(callback: (event: KeyboardEvent) => void): void {
  const handleKeyPress = (event: KeyboardEvent) => {
    // Call the callback function with the event when a key is pressed
    callback(event);

    // Remove the event listener after the first key press (if you want it to happen only once)
    // document.removeEventListener('keydown', handleKeyPress);
  };

  // Add the event listener to the document
  document.addEventListener('keydown', handleKeyPress);
}

// Example of using the function
waitForKeyPress((event) => {
  console.log(`Key pressed: ${event.key}`);
  // Add your logic here based on the key press
    if (event.key === "ArrowRight" ){
        const navLinks = document.getElementsByClassName("user-nav-link");
        for (let i= 0; i < navLinks.length; i++){
            const link = navLinks[i] as HTMLLinkElement;
            if(link.classList.contains("active")) {
                let index = (i + 1)%navLinks.length;
                const link2 = navLinks[index] as HTMLLinkElement;
                link2.click();
                break;
            }
        }
    }
    if (event.key === "ArrowLeft" ){
        const navLinks = document.getElementsByClassName("user-nav-link");
        let next = false;
        console.log(navLinks.length)
        for (let i= 0; i < navLinks.length; i++){
            const link = navLinks[i] as HTMLLinkElement;
            if(link.classList.contains("active")) {
                let index = (i - 1) % navLinks.length;
                const link2 = navLinks[index] as HTMLLinkElement;
                link2.click();
                break;
            }
        }
    }
});
