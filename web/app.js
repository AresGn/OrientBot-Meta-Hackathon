const form = document.getElementById("demo-form");
const statusEl = document.getElementById("status");
const stepsEl = document.getElementById("steps");
const reportEl = document.getElementById("report");
const submitBtn = document.getElementById("submit-btn");

function setStatus(message, isError = false) {
  statusEl.textContent = message;
  statusEl.className = isError ? "error" : "muted";
}

function renderSteps(steps) {
  if (!steps || steps.length === 0) {
    stepsEl.innerHTML =
      '<p class="muted">Aucune étape renvoyée (boucle agent non branchée).</p>';
    return;
  }
  const items = steps
    .map(
      (s) =>
        `<li><strong>${s.tool || "étape"}</strong> — ${s.summary || ""}</li>`
    )
    .join("");
  stepsEl.innerHTML = `<ol>${items}</ol>`;
}

function renderReport(report) {
  if (!report) {
    reportEl.innerHTML =
      '<p class="muted">Le rapport apparaîtra ici.</p>';
    return;
  }
  reportEl.innerHTML = `<pre>${JSON.stringify(report, null, 2)}</pre>`;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  submitBtn.disabled = true;
  setStatus("Envoi au serveur…");
  stepsEl.innerHTML = '<p class="muted">En attente…</p>';
  reportEl.innerHTML = '<p class="muted">En attente…</p>';

  const photo = document.getElementById("photo").files[0];
  const voice = document.getElementById("voice").files[0];
  const body = new FormData();
  if (photo) body.append("photo", photo);
  if (voice) body.append("voice", voice);

  try {
    const response = await fetch("/run", { method: "POST", body });
    const data = await response.json().catch(() => ({}));

    if (response.status === 501) {
      setStatus(
        "API en place : la boucle agent n’est pas encore branchée (501)."
      );
      renderSteps(data.steps);
      renderReport(null);
      return;
    }

    if (!response.ok) {
      throw new Error(data.detail || data.status || response.statusText);
    }

    setStatus("Exécution terminée.");
    renderSteps(data.steps);
    renderReport(data.report);
  } catch (err) {
    setStatus(`Erreur : ${err.message}`, true);
  } finally {
    submitBtn.disabled = false;
  }
});
