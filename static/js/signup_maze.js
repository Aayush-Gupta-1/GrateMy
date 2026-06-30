// Cheese maze with pixel collision:
// - White pixels = safe path
// - Black pixels = walls
// - Start zone: top-left quarter
// - Goal zone: bottom-right quarter

window.addEventListener("DOMContentLoaded", () => { // run after DOM ready
    const wrapper = document.getElementById("maze-wrapper"); // maze container
    const canvas = document.getElementById("maze-canvas"); // maze canvas
    const player = document.getElementById("maze-player"); // player icon
    const statusEl = document.getElementById("maze-status"); // status text
    const captchaInput = document.getElementById("captcha_ok"); // hidden captcha field

    if (!wrapper || !canvas || !player || !statusEl || !captchaInput) { // missing elements check
        console.warn("Maze elements missing"); // warn if missing
        return; // stop init
    } // end check

    const ctx = canvas.getContext("2d");  // drawing context
    const img = new Image();  // maze image

    // we know this path works (you tested it)
    img.src = "/static/images/maze.png"; // set image source

    let imageReady = false;  // maze image loaded yet
    let started = false;  // player entered start zone
    let completed = false;  // player reached goal

    img.onload = () => { // when maze image loads
        ctx.clearRect(0, 0, canvas.width, canvas.height); // clear canvas
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height); // draw maze image
        imageReady = true; // mark image ready
        statusEl.textContent = // set status text
            "Move your mouse into START to begin."; // instructions
        console.log("Maze image drawn"); // log success
    }; // end onload

    img.onerror = () => { // if image fails
        statusEl.textContent = "Maze image failed to load 🤕"; // error status
        console.error("Failed to load maze image from", img.src); // log error
    }; // end onerror

    function resetRun(message) { // resets run state
        if (completed) return;  // already done, ignore
        started = false;  // back to not started
        captchaInput.value = "0";  // not verified
        statusEl.textContent = message; // show message
    } // end resetRun

    function insideElement(el, x, y) { // checks point inside element
        const rect = canvas.getBoundingClientRect(); // canvas bounds
        const elRect = el.getBoundingClientRect(); // element bounds

        const scaleX = canvas.width / rect.width; // x scale factor
        const scaleY = canvas.height / rect.height; // y scale factor

        const elX = (elRect.left - rect.left) * scaleX; // element left in canvas coords
        const elY = (elRect.top - rect.top) * scaleY; // element top in canvas coords
        const elW = elRect.width * scaleX; // element width scaled
        const elH = elRect.height * scaleY; // element height scaled

        return (x >= elX && x <= elX + elW && // x within bounds
                y >= elY && y <= elY + elH); // y within bounds
    } // end insideElement

    function insideStartZone(x, y) { // checks if point in start zone
        return insideElement(document.getElementById("maze-start-label"), x, y); // delegate check
    } // end insideStartZone

    function insideGoalZone(x, y) { // checks if point in goal zone
        return insideElement(document.getElementById("maze-cheese-label"), x, y); // delegate check
    } // end insideGoalZone


    function isBlackPixel(r, g, b) { // checks pixel darkness
        return (r + g + b) < 100;  // dark pixel = path
    } // end isBlackPixel

    wrapper.addEventListener("mousemove", (e) => { // track mouse movement
        if (!imageReady) return; // wait for image

        const rect = canvas.getBoundingClientRect(); // canvas bounds
        const scaleX = canvas.width / rect.width; // x scale factor
        const scaleY = canvas.height / rect.height; // y scale factor

        const x = (e.clientX - rect.left) * scaleX; // mouse x in canvas coords
        const y = (e.clientY - rect.top) * scaleY; // mouse y in canvas coords

        // Move 🐭 to follow cursor (percentage of canvas)
        const percentX = (x / canvas.width) * 100; // x as percent
        const percentY = (y / canvas.height) * 100; // y as percent
        player.style.left = `${percentX}%`; // set player left
        player.style.top = `${percentY}%`; // set player top

        // If not started, only look for entering START
        if (!started) { // not started yet
            if (insideStartZone(x, y)) { // entered start zone
                started = true; // mark started
                statusEl.textContent = // update status
                    "Nice! Stay off the white walls and reach the cheese 🧀."; // instructions
            } // end if start zone
            return; // skip rest until started
        } // end if not started

        if (completed) return; // stop if already done

        // Out of bounds -> fail
        if (x < 0 || y < 0 || x >= canvas.width || y >= canvas.height) { // bounds check
            resetRun("You left the maze. Start again from START."); // fail message
            return; // stop processing
        } // end bounds check

        // Look at the pixel under the cursor
        const pixel = ctx.getImageData( // read pixel data
            Math.floor(x), // pixel x
            Math.floor(y), // pixel y
            1, // width
            1 // height
        ).data; // pixel rgba array
        const r = pixel[0]; // red value
        const g = pixel[1]; // green value
        const b = pixel[2]; // blue value

        const onPath = isBlackPixel(r, g, b); // check if on path

        if (!onPath) { // hit a wall
            resetRun("You hit a wall 😵 Try again from START."); // fail message
            return; // stop processing
        } // end wall check

        // Check for goal
        if (insideGoalZone(x, y)) { // reached goal zone
            completed = true; // mark completed
            captchaInput.value = "1"; // mark verified
            statusEl.textContent = // success status
                "Maze completed ✅ You're not a bot."; // success message
        } // end goal check
    }); // end mousemove listener

    // Leaving the maze box mid-run = fail
    wrapper.addEventListener("mouseleave", () => { // mouse left wrapper
        if (!completed && started) { // mid-run and not done
            resetRun("You left the maze. Start again from START."); // fail message
        } // end check
    }); // end mouseleave listener
}); // end DOMContentLoaded listener
