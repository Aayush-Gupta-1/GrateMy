window.addEventListener("load", () => {
    const splash = document.getElementById("splash-screen");
    const mainContent = document.getElementById("main-content");

    // show splash for 5 seconds, then fade in main content
    setTimeout(() => {
        if (splash) {
            splash.style.display = "none";
        }
        if (mainContent) {
            mainContent.style.opacity = "1";
        }
    }, 4000); // 4000 milliseconds = 4 seconds
});
