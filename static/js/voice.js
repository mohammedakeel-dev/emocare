document.addEventListener("DOMContentLoaded", () => {
  const voiceInputBtn = document.getElementById("voiceInputBtn");
  const messageInput = document.getElementById("messageInput");
  const voiceOutputBtn = document.getElementById("voiceOutputBtn");
  let recognition = null;
  let synthesis = window.speechSynthesis;

  // Initialize speech recognition
  if ("webkitSpeechRecognition" in window || "SpeechRecognition" in window) {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = "en-US";

    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      if (messageInput) {
        messageInput.value = transcript;
        messageInput.focus();
      }
    };

    recognition.onerror = (event) => {
      console.error("Speech recognition error:", event.error);
      alert("Speech recognition error. Please try again.");
    };
  }

  // Voice input - removed mic button, but keep functionality for potential future use
  // voiceInputBtn?.addEventListener("click", () => {
  //   if (!recognition) {
  //     alert("Speech recognition not supported in your browser.");
  //     return;
  //   }
  //   
  //   if (recognition.isListening) {
  //     recognition.stop();
  //     voiceInputBtn.textContent = "🎤";
  //     voiceInputBtn.classList.remove("recording");
  //   } else {
  //     recognition.start();
  //     voiceInputBtn.textContent = "🔴";
  //     voiceInputBtn.classList.add("recording");
  //   }
  // });

  // Voice output
  voiceOutputBtn?.addEventListener("click", () => {
    const lastMessage = document.querySelector(".chat-message.assistant:last-child p");
    if (lastMessage && synthesis) {
      const text = lastMessage.textContent;
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 0.9;
      utterance.pitch = 1.1;
      synthesis.speak(utterance);
    }
  });
});

