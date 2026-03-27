/* ══════════════════════════════════════════════════════════════════════════════
   VIZZY CHAT — Premium Frontend Logic
   ══════════════════════════════════════════════════════════════════════════════ */

// ── Application State ─────────────────────────────────────────────────────────
const state = {
  mode: "home",
  conversationId: null,
  messages: [],
  conversations: [],
  attachments: [],
  homeProfile: { style_selections: [], favourite_asset_ids: [], mood_keywords: [], colour_palette: [] },
  businessProfile: { business_name: "", business_type: "", brand_voice: "", primary_colours: [], tagline: "", values_keywords: [] },
  campaigns: [],
  isGenerating: false,
};

// ── Mode Content (sidebar data) ───────────────────────────────────────────────
const modeContent = {
  home: {
    summary: "Personal artmaking, storytelling, memory visualization, and iterative co-creation in one place.",
    memory: [
      { label: "Aesthetic pull",    value: "Dreamlike, intimate, painterly, emotionally symbolic" },
      { label: "Preferred outputs", value: "Artwork sets, story scenes, quote posters, reflective visuals" },
      { label: "Typical intent",    value: "Translate feelings, memories, and goals into tangible visual experiences" },
    ],
    context: [
      { label: "Creative pathway", value: "Painting, photo reimagination, dream visualization, symbolic art" },
      { label: "Narrative flow",   value: "Story sequences, storybooks, scene-by-scene visualization" },
      { label: "Reflection layer", value: "Quote posters, journaling from artwork, inner emotional landscapes" },
    ],
    capabilities: ["Multi-image generation", "Style transfer", "Story visuals", "Taste memory", "Reference uploads", "Img2Img"],
    surfaces: ["Frame display", "Print poster", "Save style", "Share set"],
    coverage: [
      "Real img2img transformation — uploads are genuine init images, not just prompt hints.",
      "Model-generated copy and story outlines replace templates — Claude writes the words.",
      "Style memory stores selections, favourites, mood keywords, and colour palette.",
      "Export panel produces downloadable PNG and ZIP files with social & email stubs.",
    ],
    prompts: [
      "Paint something that feels like how my last year felt.",
      "Turn this photo into a renaissance-style artwork.",
      "Generate a story for my kids, then visualize it scene by scene.",
      "Help me design a quote poster for my living room.",
    ],
    welcomeSuggestions: [
      { icon: "🎨", text: "Paint something that feels like how my last year felt." },
      { icon: "🖼️", text: "Turn this photo into a renaissance-style artwork." },
      { icon: "📖", text: "Generate a story for my kids, then visualize it scene by scene." },
      { icon: "✨", text: "Show me my inner emotional landscape right now." },
    ],
  },
  business: {
    summary: "Creative and marketing co-pilot for brand visuals, signage, campaigns, social-ready assets, and ambient experiences.",
    memory: [
      { label: "Brand awareness",  value: "Business type, tone, seasonality, offers, and reusable creative needs" },
      { label: "Preferred outputs", value: "Product visuals, posters, signage, campaigns, loops, branded artwork" },
      { label: "Typical intent",   value: "Drive attention and conversion without making the brand feel cheap" },
    ],
    context: [
      { label: "Business context", value: "Brand assets, values, past campaigns, and seasonal goals" },
      { label: "Asset targets",    value: "Frame, social, signage, email, memento artwork, and in-store visuals" },
      { label: "Marketing style",  value: "Premium-looking output that still feels accessible and conversion-focused" },
    ],
    capabilities: ["Campaign visuals", "In-store signage", "Product imagery", "Deploy surfaces", "Reference uploads", "Brand kit"],
    surfaces: ["Frame", "Email", "Social", "Print signage"],
    coverage: [
      "Brand kit stores name, type, voice, colours, tagline, and values.",
      "Brand context injected into every generation for automatic brand alignment.",
      "Claude writes real headlines, support copy, and CTAs.",
      "Campaign tracking lets you attach generated assets and copy to named campaigns.",
    ],
    prompts: [
      "Create premium-looking visuals for this product without making it feel expensive.",
      "Create a sale poster that does not feel cheap.",
      "Design in-store visuals for rainy days.",
      "Create an Apple-esque product video loop.",
    ],
    welcomeSuggestions: [
      { icon: "💎", text: "Create premium-looking visuals for this product." },
      { icon: "🏷️", text: "Create a sale poster that doesn't feel cheap." },
      { icon: "🌧️", text: "Design in-store visuals for rainy days." },
      { icon: "🍽️", text: "Show this dish as indulgent but refined." },
    ],
  },
};

// ── DOM References ────────────────────────────────────────────────────────────
const messageStream     = document.getElementById("messageStream");
const promptInput       = document.getElementById("promptInput");
const generateButton    = document.getElementById("generateButton");
const quickPrompts      = document.getElementById("quickPrompts");
const modeSummary       = document.getElementById("modeSummary");
const memoryList        = document.getElementById("memoryList");
const contextList       = document.getElementById("contextList");
const coverageList      = document.getElementById("coverageList");
const capabilityList    = document.getElementById("capabilityList");
const surfaceList       = document.getElementById("surfaceList");
const conversationList  = document.getElementById("conversationList");
const historyCount      = document.getElementById("historyCount");
const newChatButton     = document.getElementById("newChatButton");
const uploadButton      = document.getElementById("uploadButton");
const uploadChip        = document.getElementById("uploadChip");
const fileInput         = document.getElementById("fileInput");
const attachmentTray    = document.getElementById("attachmentTray");
const messageTemplate   = document.getElementById("messageTemplate");
const outputCardTemplate = document.getElementById("outputCardTemplate");
const lightbox          = document.getElementById("lightbox");
const lightboxImage     = document.getElementById("lightboxImage");
const lightboxDownload  = document.getElementById("lightboxDownload");
const lightboxClose     = document.getElementById("lightboxClose");
const toastContainer    = document.getElementById("toastContainer");

// ══════════════════════════════════════════════════════════════════════════════
// TOAST NOTIFICATION SYSTEM
// ══════════════════════════════════════════════════════════════════════════════

function showToast(message, type = "info", duration = 3500) {
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  const icons = { success: "✅", error: "❌", info: "💡" };
  toast.innerHTML = `<span class="toast-icon">${icons[type] || "💡"}</span><span>${message}</span>`;
  toastContainer.appendChild(toast);

  setTimeout(() => {
    toast.classList.add("leaving");
    setTimeout(() => toast.remove(), 300);
  }, duration);
}

// ══════════════════════════════════════════════════════════════════════════════
// LIGHTBOX
// ══════════════════════════════════════════════════════════════════════════════

let currentLightboxUrl = "";

function openLightbox(src, filename) {
  currentLightboxUrl = src;
  lightboxImage.src = src;
  lightboxImage.alt = filename || "Generated visual";
  lightbox.style.display = "grid";
  document.body.style.overflow = "hidden";
}

function closeLightbox() {
  lightbox.style.display = "none";
  document.body.style.overflow = "";
  currentLightboxUrl = "";
}

lightbox.addEventListener("click", (e) => {
  if (e.target === lightbox) closeLightbox();
});

lightboxClose.addEventListener("click", closeLightbox);

lightboxDownload.addEventListener("click", () => {
  if (currentLightboxUrl) {
    const a = document.createElement("a");
    a.href = currentLightboxUrl;
    a.download = currentLightboxUrl.split("/").pop() || "vizzy-output";
    a.click();
    showToast("Download started", "success");
  }
});

document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") {
    if (lightbox.style.display === "grid") closeLightbox();
    else closeModal();
  }
});

// ══════════════════════════════════════════════════════════════════════════════
// INITIALIZATION
// ══════════════════════════════════════════════════════════════════════════════

function initializeApp() {
  bindModeButtons();
  generateButton.addEventListener("click", handleGenerate);
  newChatButton.addEventListener("click", () => { resetChat(); showToast("New chat started", "info"); });
  uploadButton.addEventListener("click", () => fileInput.click());
  if (uploadChip) uploadChip.addEventListener("click", () => fileInput.click());
  fileInput.addEventListener("change", handleUpload);
  promptInput.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") handleGenerate();
  });
  loadMode("home");
  void refreshConversations();
  void loadHomeProfile();
  void loadBusinessProfile();
  void loadCampaigns();
  renderBrandKitPanel();
}

// ── Mode Switching ────────────────────────────────────────────────────────────

function bindModeButtons() {
  document.querySelectorAll(".mode-button").forEach((btn) => {
    btn.addEventListener("click", () => {
      setMode(btn.dataset.mode);
      document.querySelectorAll(".mode-button").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
    });
  });
}

function setMode(mode) {
  state.mode = mode;
  const content = modeContent[mode];
  modeSummary.textContent = content.summary;
  promptInput.value = "";
  renderMemory(content.memory);
  renderContext(content.context);
  renderCoverage(content.coverage);
  renderCapabilities(content.capabilities);
  renderSurfaces(content.surfaces);
  renderQuickPrompts(content.prompts);
  renderBrandKitPanel();
  renderDeepMemoryPanel();
  resetChat();
}

function loadMode(mode) { setMode(mode); }

function resetChat() {
  state.conversationId = null;
  state.messages       = [];
  state.attachments    = [];
  renderAttachmentTray();
  renderMessages();
  renderConversationList();
}

// ══════════════════════════════════════════════════════════════════════════════
// SIDEBAR RENDERS
// ══════════════════════════════════════════════════════════════════════════════

function renderMemory(items) {
  memoryList.innerHTML = "";
  items.forEach((item) => {
    const li = document.createElement("li");
    li.innerHTML = `<span class="memory-label">${item.label}</span>${item.value}`;
    memoryList.appendChild(li);
  });
}

function renderContext(items) {
  contextList.innerHTML = "";
  items.forEach((item) => {
    const li = document.createElement("li");
    li.innerHTML = `<span class="memory-label">${item.label}</span>${item.value}`;
    contextList.appendChild(li);
  });
}

function renderCoverage(items) {
  coverageList.innerHTML = "";
  items.forEach((item) => {
    const li = document.createElement("li");
    li.textContent = item;
    coverageList.appendChild(li);
  });
}

function renderCapabilities(items) {
  capabilityList.innerHTML = "";
  items.forEach((item) => {
    const chip = document.createElement("span");
    chip.className = "meta-chip";
    chip.textContent = item;
    capabilityList.appendChild(chip);
  });
}

function renderSurfaces(items) {
  surfaceList.innerHTML = "";
  items.forEach((item) => {
    const chip = document.createElement("span");
    chip.className = "meta-chip";
    chip.textContent = item;
    surfaceList.appendChild(chip);
  });
}

function renderQuickPrompts(prompts) {
  quickPrompts.innerHTML = "";
  prompts.forEach((prompt) => {
    const btn = document.createElement("button");
    btn.className   = "chip-button";
    btn.type        = "button";
    btn.textContent = prompt;
    btn.addEventListener("click", () => { promptInput.value = prompt; promptInput.focus(); });
    quickPrompts.appendChild(btn);
  });
}

// ══════════════════════════════════════════════════════════════════════════════
// DEEP MEMORY PANEL (Home taste profile)
// ══════════════════════════════════════════════════════════════════════════════

async function loadHomeProfile() {
  try {
    const res  = await fetch("/api/memory/home/profile");
    const data = await res.json();
    state.homeProfile = data;
    renderDeepMemoryPanel();
  } catch (_) {}
}

function renderDeepMemoryPanel() {
  const panel = document.getElementById("deepMemoryPanel");
  if (!panel) return;

  if (state.mode !== "home") {
    panel.style.display = "none";
    return;
  }
  panel.style.display = "";

  const p = state.homeProfile;
  const moods    = (p.mood_keywords    || []).slice(0, 8).join(", ") || "Not yet learned";
  const styles   = (p.style_selections || []).slice(0, 5).join(", ") || "Not yet selected";
  const palette  = (p.colour_palette   || []);
  const favCount = (p.favourite_asset_ids || []).length;

  const swatches = palette.length
    ? palette.map((c) => `<span class="colour-swatch" style="background:${c}" title="${c}"></span>`).join("")
    : '<span class="muted">Not yet captured</span>';

  panel.innerHTML = `
    <div class="panel-section-title">Your Taste Memory</div>
    <ul class="memory-list">
      <li><span class="memory-label">Mood words</span>${moods}</li>
      <li><span class="memory-label">Styles chosen</span>${styles}</li>
      <li><span class="memory-label">Favourites</span>${favCount} saved</li>
      <li><span class="memory-label">Colour palette</span><span class="swatch-row">${swatches}</span></li>
    </ul>
  `;
}

// ══════════════════════════════════════════════════════════════════════════════
// BRAND KIT PANEL (Business mode)
// ══════════════════════════════════════════════════════════════════════════════

async function loadBusinessProfile() {
  try {
    const res  = await fetch("/api/memory/business/profile");
    const data = await res.json();
    state.businessProfile = data;
    renderBrandKitPanel();
  } catch (_) {}
}

async function loadCampaigns() {
  try {
    const res  = await fetch("/api/campaigns");
    const data = await res.json();
    state.campaigns = data;
    renderBrandKitPanel();
  } catch (_) {}
}

function renderBrandKitPanel() {
  const panel = document.getElementById("brandKitPanel");
  if (!panel) return;

  if (state.mode !== "business") {
    panel.style.display = "none";
    return;
  }
  panel.style.display = "";

  const bp = state.businessProfile;
  const campaigns = state.campaigns;

  const colours = (bp.primary_colours || []).length
    ? bp.primary_colours.map((c) => `<span class="colour-swatch" style="background:${c}" title="${c}"></span>`).join("")
    : '<span class="muted">Not set</span>';

  const campaignList = campaigns.length
    ? campaigns.slice(0, 3).map((c) => `<li>${c.name} <span class="chip-mini status-${c.status}">${c.status}</span></li>`).join("")
    : '<li class="muted">No campaigns yet</li>';

  panel.innerHTML = `
    <div class="panel-section-title">Brand Kit</div>
    <ul class="memory-list">
      <li><span class="memory-label">Name</span>${bp.business_name || '<span class="muted">Not set</span>'}</li>
      <li><span class="memory-label">Type</span>${bp.business_type || '<span class="muted">Not set</span>'}</li>
      <li><span class="memory-label">Voice</span>${bp.brand_voice  || '<span class="muted">Not set</span>'}</li>
      <li><span class="memory-label">Tagline</span>${bp.tagline    || '<span class="muted">Not set</span>'}</li>
      <li><span class="memory-label">Values</span>${(bp.values_keywords||[]).join(", ") || '<span class="muted">Not set</span>'}</li>
      <li><span class="memory-label">Colours</span><span class="swatch-row">${colours}</span></li>
    </ul>
    <button type="button" class="mini-button" style="margin-top:10px" onclick="openBrandKitEditor()">✏️ Edit Brand Kit</button>
    <div class="panel-section-title" style="margin-top:14px">Campaigns</div>
    <ul class="memory-list">${campaignList}</ul>
    <button type="button" class="mini-button" style="margin-top:8px" onclick="openNewCampaignDialog()">+ New Campaign</button>
  `;
}

// ── Brand Kit Editor Modal ────────────────────────────────────────────────────

function openBrandKitEditor() {
  const bp = state.businessProfile;
  const modal = _createModal("Edit Brand Kit", `
    <label>Business name<input id="bk-name"   value="${bp.business_name  || ""}" placeholder="e.g. Café Mira" /></label>
    <label>Business type<input id="bk-type"   value="${bp.business_type  || ""}" placeholder="e.g. restaurant, retail" /></label>
    <label>Brand voice<input   id="bk-voice"  value="${bp.brand_voice    || ""}" placeholder="e.g. warm, premium, playful" /></label>
    <label>Tagline<input       id="bk-tagline" value="${bp.tagline        || ""}" placeholder="e.g. Where every cup counts" /></label>
    <label>Values (comma-separated)<input id="bk-values" value="${(bp.values_keywords||[]).join(", ")}" placeholder="e.g. local, sustainable, artisan" /></label>
    <label>Primary colours (comma-separated hex)<input id="bk-colours" value="${(bp.primary_colours||[]).join(", ")}" placeholder="e.g. #1a1a2e, #e94560" /></label>
    <div class="modal-actions">
      <button type="button" class="mini-button" onclick="closeModal()">Cancel</button>
      <button type="button" class="mini-button primary" onclick="saveBrandKit()">Save</button>
    </div>
  `);
  document.body.appendChild(modal);
}

async function saveBrandKit() {
  const payload = {
    business_name:    document.getElementById("bk-name").value.trim(),
    business_type:    document.getElementById("bk-type").value.trim(),
    brand_voice:      document.getElementById("bk-voice").value.trim(),
    tagline:          document.getElementById("bk-tagline").value.trim(),
    values_keywords:  document.getElementById("bk-values").value.split(",").map((s) => s.trim()).filter(Boolean),
    primary_colours:  document.getElementById("bk-colours").value.split(",").map((s) => s.trim()).filter(Boolean),
  };
  try {
    const res  = await fetch("/api/memory/business/profile", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    const data = await res.json();
    state.businessProfile = data;
    renderBrandKitPanel();
    closeModal();
    showToast("Brand kit saved", "success");
  } catch (_) { showToast("Failed to save brand kit", "error"); }
}

// ── New Campaign Dialog ───────────────────────────────────────────────────────

function openNewCampaignDialog() {
  const modal = _createModal("New Campaign", `
    <label>Campaign name<input id="camp-name"    placeholder="e.g. Monsoon Warmth" /></label>
    <label>Goal<input          id="camp-goal"    placeholder="e.g. awareness, conversion, seasonal" /></label>
    <label>Season / event<input id="camp-season" placeholder="e.g. Diwali, summer, rainy season" /></label>
    <label>Surfaces (comma-separated)<input id="camp-surfaces" placeholder="e.g. frame, social, print" /></label>
    <div class="modal-actions">
      <button type="button" class="mini-button" onclick="closeModal()">Cancel</button>
      <button type="button" class="mini-button primary" onclick="saveNewCampaign()">Create</button>
    </div>
  `);
  document.body.appendChild(modal);
}

async function saveNewCampaign() {
  const payload = {
    name:     document.getElementById("camp-name").value.trim(),
    goal:     document.getElementById("camp-goal").value.trim(),
    season:   document.getElementById("camp-season").value.trim(),
    surfaces: document.getElementById("camp-surfaces").value.split(",").map((s) => s.trim()).filter(Boolean),
  };
  if (!payload.name) { showToast("Campaign name is required", "error"); return; }
  try {
    const res  = await fetch("/api/campaigns", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    const data = await res.json();
    state.campaigns.unshift(data);
    renderBrandKitPanel();
    closeModal();
    showToast(`Campaign "${payload.name}" created`, "success");
  } catch (_) { showToast("Failed to create campaign", "error"); }
}

// ══════════════════════════════════════════════════════════════════════════════
// MODAL HELPERS
// ══════════════════════════════════════════════════════════════════════════════

function _createModal(title, bodyHTML) {
  const overlay = document.createElement("div");
  overlay.className = "modal-overlay";
  overlay.id = "activeModal";
  overlay.innerHTML = `
    <div class="modal-box">
      <div class="modal-title">${title}</div>
      ${bodyHTML}
    </div>
  `;
  overlay.addEventListener("click", (e) => { if (e.target === overlay) closeModal(); });
  return overlay;
}

function closeModal() {
  const m = document.getElementById("activeModal");
  if (m) m.remove();
}

// ══════════════════════════════════════════════════════════════════════════════
// ATTACHMENTS
// ══════════════════════════════════════════════════════════════════════════════

function renderAttachmentTray() {
  attachmentTray.innerHTML = "";
  if (!state.attachments.length) return;
  state.attachments.forEach((att, i) => {
    const item = document.createElement("div");
    item.className = "attachment-chip";
    item.innerHTML = `
      <img src="${att.url}" alt="${att.name}" />
      <span>${att.name}</span>
      <button type="button" data-index="${i}" title="Remove">×</button>
    `;
    item.querySelector("button").addEventListener("click", () => {
      state.attachments.splice(i, 1);
      renderAttachmentTray();
    });
    attachmentTray.appendChild(item);
  });
}

async function handleUpload(event) {
  const file = event.target.files?.[0];
  if (!file) return;
  const formData = new FormData();
  formData.append("file", file);
  try {
    const res     = await fetch("/api/uploads", { method: "POST", body: formData });
    const payload = await res.json();
    if (!res.ok) throw new Error(payload.detail || "Upload failed");
    state.attachments.push(payload.attachment);
    renderAttachmentTray();
    showToast(`"${file.name}" uploaded`, "success");
  } catch (err) {
    showToast(err.message || "Upload failed", "error");
  } finally {
    fileInput.value = "";
  }
}

// ══════════════════════════════════════════════════════════════════════════════
// MESSAGE RENDERING
// ══════════════════════════════════════════════════════════════════════════════

function renderMessages() {
  messageStream.innerHTML = "";

  // Show welcome state if no messages
  if (!state.messages.length) {
    renderWelcomeState();
    return;
  }

  state.messages.forEach((message, idx) => {
    const fragment    = messageTemplate.content.cloneNode(true);
    const article     = fragment.querySelector(".message-card");
    const roleEl      = fragment.querySelector(".message-role");
    const tag         = fragment.querySelector(".message-tag");
    const text        = fragment.querySelector(".message-text");
    const outputGrid  = fragment.querySelector(".output-grid");
    const attachBox   = fragment.querySelector(".message-attachments");

    article.classList.add(message.role);
    article.style.animationDelay = `${Math.min(idx * 50, 200)}ms`;

    // Build avatar + role
    if (message.role === "assistant") {
      roleEl.innerHTML = `<span class="avatar vizzy">V</span> Vizzy`;
    } else {
      roleEl.innerHTML = `<span class="avatar user-avatar">Y</span> You`;
    }

    tag.textContent  = message.tag || "";
    text.textContent = message.text;

    // Attachments
    if (message.attachments?.length) {
      message.attachments.forEach((att) => {
        const preview = document.createElement("div");
        preview.className = "message-attachment";
        preview.innerHTML = `<img src="${att.url}" alt="${att.name}" /><span>${att.name}</span>`;
        attachBox.appendChild(preview);
      });
    } else {
      attachBox?.remove();
    }

    // Output cards
    if (message.assets?.length) {
      message.assets.forEach((asset) => outputGrid.appendChild(createOutputCard(asset, message)));
    }

    messageStream.appendChild(fragment);
  });

  // Smooth scroll to bottom
  requestAnimationFrame(() => {
    messageStream.scrollTo({ top: messageStream.scrollHeight, behavior: "smooth" });
  });
}

// ── Welcome State ─────────────────────────────────────────────────────────────

function renderWelcomeState() {
  const content = modeContent[state.mode];

  const welcomeDiv = document.createElement("div");
  welcomeDiv.className = "welcome-state";
  welcomeDiv.innerHTML = `
    <div class="welcome-icon">V</div>
    <h2 class="welcome-title">What will you create today?</h2>
    <p class="welcome-subtitle">Start with a prompt, upload a reference image, or try one of these ideas. Vizzy returns visual, narrative, and deploy-ready directions.</p>
    <div class="welcome-suggestions" id="welcomeSuggestions"></div>
  `;

  messageStream.appendChild(welcomeDiv);

  const sugContainer = welcomeDiv.querySelector("#welcomeSuggestions");
  content.welcomeSuggestions.forEach((sug, i) => {
    const card = document.createElement("button");
    card.className = "suggestion-card";
    card.type = "button";
    card.style.animationDelay = `${300 + i * 100}ms`;
    card.style.animation = `fadeInUp 500ms ease-out ${300 + i * 100}ms both`;
    card.innerHTML = `
      <span class="suggestion-icon">${sug.icon}</span>
      <span class="suggestion-text">${sug.text}</span>
    `;
    card.addEventListener("click", () => {
      promptInput.value = sug.text;
      promptInput.focus();
    });
    sugContainer.appendChild(card);
  });
}

// ── Typing Indicator ──────────────────────────────────────────────────────────

function showTypingIndicator() {
  const indicator = document.createElement("div");
  indicator.className = "typing-indicator";
  indicator.id = "typingIndicator";
  indicator.innerHTML = `
    <div class="message-header">
      <span class="message-role"><span class="avatar vizzy">V</span> Vizzy</span>
      <span class="message-tag">Thinking</span>
    </div>
    <div class="typing-dots">
      <span></span><span></span><span></span>
    </div>
    <span class="typing-label">Generating your creative directions...</span>
  `;
  messageStream.appendChild(indicator);
  requestAnimationFrame(() => {
    messageStream.scrollTo({ top: messageStream.scrollHeight, behavior: "smooth" });
  });
}

function hideTypingIndicator() {
  const indicator = document.getElementById("typingIndicator");
  if (indicator) indicator.remove();
}

// ══════════════════════════════════════════════════════════════════════════════
// OUTPUT CARD FACTORY
// ══════════════════════════════════════════════════════════════════════════════

function createOutputCard(asset, message) {
  const fragment   = outputCardTemplate.content.cloneNode(true);
  const image      = fragment.querySelector(".output-image");
  const textBlock  = fragment.querySelector(".output-text");
  const preview    = fragment.querySelector(".output-preview");

  fragment.querySelector(".output-type").textContent        = asset.type;
  fragment.querySelector(".output-title").textContent       = asset.title;
  fragment.querySelector(".output-description").textContent = asset.description;

  if (asset.preview_url) {
    image.src = asset.preview_url;
    image.alt = asset.title;
    // Lightbox on click
    preview.addEventListener("click", () => {
      openLightbox(asset.preview_url, asset.filename);
    });
  } else {
    preview?.classList.add("text-only");
    image?.remove();
  }

  if (asset.text_content) {
    textBlock.textContent = asset.text_content;
  } else {
    textBlock?.remove();
  }

  const actionsContainer = fragment.querySelector(".output-actions");
  (asset.actions || []).forEach((action) => {
    const btn = document.createElement("button");
    btn.type      = "button";
    btn.className = "mini-button";
    btn.textContent = action.label;
    btn.addEventListener("click", () => handleAction(action, asset, message));
    actionsContainer.appendChild(btn);
  });

  // Feedback row for image assets (home mode)
  if (state.mode === "home" && asset.preview_url && asset.type !== "Deploy" && asset.type !== "Copy" && asset.type !== "Story Outline") {
    const feedbackRow = document.createElement("div");
    feedbackRow.className = "feedback-row";
    feedbackRow.innerHTML = `
      <button type="button" class="feedback-btn like"    title="Like this">👍</button>
      <button type="button" class="feedback-btn dislike" title="Dislike this">👎</button>
    `;
    feedbackRow.querySelector(".like").addEventListener("click", (e) => {
      sendFeedback(asset, "like", message);
      e.target.style.background = "var(--success-soft)";
      e.target.style.borderColor = "var(--success)";
    });
    feedbackRow.querySelector(".dislike").addEventListener("click", (e) => {
      sendFeedback(asset, "dislike", message);
      e.target.style.background = "rgba(248,113,113,0.12)";
      e.target.style.borderColor = "var(--error)";
    });
    actionsContainer.appendChild(feedbackRow);
  }

  return fragment;
}

// ══════════════════════════════════════════════════════════════════════════════
// ACTION HANDLER
// ══════════════════════════════════════════════════════════════════════════════

function handleAction(action, asset, message) {
  // Prompt-based refinement
  if (action.prompt_suffix) {
    promptInput.value = `${asset.title}. ${action.prompt_suffix}`;
    promptInput.focus();
    showToast("Refinement prompt loaded — hit Generate", "info");
    return;
  }

  // Named actions
  switch (action.action) {
    case "download":
      if (asset.preview_url) {
        const a = document.createElement("a");
        a.href     = asset.preview_url;
        a.download = asset.filename || "vizzy-output";
        a.click();
        showToast("Download started", "success");
      }
      break;

    case "export_zip":
      void handleExport("zip", asset, message);
      break;

    case "export_print":
      void handleExport("print", asset, message);
      break;

    case "export_email":
      void handleExport("email", asset, message);
      break;

    case "favourite":
      void sendFeedback(asset, "like", message);
      showToast("Added to favourites ❤", "success");
      break;

    case "add_to_campaign":
      openAddToCampaignDialog(asset, message);
      break;

    default:
      if (asset.preview_url) openLightbox(asset.preview_url, asset.filename);
  }
}

// ── Export / Download ──────────────────────────────────────────────────────────

async function handleExport(surface, asset, message) {
  const filenames = (message?.assets || [])
    .filter((a) => a.filename)
    .map((a) => a.filename);

  if (!filenames.length && asset.asset_filenames?.length) {
    filenames.push(...asset.asset_filenames);
  }

  showToast(`Preparing ${surface} export...`, "info");

  try {
    const res  = await fetch("/api/export", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        surface,
        asset_filenames: filenames,
        conversation_id: state.conversationId,
      }),
    });
    const data = await res.json();

    if (data.download_url) {
      const a = document.createElement("a");
      a.href     = data.download_url;
      a.download = "";
      a.click();
      showToast("Download ready", "success");
    } else if (data.download_urls?.length) {
      data.download_urls.forEach((url) => {
        const a = document.createElement("a");
        a.href     = url;
        a.download = "";
        document.body.appendChild(a);
        a.click();
        a.remove();
      });
      showToast(`${data.download_urls.length} files downloaded`, "success");
    } else if (data.stub) {
      _showExportStubModal(surface, data);
    }
  } catch (err) {
    showToast("Export failed: " + (err.message || "Unknown error"), "error");
  }
}

function _showExportStubModal(surface, data) {
  const modal = _createModal(`${surface.charAt(0).toUpperCase() + surface.slice(1)} Export`, `
    <p style="color:var(--ink-secondary); line-height:1.6">${data.note || "This surface export requires additional configuration."}</p>
    ${data.html_template_hint ? `<textarea readonly rows="4" style="width:100%;font-size:0.78rem;margin-top:8px">${data.html_template_hint}</textarea>` : ""}
    <div class="modal-actions"><button type="button" class="mini-button" onclick="closeModal()">Close</button></div>
  `);
  document.body.appendChild(modal);
}

// ── Feedback ──────────────────────────────────────────────────────────────────

async function sendFeedback(asset, signal, message) {
  const prompt = message?.text || "";
  try {
    await fetch("/api/memory/home/feedback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt, asset_filename: asset.filename || "", signal }),
    });
    void loadHomeProfile();
    if (signal === "like") showToast("Taste memory updated ❤", "success");
  } catch (_) {}
}

// ── Add to Campaign ───────────────────────────────────────────────────────────

function openAddToCampaignDialog(asset, message) {
  if (!state.campaigns.length) {
    showToast("No campaigns yet — create one in the Brand Kit panel first", "info");
    return;
  }
  const options = state.campaigns.map((c) => `<option value="${c.id}">${c.name}</option>`).join("");
  const modal = _createModal("Add to Campaign", `
    <label>Select campaign
      <select id="camp-select">${options}</select>
    </label>
    <div class="modal-actions">
      <button type="button" class="mini-button" onclick="closeModal()">Cancel</button>
      <button type="button" class="mini-button primary" onclick="confirmAddToCampaign('${asset.filename || ""}')">Add</button>
    </div>
  `);
  document.body.appendChild(modal);
}

async function confirmAddToCampaign(filename) {
  const campaignId = parseInt(document.getElementById("camp-select").value, 10);
  try {
    await fetch(`/api/campaigns/${campaignId}/assets`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ asset_filenames: [filename] }),
    });
    await loadCampaigns();
    closeModal();
    showToast("Asset added to campaign", "success");
  } catch (_) { showToast("Failed to add to campaign", "error"); }
}

// ══════════════════════════════════════════════════════════════════════════════
// GENERATE (Main flow)
// ══════════════════════════════════════════════════════════════════════════════

async function handleGenerate() {
  const prompt = promptInput.value.trim();
  if (!prompt) { promptInput.focus(); return; }
  if (state.isGenerating) return;

  state.isGenerating = true;
  generateButton.disabled    = true;
  generateButton.textContent = "⏳ Generating...";
  generateButton.classList.add("generating");

  // Add user message immediately
  const userMsg = {
    role: "user",
    tag: state.mode === "home" ? "Prompt" : "Brief",
    text: prompt,
    assets: [],
    attachments: [...state.attachments],
  };
  state.messages.push(userMsg);

  // Clear prompt and attachments
  promptInput.value = "";
  state.attachments = [];
  renderAttachmentTray();
  renderMessages();

  // Show typing indicator
  showTypingIndicator();

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        prompt,
        mode: state.mode,
        conversation_id: state.conversationId,
        attachments: userMsg.attachments,
      }),
    });
    const payload = await res.json();
    if (!res.ok) throw new Error(payload.detail || "Request failed");

    hideTypingIndicator();

    state.conversationId = payload.conversation.id;
    // Replace the provisional user message with the server's version
    state.messages[state.messages.length - 1] = payload.user_message;
    state.messages.push(payload.assistant_message);
    renderMessages();

    await refreshConversations();
    if (state.mode === "home")     void loadHomeProfile();
    if (state.mode === "business") void loadBusinessProfile();

    showToast("Creative directions ready ✨", "success");
  } catch (err) {
    hideTypingIndicator();
    state.messages.push({
      role: "assistant", tag: "Error",
      text: err.message || "Something went wrong. Please try again.",
      assets: [], attachments: [],
    });
    renderMessages();
    showToast(err.message || "Generation failed", "error");
  } finally {
    state.isGenerating = false;
    generateButton.disabled    = false;
    generateButton.textContent = "✨ Generate";
    generateButton.classList.remove("generating");
  }
}

// ══════════════════════════════════════════════════════════════════════════════
// CONVERSATIONS
// ══════════════════════════════════════════════════════════════════════════════

async function refreshConversations() {
  try {
    const res     = await fetch("/api/conversations");
    const payload = await res.json();
    state.conversations = payload;
    renderConversationList();
  } catch (_) {}
}

function renderConversationList() {
  conversationList.innerHTML = "";
  historyCount.textContent = `${state.conversations.length}`;

  if (!state.conversations.length) {
    conversationList.innerHTML = '<div class="history-item" style="text-align:center;color:var(--muted)">No saved chats yet.<br>Your first prompt will start one.</div>';
    return;
  }

  state.conversations.forEach((conv) => {
    const btn = document.createElement("button");
    btn.type      = "button";
    btn.className = "history-item";
    if (conv.id === state.conversationId) btn.classList.add("active");
    btn.innerHTML = `
      <span class="memory-label">${conv.mode}</span>
      <span class="history-item-title">${conv.title}</span>
    `;
    btn.addEventListener("click", () => void loadConversation(conv.id));
    conversationList.appendChild(btn);
  });
}

async function loadConversation(conversationId) {
  try {
    const res     = await fetch(`/api/conversations/${conversationId}`);
    const payload = await res.json();
    state.conversationId = payload.conversation.id;
    state.messages       = payload.messages;
    state.attachments    = [];
    renderAttachmentTray();

    if (payload.conversation.mode !== state.mode) {
      document.querySelectorAll(".mode-button").forEach((btn) => {
        btn.classList.toggle("active", btn.dataset.mode === payload.conversation.mode);
      });
      state.mode = payload.conversation.mode;
      const content = modeContent[state.mode];
      modeSummary.textContent = content.summary;
      renderMemory(content.memory);
      renderContext(content.context);
      renderCoverage(content.coverage);
      renderCapabilities(content.capabilities);
      renderSurfaces(content.surfaces);
      renderQuickPrompts(content.prompts);
    }

    renderMessages();
    renderConversationList();
    renderBrandKitPanel();
    renderDeepMemoryPanel();
    showToast("Conversation loaded", "info");
  } catch (err) {
    showToast("Failed to load conversation", "error");
  }
}

// ══════════════════════════════════════════════════════════════════════════════
// BOOT
// ══════════════════════════════════════════════════════════════════════════════

initializeApp();