window.addEventListener("load", () => { // run after page load
    const splash = document.getElementById("splash-screen");  // splash screen element
    const mainContent = document.getElementById("main-content");  // page content element

    // show splash for 5 seconds, then fade in main content
    setTimeout(() => { // delay before transition
        if (splash) { // if splash exists
            splash.style.display = "none";  // hide splash
        } // end if splash
        if (mainContent) { // if main content exists
            mainContent.style.opacity = "1";  // fade in content
        } // end if mainContent
    }, 4000); // 4000 milliseconds = 4 seconds
}); // end load listener
