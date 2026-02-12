// Cheese maze with pixel collision:
// - White pixels = safe path
// - Black pixels = walls
// - Start zone: top-left quarter
// - Goal zone: bottom-right quarter

window.addEventListener("DOMContentLoaded", () => {
    const wrapper = document.getElementById("maze-wrapper");
    const canvas = document.getElementById("maze-canvas");
    const player = document.getElementById("maze-player");
    const statusEl = document.getElementById("maze-status");
    const captchaInput = document.getElementById("captcha_ok");

    if (!wrapper || !canvas || !player || !statusEl || !captchaInput) {
        console.warn("Maze elements missing");
        return;
    }

    const ctx = canvas.getContext("2d");
    const img = new Image();

    // we know this path works (you tested it)
    img.src = "/static/images/maze.png";

    let imageReady = false;
    let started = false;
    let completed = false;

    img.onload = () => {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
        imageReady = true;
        statusEl.textContent =
            "Move your mouse into START to begin.";
        console.log("Maze image drawn");
    };

    img.onerror = () => {
        statusEl.textContent = "Maze image failed to load 🤕";
        console.error("Failed to load maze image from", img.src);
    };

    function resetRun(message) {
        if (completed) return;
        started = false;
        captchaInput.value = "0";
        statusEl.textContent = message;
    }

    function insideElement(el, x, y) {
        const rect = canvas.getBoundingClientRect();
        const elRect = el.getBoundingClientRect();

        const scaleX = canvas.width / rect.width;
        const scaleY = canvas.height / rect.height;

        const elX = (elRect.left - rect.left) * scaleX;
        const elY = (elRect.top - rect.top) * scaleY;
        const elW = elRect.width * scaleX;
        const elH = elRect.height * scaleY;

        return (x >= elX && x <= elX + elW &&
                y >= elY && y <= elY + elH);
    }

    function insideStartZone(x, y) {
        return insideElement(document.getElementById("maze-start-label"), x, y);
    }

    function insideGoalZone(x, y) {
        return insideElement(document.getElementById("maze-cheese-label"), x, y);
    }


    function isBlackPixel(r, g, b) {
        // white-ish (very bright)
        return (r + g + b) < 100;
    }

    wrapper.addEventListener("mousemove", (e) => {
        if (!imageReady) return;

        const rect = canvas.getBoundingClientRect();
        const scaleX = canvas.width / rect.width;
        const scaleY = canvas.height / rect.height;

        const x = (e.clientX - rect.left) * scaleX;
        const y = (e.clientY - rect.top) * scaleY;

        // Move 🐭 to follow cursor (percentage of canvas)
        const percentX = (x / canvas.width) * 100;
        const percentY = (y / canvas.height) * 100;
        player.style.left = `${percentX}%`;
        player.style.top = `${percentY}%`;

        // If not started, only look for entering START
        if (!started) {
            if (insideStartZone(x, y)) {
                started = true;
                statusEl.textContent =
                    "Nice! Stay on the white path and reach the cheese 🧀.";
            }
            return;
        }

        if (completed) return;

        // Out of bounds -> fail
        if (x < 0 || y < 0 || x >= canvas.width || y >= canvas.height) {
            resetRun("You left the maze. Start again from START.");
            return;
        }

        // Look at the pixel under the cursor
        const pixel = ctx.getImageData(
            Math.floor(x),
            Math.floor(y),
            1,
            1
        ).data;
        const r = pixel[0];
        const g = pixel[1];
        const b = pixel[2];

        const onPath = isBlackPixel(r, g, b);

        if (!onPath) {
            resetRun("You hit a wall 😵 Try again from START.");
            return;
        }

        // Check for goal
        if (insideGoalZone(x, y)) {
            completed = true;
            captchaInput.value = "1";
            statusEl.textContent =
                "Maze completed ✅ You're not a bot.";
        }
    });

    // Leaving the maze box mid-run = fail
    wrapper.addEventListener("mouseleave", () => {
        if (!completed && started) {
            resetRun("You left the maze. Start again from START.");
        }
    });
});
