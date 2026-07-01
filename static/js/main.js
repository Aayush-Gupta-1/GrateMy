window.addEventListener("load", () => {
    const splash = document.getElementById("splash-screen");  // splash screen element
    const mainContent = document.getElementById("main-content");  // page content element

    // show splash for 5 seconds, then fade in main content
    setTimeout(() => {
        if (splash) {
            splash.style.display = "none";  // hide splash
        }
        if (mainContent) {
            mainContent.style.opacity = "1";  // fade in content
        }
    }, 4000); // 4000 milliseconds = 4 seconds
});
