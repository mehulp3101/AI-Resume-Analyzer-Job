// Load resume text into the analyzer. Matching runs in the Python models.
const resume = document.getElementById("resume");
const message = document.getElementById("file-status");
const fileInput = document.getElementById("file");
const analyzeButton = resume.form.querySelector('button[type="submit"]');
let selection = 0;

function showMessage(text, isError = false) {
    message.textContent = text;
    message.style.color = isError ? "#b42318" : "#08776e";
}

function resetFile() {
    selection++;
    fileInput.value = "";
    analyzeButton.disabled = false;
}

document.getElementById("example").onclick = () => {
    resetFile();
    resume.value = "IT student experienced in HTML, CSS, JavaScript, PHP, MySQL, React, GitHub and customer service.";
    showMessage("Example loaded. Select Analyze resume.");
};

document.getElementById("clear").onclick = () => {
    resetFile();
    resume.value = "";
    showMessage("Text cleared. Submit new text to update results, or clear skills on Jobs.");
};

fileInput.onchange = async () => {
    const current = ++selection;
    const file = fileInput.files[0];
    analyzeButton.disabled = false;
    showMessage("");
    if (!file) return;

    function rejectFile(text) {
        fileInput.value = "";
        showMessage(text, true);
    }

    const name = file.name.toLowerCase();
    const isPdf = name.endsWith(".pdf");
    if ((!isPdf && !name.endsWith(".txt")) ||
        file.type.startsWith("image/") || file.type.includes("zip")) {
        return rejectFile("Invalid file type. Upload a PDF or TXT resume. ZIP files and photos are not supported.");
    }
    if (file.size === 0) return rejectFile("The file is empty.");
    if (file.size > 1000000) return rejectFile("The file is too large. Maximum size is 1 MB.");

    analyzeButton.disabled = true;
    showMessage("Reading resume…");
    try {
        let text;
        if (isPdf) {
            const response = await fetch("/analyzer/pdf", {
                method: "POST",
                headers: {
                    "Content-Type": "application/pdf",
                    "X-CSRF-Token": resume.form.elements.csrf.value
                },
                body: file
            });
            const result = await response.json();
            if (current !== selection) return;
            if (!response.ok) return rejectFile(result.error || "Could not read this PDF.");
            text = result.text;
        } else {
            text = new TextDecoder("utf-8", { fatal: true }).decode(await file.arrayBuffer());
            if (/[\x00-\x08\x0b\x0c\x0e-\x1f]/.test(text)) {
                throw new Error("Not plain text");
            }
        }
        if (current !== selection) return;
        if (!text.trim()) return rejectFile("The file contains no resume text.");
        if (text.length > 200000) return rejectFile("The resume exceeds 200,000 characters.");
        resume.value = text;
        showMessage("Resume loaded. Click Analyze resume.");
    } catch {
        if (current === selection) rejectFile("Could not read this file. Choose a PDF or UTF-8 TXT resume, or paste the text.");
    } finally {
        if (current === selection) analyzeButton.disabled = false;
    }
};

resume.form.addEventListener("submit", (event) => {
    if (analyzeButton.disabled) {
        event.preventDefault();
        return;
    }
    if (!resume.value.trim()) {
        event.preventDefault();
        showMessage("Paste your resume text or choose a PDF or TXT file.", true);
    }
});
