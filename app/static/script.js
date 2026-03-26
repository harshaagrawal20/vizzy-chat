const state = {
  mode: "home",
  conversationId: null,
  messages: [],
  conversations: [],
};

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
        "Vizzy reads mood, references, and narrative intent, then returns multiple visual directions you can refine in chat.",
    },
    prompts: [
      "Paint something that feels like how my last year felt.",
      "Turn this photo into a renaissance-style artwork.",
      "Generate a story for my kids, then visualize it scene by scene.",
      "Help me design a quote poster for my living room.",
    ],
  },
  business: {
    summary:
      "Creative and marketing co-pilot for brand visuals, signage, campaigns, social-ready assets, and ambient experiences.",
    memory: [
      { label: "Brand awareness", value: "Understands business type, tone, seasonality, offers, and reusable creative needs" },
      { label: "Preferred outputs", value: "Product visuals, posters, signage, campaigns, loops, branded artwork" },
      { label: "Typical intent", value: "Drive attention and conversion without making the brand feel cheap" },
    ],
    pathway: {
      title: "Brand Intent to Assets",
      body:
        "Vizzy turns a short business brief into visual options that can be reused across in-store screens, social, and print.",
    },
    prompts: [
      "Create premium-looking visuals for this product without making it feel expensive.",
      "Create a sale poster that does not feel cheap.",
      "Design in-store visuals for rainy days.",
      "Create an Apple-esque product video loop.",
    ],
  },
};

const messageStream = document.getElementById("messageStream");
const promptInput = document.getElementById("promptInput");
const generateButton = document.getElementById("generateButton");
const quickPrompts = document.getElementById("quickPrompts");
const modeSummary = document.getElementById("modeSummary");
const memoryList = document.getElementById("memoryList");
const pathwayCard = document.getElementById("pathwayCard");
const conversationList = document.getElementById("conversationList");
const newChatButton = document.getElementById("newChatButton");
const messageTemplate = document.getElementById("messageTemplate");
const outputCardTemplate = document.getElementById("outputCardTemplate");

function initializeApp() {
  bindModeButtons();
  generateButton.addEventListener("click", handleGenerate);
  newChatButton.addEventListener("click", resetChat);
  promptInput.addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
      handleGenerate();
    }
  });
  loadMode("home");
  void refreshConversations();
}

function bindModeButtons() {
  document.querySelectorAll(".mode-button").forEach((button) => {
    button.addEventListener("click", () => {
      setMode(button.dataset.mode);
      document.querySelectorAll(".mode-button").forEach((item) => item.classList.remove("active"));
      button.classList.add("active");
    });
  });
}

function setMode(mode) {
  state.mode = mode;
  const content = modeContent[mode];
  modeSummary.textContent = content.summary;
  promptInput.value = content.prompts[0];
  renderMemory(content.memory);
  renderPathway(content.pathway);
  renderQuickPrompts(content.prompts);
  resetChat();
}

function loadMode(mode) {
  setMode(mode);
}

function resetChat() {
  state.conversationId = null;
  state.messages = [];
  renderMessages();
}

function renderMemory(items) {
  memoryList.innerHTML = "";
  items.forEach((item) => {
    const li = document.createElement("li");
    li.innerHTML = `<span class="memory-label">${item.label}</span>${item.value}`;
    memoryList.appendChild(li);
  });
}

function renderPathway(pathway) {
  pathwayCard.innerHTML = `<span class="memory-label">${pathway.title}</span>${pathway.body}`;
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

function renderMessages() {
  messageStream.innerHTML = "";

  if (!state.messages.length) {
    const empty = document.createElement("article");
    empty.className = "message assistant";
    empty.innerHTML = `
      <div class="message-header">
        <span class="message-role">Vizzy</span>
        <span class="message-tag">Ready</span>
      </div>
      <p class="message-text">Start with a prompt and I'll create multiple free local visual directions for you.</p>
    `;
    messageStream.appendChild(empty);
    return;
  }

  state.messages.forEach((message) => {
    const fragment = messageTemplate.content.cloneNode(true);
    const article = fragment.querySelector(".message");
    const role = fragment.querySelector(".message-role");
    const tag = fragment.querySelector(".message-tag");
    const text = fragment.querySelector(".message-text");
    const outputGrid = fragment.querySelector(".output-grid");

    article.classList.add(message.role);
    role.textContent = message.role === "assistant" ? "Vizzy" : "You";
    tag.textContent = message.tag || "";
    text.textContent = message.text;

    if (message.assets?.length) {
      message.assets.forEach((asset) => {
        outputGrid.appendChild(createOutputCard(asset));
      });
    }

    messageStream.appendChild(fragment);
  });

  messageStream.lastElementChild?.scrollIntoView({ behavior: "smooth", block: "end" });
}

function createOutputCard(asset) {
  const fragment = outputCardTemplate.content.cloneNode(true);
  const image = fragment.querySelector(".output-image");
  fragment.querySelector(".output-type").textContent = asset.type;
  fragment.querySelector(".output-title").textContent = asset.title;
  fragment.querySelector(".output-description").textContent = asset.description;
  image.src = asset.preview_url;
  image.alt = asset.title;

  const actionsContainer = fragment.querySelector(".output-actions");
  asset.actions.forEach((action) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "mini-button";
    button.textContent = action.label;
    actionsContainer.appendChild(button);
  });
  return fragment;
}

async function handleGenerate() {
  const prompt = promptInput.value.trim();
  if (!prompt) {
    promptInput.focus();
    return;
  }

  generateButton.disabled = true;
  generateButton.textContent = "Generating...";

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        prompt,
        mode: state.mode,
        conversation_id: state.conversationId,
      }),
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || "Request failed");
    }

    state.conversationId = payload.conversation.id;
    state.messages.push(payload.user_message, payload.assistant_message);
    renderMessages();
    await refreshConversations();
  } catch (error) {
    const fallback = {
      role: "assistant",
      tag: "Error",
      text: error.message || "Something went wrong.",
      assets: [],
    };
    state.messages.push(fallback);
    renderMessages();
  } finally {
    generateButton.disabled = false;
    generateButton.textContent = "Generate";
  }
}

async function refreshConversations() {
  const response = await fetch("/api/conversations");
  const payload = await response.json();
  state.conversations = payload;
  renderConversationList();
}

function renderConversationList() {
  conversationList.innerHTML = "";
  if (!state.conversations.length) {
    conversationList.innerHTML = '<div class="pathway-card">No saved chats yet. Your first prompt will start one.</div>';
    return;
  }

  state.conversations.forEach((conversation) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "conversation-button";
    if (conversation.id === state.conversationId) {
      button.classList.add("active");
    }
    button.innerHTML = `
      <span class="memory-label">${conversation.mode}</span>
      ${conversation.title}
    `;
    button.addEventListener("click", () => {
      void loadConversation(conversation.id);
    });
    conversationList.appendChild(button);
  });
}

async function loadConversation(conversationId) {
  const response = await fetch(`/api/conversations/${conversationId}`);
  const payload = await response.json();
  state.conversationId = payload.conversation.id;
  state.messages = payload.messages;
  if (payload.conversation.mode !== state.mode) {
    document.querySelectorAll(".mode-button").forEach((button) => {
      button.classList.toggle("active", button.dataset.mode === payload.conversation.mode);
    });
    setMode(payload.conversation.mode);
    state.conversationId = payload.conversation.id;
    state.messages = payload.messages;
  }
  renderMessages();
  renderConversationList();
}

initializeApp();
