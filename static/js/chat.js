document.addEventListener("DOMContentLoaded", () => {
  const videoElement = document.getElementById("videoElement");
  const canvasElement = document.getElementById("canvasElement");
  const cameraPreview = document.getElementById("cameraPreview");
  const cameraPlaceholder = document.getElementById("cameraPlaceholder");
  const toggleCameraBtn = document.getElementById("toggleCamera");
  const captureBtn = document.getElementById("captureBtn");
  const stopCameraBtn = document.getElementById("stopCameraBtn");
  const cameraControls = document.getElementById("cameraControls");
  const cameraImageInput = document.getElementById("cameraImageInput");
  const imageInput = document.getElementById("imageInput");
  const hiddenImageInput = document.getElementById("hiddenImageInput");
  const uploadDropzone = document.getElementById("uploadDropzone");
  const imagePreview = document.getElementById("imagePreview");
  const previewImg = document.getElementById("previewImg");
  const removePreviewBtn = document.getElementById("removePreview");
  const chatForm = document.getElementById("chatForm");
  const messageInput = document.getElementById("messageInput");
  const cameraBtn = document.getElementById("cameraBtn");
  let stream = null;
  let capturedImage = null;
  
  // Reset camera state on page load
  if (videoElement) {
    videoElement.srcObject = null;
  }
  if (cameraImageInput) {
    cameraImageInput.value = "";
  }
  if (uploadDropzone && uploadDropzone.style.display === "none") {
    uploadDropzone.style.display = "block";
  }

  // Camera functionality
  toggleCameraBtn?.addEventListener("click", async () => {
    if (stream) {
      stopCamera();
    } else {
      await startCamera();
    }
  });

  stopCameraBtn?.addEventListener("click", () => {
    stopCamera();
  });

  captureBtn?.addEventListener("click", () => {
    captureImage();
  });

  async function startCamera() {
    try {
      stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "user" } });
      videoElement.srcObject = stream;
      videoElement.style.display = "block";
      cameraPlaceholder.style.display = "none";
      cameraControls.style.display = "block";
      toggleCameraBtn.textContent = "Disable";
      
      // Wait for video to be ready
      videoElement.addEventListener("loadedmetadata", () => {
        if (captureBtn) {
          captureBtn.disabled = false;
          captureBtn.textContent = "Capture";
        }
      }, { once: true });
    } catch (err) {
      alert("Could not access camera. Please check permissions.");
      console.error("Camera error:", err);
    }
  }

  function stopCamera() {
    if (stream) {
      stream.getTracks().forEach((track) => track.stop());
      stream = null;
    }
    if (videoElement) {
      videoElement.style.display = "none";
      videoElement.srcObject = null;
    }
    if (cameraPlaceholder) {
      cameraPlaceholder.style.display = "block";
    }
    if (cameraControls) {
      cameraControls.style.display = "none";
    }
    if (toggleCameraBtn) {
      toggleCameraBtn.textContent = "Enable";
    }
    if (captureBtn) {
      captureBtn.disabled = true;
      captureBtn.textContent = "Capture";
    }
    if (canvasElement) {
      canvasElement.style.display = "none";
    }
    if (cameraImageInput) {
      cameraImageInput.value = "";
    }
    capturedImage = null;
  }

  function captureImage() {
    if (!videoElement || !stream) {
      alert("Camera not active. Please enable the camera first.");
      return;
    }
    
    if (videoElement.readyState !== videoElement.HAVE_ENOUGH_DATA && videoElement.videoWidth === 0) {
      alert("Camera not ready. Please wait a moment and try again.");
      return;
    }
    
    try {
      // Set canvas dimensions to match video
      const width = videoElement.videoWidth || 640;
      const height = videoElement.videoHeight || 480;
      canvasElement.width = width;
      canvasElement.height = height;
      
      const ctx = canvasElement.getContext("2d");
      ctx.drawImage(videoElement, 0, 0, width, height);
      const imageData = canvasElement.toDataURL("image/jpeg", 0.8);
      
      if (!imageData || imageData.length < 100) {
        alert("Failed to capture image. Please try again.");
        return;
      }
      
      capturedImage = imageData;
      cameraImageInput.value = imageData;
      
      // Show preview of captured image
      if (previewImg) {
        previewImg.src = imageData;
        if (imagePreview) {
          imagePreview.style.display = "block";
        }
      }
      
      // Show captured image in camera preview area
      showCapturedPreview(imageData);
      
      // Hide upload dropzone temporarily
      if (uploadDropzone) {
        uploadDropzone.style.display = "none";
      }
      
      // Clear any file upload
      if (hiddenImageInput) {
        hiddenImageInput.value = "";
      }
      if (imageInput) {
        imageInput.value = "";
      }
      if (messageInput) {
        messageInput.value = "";
        messageInput.required = false;
      }
      
      // Disable capture button during processing
      if (captureBtn) {
        captureBtn.disabled = true;
        captureBtn.textContent = "Processing...";
      }
      
      // Auto-submit the form to process the captured image
      setTimeout(() => {
        if (chatForm) {
          chatForm.submit();
        }
      }, 300);
    } catch (err) {
      console.error("Capture error:", err);
      alert("Failed to capture image: " + err.message);
      if (captureBtn) {
        captureBtn.disabled = false;
        captureBtn.textContent = "Capture";
      }
    }
  }

  // Image upload functionality
  imageInput?.addEventListener("change", (e) => {
    const file = e.target.files[0];
    if (file) {
      handleImageFile(file);
    }
  });

  uploadDropzone?.addEventListener("click", (event) => {
    if (event.target !== imageInput) imageInput?.click();
  });

  uploadDropzone?.addEventListener("dragover", (e) => {
    e.preventDefault();
    uploadDropzone.style.borderColor = "var(--accent)";
  });

  uploadDropzone?.addEventListener("dragleave", () => {
    uploadDropzone.style.borderColor = "var(--border)";
  });

  uploadDropzone?.addEventListener("drop", (e) => {
    e.preventDefault();
    uploadDropzone.style.borderColor = "var(--border)";
    const file = e.dataTransfer.files[0];
    if (file && file.type.startsWith("image/")) {
      handleImageFile(file);
    }
  });

  function handleImageFile(file) {
    const reader = new FileReader();
    reader.onload = (e) => {
      previewImg.src = e.target.result;
      imagePreview.style.display = "block";
      const dataTransfer = new DataTransfer();
      dataTransfer.items.add(file);
      hiddenImageInput.files = dataTransfer.files;
      messageInput.required = false;
    };
    reader.readAsDataURL(file);
  }

  removePreviewBtn?.addEventListener("click", () => {
    imagePreview.style.display = "none";
    previewImg.src = "";
    hiddenImageInput.value = "";
    imageInput.value = "";
    messageInput.required = true;
  });

  cameraBtn?.addEventListener("click", async () => {
    if (!stream) {
      await startCamera();
    } else {
      captureImage();
    }
  });
  
  // Show captured image preview in camera preview area
  function showCapturedPreview(imageData) {
    if (!cameraPreview) return;
    
    const previewImg = document.createElement("img");
    previewImg.src = imageData;
    previewImg.style.width = "100%";
    previewImg.style.borderRadius = "12px";
    previewImg.style.maxHeight = "180px";
    previewImg.style.objectFit = "cover";
    previewImg.id = "capturedPreviewImg";
    
    // Hide video and placeholder
    if (videoElement) {
      videoElement.style.display = "none";
    }
    if (cameraPlaceholder) {
      cameraPlaceholder.style.display = "none";
    }
    
    // Clear and add preview
    cameraPreview.innerHTML = "";
    cameraPreview.appendChild(previewImg);
    
    // Add a label
    const label = document.createElement("p");
    label.textContent = "📷 Image captured! Processing...";
    label.style.marginTop = "0.5rem";
    label.style.fontSize = "0.85rem";
    label.style.color = "var(--accent)";
    label.style.textAlign = "center";
    cameraPreview.appendChild(label);
  }

  // Auto-scroll chat thread
  const chatThread = document.getElementById("chatThread");
  if (chatThread) {
    chatThread.scrollTop = chatThread.scrollHeight;
  }

  // Form submission
  chatForm?.addEventListener("submit", (e) => {
    // Allow submission if there's a message, uploaded image, or camera snapshot
    const hasMessage = messageInput.value.trim();
    const hasUploadedImage = hiddenImageInput.files.length > 0;
    const hasCameraImage = cameraImageInput.value && cameraImageInput.value.length > 0;
    
    if (!hasMessage && !hasUploadedImage && !hasCameraImage) {
      e.preventDefault();
      alert("Please share a message, image, or camera snapshot.");
      return;
    }
    
    // If camera image is present, make sure message is not required
    if (hasCameraImage) {
      messageInput.required = false;
    }
  });
  
  // Make sure video is ready before allowing capture
  videoElement?.addEventListener("loadedmetadata", () => {
    if (captureBtn) {
      captureBtn.disabled = false;
    }
  });
  
  // Initialize capture button state
  if (captureBtn) {
    captureBtn.disabled = true;
  }
});


