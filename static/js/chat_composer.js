// Handles Enter-to-send (Shift+Enter for newline) and basic composer interactions
document.addEventListener("DOMContentLoaded", function () {
  const textarea = document.getElementById("messageInput");
  const form = document.getElementById("chatForm");
  if (textarea && form) {
    textarea.addEventListener("keydown", function (e) {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        const message = textarea.value.trim();
        if (message) {
          // Submit the form first, then clear after submission starts
          form.submit();
          // Clear after a tiny delay to ensure form submission is processed
          setTimeout(() => {
            textarea.value = "";
          }, 50);
        }
      }
    });
    
    // Also clear on form submit
    form.addEventListener("submit", function() {
      // Small delay to ensure form submission happens
      setTimeout(() => {
        if (textarea) {
          textarea.value = "";
        }
      }, 100);
    });
  }

  // Make icon buttons accessible: focus and press triggers
  document.querySelectorAll(".icon-btn").forEach((btn) => {
    btn.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        btn.click();
      }
    });
  });

  // Emoji picker: removed - emoji button has been removed from UI
  // Emoji functionality can be added back in the future if needed
});
