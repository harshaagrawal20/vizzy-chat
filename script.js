// ── App State ────────────────────────────────────────────────────────────────
const appState = {
  mode: "home",
  messages: [],
  conversationId: null,
};

// ── Sidebar content ──────────────────────────────────────────────────────────
const modeContent = {
  home: {
    summary:
      "Personal artmaking, storytelling, memory visualization, and iterative co-creation in one place.",
    memory: [
      { label: "Aesthetic pull", value: "Dreamlike, intimate, painterly, emotionally symbolic" },
      { label: "Preferred outputs", value: "Artwork sets, story scenes, quote posters, reflective visuals" },
      { label: "Typical intent", value: "Translate feelings, memories, and goals into tangible visual experiences" },
    ],
    pathway: {
      title: "Emotion to Expression",
      body:
        "AtelierAI reads mood, references, and narrative intent, then suggests multiple visual directions with refinement prompts.",
    },
    prompts: [
      "Paint something that feels like how my last year felt.",
      "Turn this photo into a renaissance-style artwork.",
      "Generate a story for my kids, then visualize it scene by scene.",
      "Who is Albert Einstein? Tell me about his life.",
    ],
  },
  business: {
    summary:
      "Creative and marketing co-pilot for brand visuals, signage, campaigns, social-ready assets, and ambient experiences.",
    memory: [
      { label: "Brand awareness", value: "Understands business type, brand tone, assets, seasonality, and offer goals" },
      { label: "Preferred outputs", value: "Product visuals, posters, signage, campaigns, loops, branded artwork" },
      { label: "Typical intent", value: "Drive attention and conversion without compromising brand perception" },
    ],
    pathway: {
      title: "Brand Intent to Assets",
      body:
        "AtelierAI aligns with your business context, generates campaign-ready options, and adapts them for frame, email, and social surfaces.",
    },
    prompts: [
      "Create premium-looking visuals for this product without making it feel expensive.",
      "Create a sale poster that does not feel cheap.",
      "What is machine learning? Explain with examples.",
      "Calculate 15% of 2500 and explain the result.",
    ],
  },
};

// ── DOM refs ─────────────────────────────────────────────────────────────────
const messageStream = document.getElementById("messageStream");
const promptInput = document.getElementById("promptInput");
const generateButton = document.getElementById("generateButton");
const quickPrompts = document.getElementById("quickPrompts");
const modeSummary = document.getElementById("modeSummary");
const memoryList = document.getElementById("memoryList");
const pathwayCard = document.getElementById("pathwayCard");
const messageTemplate = document.getElementById("messageTemplate");
const outputCardTemplate = document.getElementById("outputCardTemplate");
const mcpCardTemplate = document.getElementById("mcpCardTemplate");

// KG modal
const kgPanel = document.getElementById("kgPanel");
const kgTripleCount = document.getElementById("kgTripleCount");
const kgViewButton = document.getElementById("kgViewButton");
const kgModalOverlay = document.getElementById("kgModalOverlay");
const kgModalClose = document.getElementById("kgModalClose");
const kgFrame = document.getElementById("kgFrame");

// ── Init ─────────────────────────────────────────────────────────────────────
function initializeApp() {
  bindModeButtons();
  generateButton.addEventListener("click", handleGenerate);
  promptInput.addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
      handleGenerate();
    }
  });

  // KG modal events
  kgViewButton.addEventListener("click", openKgModal);
  kgModalClose.addEventListener("click", closeKgModal);
  kgModalOverlay.addEventListener("click", (e) => {
    if (e.target === kgModalOverlay) closeKgModal();
  });

  loadMode("home");
  renderWelcomeMessage();
}

function bindModeButtons() {
  document.querySelectorAll(".mode-button").forEach((button) => {
    button.addEventListener("click", () => {
      loadMode(button.dataset.mode);
      document.querySelectorAll(".mode-button").forEach((item) => item.classList.remove("active"));
      button.classList.add("active");
    });
  });
}

function loadMode(mode) {
  appState.mode = mode;
  const content = modeContent[mode];

  modeSummary.textContent = content.summary;
  promptInput.value = content.prompts[0];
  renderMemory(content.memory);
  renderPathway(content.pathway);
  renderQuickPrompts(content.prompts);
}

// ── Sidebar renders ──────────────────────────────────────────────────────────
function renderMemory(items) {
  memoryList.innerHTML = "";
  items.forEach((item) => {
    const li = document.createElement("li");
    li.innerHTML = `<span class="memory-label">${item.label}</span>${item.value}`;
    memoryList.appendChild(li);
  });
}

function renderPathway(pathway) {
  pathwayCard.innerHTML = `
    <span class="memory-label">${pathway.title}</span>
    ${pathway.body}
  `;
}

function renderQuickPrompts(prompts) {
  quickPrompts.innerHTML = "";
  prompts.forEach((prompt) => {
    const button = document.createElement("button");
    button.className = "chip-button";
    button.type = "button";
    button.textContent = prompt;
    button.addEventListener("click", () => {
      promptInput.value = prompt;
      promptInput.focus();
    });
    quickPrompts.appendChild(button);
  });
}

// ── Welcome message ──────────────────────────────────────────────────────────
function renderWelcomeMessage() {
  messageStream.innerHTML = "";
  const fragment = messageTemplate.content.cloneNode(true);
  fragment.querySelector(".message").classList.add("assistant");
  fragment.querySelector(".message-role").textContent = "AtelierAI";
  fragment.querySelector(".message-tag").textContent = "Welcome";
  fragment.querySelector(".message-text").textContent =
    "Hello! I'm AtelierAI — your creative AI co-pilot. I can generate images, stories, and posters for your home or business. " +
    "I also have an MCP Agent mode: ask me factual questions like \"Who is Nikola Tesla?\" or \"Calculate 256 * 12\" and I'll use tools to answer step-by-step. " +
    "Type a prompt below or pick one of the quick starters!";
  messageStream.appendChild(fragment);
}

// ── Message stream ───────────────────────────────────────────────────────────
function appendMessage(message) {
  const fragment = messageTemplate.content.cloneNode(true);
  const article = fragment.querySelector(".message");
  article.classList.add(message.role);
  fragment.querySelector(".message-role").textContent = message.role === "assistant" ? "AtelierAI" : "You";
  fragment.querySelector(".message-tag").textContent = message.tag || "";
  fragment.querySelector(".message-text").textContent = message.text;

  const outputGrid = fragment.querySelector(".output-grid");
  if (message.assets && message.assets.length) {
    message.assets.forEach((asset) => {
      outputGrid.appendChild(createOutputCard(asset));
    });
  }

  messageStream.appendChild(fragment);
  messageStream.lastElementChild?.scrollIntoView({ behavior: "smooth", block: "end" });
}

// ── Output cards ─────────────────────────────────────────────────────────────
function createOutputCard(asset) {
  const isMcp = asset.type === "MCP Agent" || asset.type === "Final Answer";

  // Choose template
  const template = (isMcp && mcpCardTemplate) ? mcpCardTemplate : outputCardTemplate;
  const fragment = template.content.cloneNode(true);

  // Type badge
  const typeEl = fragment.querySelector(".output-type");
  if (typeEl) typeEl.textContent = asset.type;

  // Title
  const titleEl = fragment.querySelector(".output-title");
  if (titleEl) titleEl.textContent = asset.title || "";

  // Description
  const descEl = fragment.querySelector(".output-description");
  if (descEl) descEl.textContent = asset.description || "";

  // Image preview
  if (asset.preview_url) {
    const preview = fragment.querySelector(".output-preview");
    if (preview) {
      const img = document.createElement("img");
      img.src = asset.preview_url;
      img.alt = asset.title || "Generated image";
      img.style.cssText = "width:100%;height:100%;object-fit:cover;border-radius:inherit;position:absolute;top:0;left:0;";
      preview.style.position = "relative";
      preview.appendChild(img);
      img.addEventListener("click", () => openLightbox(asset.preview_url));
    }
  }

  // Text content (for MCP steps, Copy, Story, etc.)
  if (asset.text_content) {
    // MCP cards use .mcp-steps, others use .output-text-content
    const stepsEl = fragment.querySelector(".mcp-steps");
    const textEl = fragment.querySelector(".output-text-content");

    if (isMcp && stepsEl) {
      renderMcpSteps(stepsEl, asset);
    } else if (textEl) {
      textEl.textContent = asset.text_content;
      textEl.style.display = "block";
    }
  }

  // Action buttons
  const actionsContainer = fragment.querySelector(".output-actions");
  if (actionsContainer && asset.actions) {
    asset.actions.forEach((action) => {
      const label = typeof action === "string" ? action : action.label;
      const button = document.createElement("button");
      button.type = "button";
      button.className = "mini-button";
      button.textContent = label;

      // Handle prompt_suffix actions
      if (action.prompt_suffix) {
        button.addEventListener("click", () => {
          promptInput.value = promptInput.value.trim() + action.prompt_suffix;
          promptInput.focus();
        });
      }
      // Handle download action
      if (action.action === "download" && asset.preview_url) {
        button.addEventListener("click", () => {
          const a = document.createElement("a");
          a.href = asset.preview_url;
          a.download = asset.filename || "atelierai-image";
          a.click();
        });
      }
      actionsContainer.appendChild(button);
    });
  }

  return fragment;
}

// Render MCP reasoning steps nicely
function renderMcpSteps(container, asset) {
  if (!asset.text_content) return;

  const lines = asset.text_content.split("\n").filter(Boolean);
  lines.forEach((line) => {
    const div = document.createElement("div");
    div.className = "mcp-step-line";

    if (line.startsWith("🔧")) {
      div.className += " mcp-tool-call";
    } else if (line.startsWith("📄")) {
      div.className += " mcp-tool-result";
    }

    div.textContent = line;
    container.appendChild(div);
  });

  // Also show full text for Final Answer type
  if (asset.type === "Final Answer") {
    const pre = document.createElement("pre");
    pre.className = "mcp-final-answer";
    pre.textContent = asset.text_content;
    container.appendChild(pre);
  }
}

// ── Simple lightbox ──────────────────────────────────────────────────────────
function openLightbox(url) {
  const overlay = document.createElement("div");
  overlay.style.cssText = `
    position:fixed;inset:0;background:rgba(0,0,0,.85);
    display:flex;align-items:center;justify-content:center;
    z-index:9999;cursor:zoom-out;
  `;
  const img = document.createElement("img");
  img.src = url;
  img.style.cssText = "max-width:90vw;max-height:90vh;border-radius:12px;box-shadow:0 0 60px rgba(0,0,0,.6);";
  overlay.appendChild(img);
  overlay.addEventListener("click", () => document.body.removeChild(overlay));
  document.body.appendChild(overlay);
}

// ── KG Modal ─────────────────────────────────────────────────────────────────
async function openKgModal() {
  if (!appState.conversationId) return;
  kgModalOverlay.style.display = "flex";
  kgFrame.srcdoc = "<body style='background:#0f0f1a;display:flex;align-items:center;justify-content:center;height:100vh;'><p style='color:#a78bfa;font-family:sans-serif;'>Loading graph...</p></body>";

  try {
    const resp = await fetch(`/api/knowledge-graph/${appState.conversationId}/render`);
    const data = await resp.json();
    kgFrame.srcdoc = data.html || "";
  } catch {
    kgFrame.srcdoc = "<body style='background:#0f0f1a;color:#f87171;font-family:sans-serif;padding:2rem;'>Failed to load graph.</body>";
  }
}

function closeKgModal() {
  kgModalOverlay.style.display = "none";
  kgFrame.srcdoc = "";
}

// Update KG panel after each response
async function updateKgPanel() {
  if (!appState.conversationId) return;
  try {
    const resp = await fetch(`/api/knowledge-graph/${appState.conversationId}`);
    const data = await resp.json();
    if (data.triple_count > 0) {
      kgPanel.style.display = "";
      kgTripleCount.textContent = `${data.triple_count} triples`;
    }
  } catch {
    // silent
  }
}

// ── Loading indicator ─────────────────────────────────────────────────────────
function showTypingIndicator() {
  const div = document.createElement("div");
  div.id = "typingIndicator";
  div.className = "message assistant";
  div.innerHTML = `
    <div class="message-header">
      <span class="message-role">AtelierAI</span>
      <span class="message-tag">Thinking…</span>
    </div>
    <p class="message-text" style="display:flex;gap:.3rem;align-items:center;">
      <span class="dot-bounce" style="animation-delay:0s">●</span>
      <span class="dot-bounce" style="animation-delay:.15s">●</span>
      <span class="dot-bounce" style="animation-delay:.3s">●</span>
    </p>`;
  messageStream.appendChild(div);
  div.scrollIntoView({ behavior: "smooth", block: "end" });
}

function hideTypingIndicator() {
  const el = document.getElementById("typingIndicator");
  if (el) el.remove();
}

// ── Generate handler ─────────────────────────────────────────────────────────
async function handleGenerate() {
  const prompt = promptInput.value.trim();
  if (!prompt) {
    promptInput.focus();
    return;
  }

  // Disable button during request
  generateButton.disabled = true;
  generateButton.textContent = "Generating…";

  // Show user message immediately
  appendMessage({
    role: "user",
    tag: appState.mode === "home" ? "Prompt" : "Brief",
    text: prompt,
  });
  promptInput.value = "";
  showTypingIndicator();

  try {
    const payload = {
      prompt,
      mode: appState.mode,
      conversation_id: appState.conversationId,
      attachments: [],
    };

    const resp = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!resp.ok) throw new Error(`Server error: ${resp.status}`);
    const data = await resp.json();

    // Update state
    appState.conversationId = data.conversation?.id ?? appState.conversationId;

    hideTypingIndicator();

    // Show assistant reply
    const assistantMsg = data.assistant_message;
    appendMessage({
      role: "assistant",
      tag: assistantMsg.tag || "Response",
      text: assistantMsg.text,
      assets: assistantMsg.assets || [],
    });

    // Update KG panel in background
    updateKgPanel();

  } catch (err) {
    hideTypingIndicator();
    appendMessage({
      role: "assistant",
      tag: "Error",
      text: `Something went wrong: ${err.message}. Make sure the server is running.`,
    });
  } finally {
    generateButton.disabled = false;
    generateButton.textContent = "Generate";
  }
}

initializeApp();
