const micBtn = document.getElementById('mic-btn');
const status = document.getElementById('status');
const transcript = document.getElementById('transcript');
const response = document.getElementById('response');

const API_URL = window.location.origin;
const recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
recognition.continuous = false;
recognition.interimResults = false;
recognition.lang = 'en-US';

let isListening = false;

micBtn.addEventListener('click', () => {
    if (isListening) {
        recognition.stop();
        return;
    }
    recognition.start();
    isListening = true;
    micBtn.classList.add('listening');
    status.textContent = 'Listening...';
    transcript.textContent = '';
    response.textContent = '';
});

recognition.onresult = async (event) => {
    const text = event.results[0][0].transcript;
    transcript.textContent = `You said: ${text}`;
    status.textContent = 'Processing...';

    try {
        const res = await fetch(`${API_URL}/api/intent`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text }),
        });
        const data = await res.json();
        response.textContent = data.reply;
        speak(data.reply);
    } catch (err) {
        response.textContent = 'Error: Could not reach the server.';
        status.textContent = 'Error';
    }
};

recognition.onend = () => {
    isListening = false;
    micBtn.classList.remove('listening');
    status.textContent = 'Click the microphone to start';
};

recognition.onerror = (event) => {
    isListening = false;
    micBtn.classList.remove('listening');
    status.textContent = `Error: ${event.error}`;
};

function speak(text) {
    if (!window.speechSynthesis) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1;
    utterance.pitch = 1;
    window.speechSynthesis.speak(utterance);
}
