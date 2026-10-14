const topicInput = document.getElementById("topic");
const generatorForm = document.getElementById("generatorForm");

const generateBtn = document.getElementById("generateBtn");
const loading = document.getElementById("loading");

const resultSection = document.getElementById("resultSection");
const postOutput = document.getElementById("postOutput");

const attempts = document.getElementById("attempts");
const status = document.getElementById("status");
const metaStatus = document.getElementById("metaStatus");

const characterCount = document.getElementById("characterCount");

const errorBox = document.getElementById("error");
const errorText = document.getElementById("errorText");
const dismissError = document.getElementById("dismissError");

const copyBtn = document.getElementById("copyBtn");
const copyLabel = document.getElementById("copyLabel");

const MAX_TOPIC_LENGTH = 2000;


/* --------------------------------
   Topic input
--------------------------------- */

topicInput.addEventListener("input", () => {
    updateCharacterCount();
    hideError();
});


function updateCharacterCount() {
    const length = topicInput.value.length;

    characterCount.textContent =
        `${length.toLocaleString()} / ${MAX_TOPIC_LENGTH.toLocaleString()}`;

    characterCount.style.color =
        length >= MAX_TOPIC_LENGTH
            ? "var(--error)"
            : "";
}


/* --------------------------------
   Generate post
--------------------------------- */

generatorForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const topic = topicInput.value.trim();

    if (!topic) {
        showError("Please enter a topic before generating a post.");
        topicInput.focus();
        return;
    }

    if (topic.length > MAX_TOPIC_LENGTH) {
        showError(
            `Your topic is too long. Please keep it under ${MAX_TOPIC_LENGTH.toLocaleString()} characters.`
        );
        topicInput.focus();
        return;
    }

    hideError();
    setGeneratingState(true);

    try {
        const response = await fetch("/generate", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                topic: topic
            })
        });

        let data;

        try {
            data = await response.json();
        } catch {
            throw new Error(
                "The server returned an invalid response."
            );
        }

        if (!response.ok || !data.success) {
            throw new Error(
                data.error || "Something went wrong while generating the post."
            );
        }

        renderResult(data);

    } catch (error) {
        showError(
            error instanceof Error
                ? error.message
                : "Something went wrong. Please try again."
        );

    } finally {
        setGeneratingState(false);
    }
});


/* --------------------------------
   Result rendering
--------------------------------- */

function renderResult(data) {
    postOutput.textContent = data.draft || "";

    attempts.textContent =
        data.attempts ?? "—";

    const approved = Boolean(data.approved);
    const statusText = approved
        ? "Approved"
        : "Not approved";

    status.textContent = statusText;
    metaStatus.textContent = statusText;

    const statusDot = document.querySelector(
        ".result-status .status-dot"
    );

    if (statusDot) {
        statusDot.style.background =
            approved
                ? "var(--success)"
                : "var(--error)";

        statusDot.style.boxShadow =
            approved
                ? "0 0 0 3px rgba(111, 214, 161, 0.08)"
                : "0 0 0 3px rgba(240, 124, 124, 0.08)";
    }

    resultSection.classList.remove("hidden");

    requestAnimationFrame(() => {
        resultSection.scrollIntoView({
            behavior: "smooth",
            block: "start"
        });
    });
}


/* --------------------------------
   Loading state
--------------------------------- */

function setGeneratingState(isGenerating) {
    generateBtn.disabled = isGenerating;
    topicInput.disabled = isGenerating;

    loading.classList.toggle("hidden", !isGenerating);

    if (isGenerating) {
        resultSection.classList.add("hidden");
        generateBtn.querySelector(".button-label").textContent =
            "Generating...";
    } else {
        generateBtn.querySelector(".button-label").textContent =
            "Generate post";
    }
}


/* --------------------------------
   Copy generated post
--------------------------------- */

copyBtn.addEventListener("click", async () => {
    const post = postOutput.textContent.trim();

    if (!post) {
        return;
    }

    try {
        await navigator.clipboard.writeText(post);

        showCopySuccess();

    } catch {
        showError(
            "Could not copy automatically. Please select the post and copy it manually."
        );
    }
});


function showCopySuccess() {
    const originalLabel = copyLabel.textContent;

    copyLabel.textContent = "Copied";
    copyBtn.disabled = true;

    setTimeout(() => {
        copyLabel.textContent = originalLabel;
        copyBtn.disabled = false;
    }, 1500);
}


/* --------------------------------
   Keyboard shortcut
--------------------------------- */

topicInput.addEventListener("keydown", (event) => {
    const isShortcut =
        (event.metaKey || event.ctrlKey) &&
        event.key === "Enter";

    if (!isShortcut) {
        return;
    }

    event.preventDefault();

    if (!generateBtn.disabled) {
        generatorForm.requestSubmit();
    }
});


/* --------------------------------
   Error handling
--------------------------------- */

function showError(message) {
    errorText.textContent = message;
    errorBox.classList.remove("hidden");
}


function hideError() {
    errorBox.classList.add("hidden");
    errorText.textContent = "";
}


dismissError.addEventListener("click", hideError);


/* --------------------------------
   Initial state
--------------------------------- */

updateCharacterCount();

