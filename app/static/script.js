const selectBtn = document.getElementById("selectRoiBtn");
const canvas = document.getElementById("roiCanvas");
const ctx = canvas.getContext("2d");

// Disable submit to ROI until url is input, then generate tabs until ROI is selected
selectBtn.disabled = true;
document.getElementById("generateTabsBtn").disabled = true;


document.getElementById("urlForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  window.selectedROI = null;
  const youtube_url = document.getElementById("url").value;
  const response = await fetch("/tabs/fetch_video_info", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ youtube_url })
  });

  const data = await response.json();
  const videoContainer = document.getElementById("videoContainer");
  // Clear old video if any
  videoContainer.innerHTML = "";

  // Create iframe
  const iframe = document.createElement("iframe");
  iframe.id = "videoEmbed";
  iframe.width = "560";
  iframe.height = "315";
  iframe.src = `https://www.youtube.com/embed/${data.video_id}?enablejsapi=1`;
  iframe.frameBorder = "0";
  iframe.allow ="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture";
  iframe.allowFullscreen = true;

  // Append iframe, then canvas
  videoContainer.appendChild(iframe);
  videoContainer.appendChild(canvas);

    selectBtn.disabled = false;
  });

let startX, startY, endX, endY;
let drawing = false;
document.getElementById("selectRoiBtn").addEventListener("click", () => {
  const iframe = document.querySelector("#videoContainer iframe");
  if (!iframe) {
    alert("Please load a YouTube video first!");
    return;
  }

  const rect = iframe.getBoundingClientRect();
  const containerRect = document.getElementById("videoContainer").getBoundingClientRect();
  canvas.style.top = rect.top - containerRect.top + "px";
  canvas.style.left = rect.left - containerRect.left + "px";

  // Match canvas to iframe size
  canvas.width = rect.width;
  canvas.height = rect.height;

  // Show canvas
  canvas.style.display = "block";

  // Reset overlay
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = "rgba(0, 0, 0, 0.2)";
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  // Disable video interaction
  iframe.style.pointerEvents = "none";

});

  // Mouse events
  canvas.addEventListener("mousedown", (e) => {
    drawing = true;
    startX = e.offsetX;
    startY = e.offsetY;
  });

  canvas.addEventListener("mousemove", (e) => {
    if (!drawing) return;
    endX = e.offsetX;
    endY = e.offsetY;

    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = "rgba(0, 0, 0, 0.2)";
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    ctx.strokeStyle = "red";
    ctx.lineWidth = 2;
    ctx.strokeRect(startX, startY, endX - startX, endY - startY);
  });

  canvas.addEventListener("mouseup", () => {
    document.getElementById("generateTabsBtn").disabled = false;
    drawing = false;
    const iframe = document.getElementById("videoEmbed");
    const roi = {
      x: Math.min(startX, endX),
      y: Math.min(startY, endY),
      width: Math.abs(endX - startX),
      height: Math.abs(endY - startY)
    };

    console.log("ROI selected:", roi);
    window.selectedROI = roi;

    // Hide overlay and re-enable video
    canvas.style.display = "none";
    iframe.style.pointerEvents = "auto";
  });

  // Show loading spinner
const spinner = document.getElementById("loadingSpinner");
const roiForm = document.getElementById("roiForm");
roiForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  console.log("Submitting ROI form");
  // Disable submit button to prevent multiple submissions
  const submitButton = e.target.querySelector("button[type='submit']");
  submitButton.disabled = true;
  const iframe = document.getElementById("videoEmbed");
  const data = {
    youtube_url: document.getElementById("url").value,
    start_buffer: parseInt(document.getElementById("start_buffer").value),
    end_buffer: parseInt(document.getElementById("end_buffer").value),
    roi: window.selectedROI,
    iframe_width: iframe.clientWidth,
    iframe_height: iframe.clientHeight
  };
    spinner.classList.remove("hidden"); // SHOW SPINNER
  try {
    const response = await fetch("/tabs/process_video", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data)
    });
    spinner.classList.add("hidden"); // HIDE SPINNER
    const resultDiv = document.getElementById("result");

    if (response.ok) {
      const result = await response.json();
      resultDiv.innerHTML = `
        <p>${result.message}</p>
        <a href="/static/${result.output}" target="_blank">Download PDF</a>
      `;
    } else {
      resultDiv.innerHTML = `<p>Error: ${response.status}</p>`;
    }
  } catch (err) {
    document.getElementById("result").innerHTML = `<p>Request failed: ${err}</p>`;
  } finally {
    // Re-enable submit button
    submitButton.disabled = false;
  }
});
