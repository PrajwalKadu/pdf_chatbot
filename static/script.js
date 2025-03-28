function uploadPDF() {
    let fileInput = document.getElementById('pdfFile');
    let uploadStatus = document.getElementById('uploadStatus');
    let uploadBtn = document.getElementById("uploadBtn");

    if (!fileInput.files.length) {
        uploadStatus.innerText = "No file selected.";
        return;
    }

    let formData = new FormData();
    formData.append('file', fileInput.files[0]);

    uploadStatus.innerText = "Uploading...";
    uploadBtn.disabled = true;

    fetch('/upload', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        uploadStatus.innerText = data.message || data.error;
        uploadBtn.disabled = false;
    })
    .catch(error => {
        console.error('Error:', error);
        uploadStatus.innerText = "Upload failed.";
        uploadBtn.disabled = false;
    });
}

function askQuestion() {
    let userInput = document.getElementById('userInput');
    let chatBox = document.getElementById('chatBox');
    let askButton = document.getElementById('askBtn');

    let question = userInput.value.trim();
    if (!question) return;

    let userMsg = document.createElement('div');
    userMsg.classList.add('chat-message', 'user-message');
    userMsg.innerHTML = `<b>You:</b> ${question}`;
    chatBox.appendChild(userMsg);

    let botMsg = document.createElement('div');
    botMsg.classList.add('chat-message', 'bot-message');
    botMsg.innerHTML = `<b>Bot:</b> `;
    chatBox.appendChild(botMsg);

    userInput.value = "";
    askButton.disabled = true;

    setTimeout(() => {
        chatBox.scrollTop = chatBox.scrollHeight;
    }, 100);

    fetch('/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question })
    })
    .then(response => response.body.getReader())
    .then(reader => {
        let decoder = new TextDecoder();
        let accumulatedText = "";

        function processText({ done, value }) {
            if (done) {
                askButton.disabled = false;
                return;
            }
            let newText = decoder.decode(value, { stream: true });
            accumulatedText += newText;
            botMsg.innerHTML = `<b>Bot:</b> ${accumulatedText}`;

            setTimeout(() => {
                chatBox.scrollTop = chatBox.scrollHeight;
            }, 100);

            return reader.read().then(processText);
        }
        return reader.read().then(processText);
    })
    .catch(error => {
        console.error('Error:', error);
        botMsg.innerHTML = `<b>Bot:</b> Error processing request.`;
        askButton.disabled = false;
    });
}

function handleKeyPress(event) {
    if (event.key === "Enter") {
        askQuestion();
    }
}
