const appState = {
  mode: "home",
  messages: [],
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
        "Vizzy reads mood, references, and narrative intent, then suggests multiple visual directions with refinement prompts.",
    },
    prompts: [
      "Paint something that feels like how my last year felt.",
      "Turn this photo into a renaissance-style artwork.",
      "Generate a story for my kids, then visualize it scene by scene.",
      "Make a vision board with my goals for the next 3 years.",
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
        "Vizzy aligns with your business context, generates campaign-ready options, and adapts them for frame, email, and social surfaces.",
    },
    prompts: [
      "Create premium-looking visuals for this product without making it feel expensive.",
      "Create a sale poster that does not feel cheap.",
      "Design in-store visuals for rainy days.",
      "Create an Apple-esque product video loop.",
    ],
  },
};

const starterConversation = {
  home: [
    {
      role: "user",
      tag: "Prompt",
      text: "Show me my inner emotional landscape right now.",
    },
    {
      role: "assistant",
      tag: "Creative plan",
      text:
        "I interpreted this as an introspective visual request. I can express it as atmospheric artwork, a symbolic map, and a guided journaling poster so you can choose the form that resonates most.",
      outputs: [
        {
          type: "Artwork",
          title: "Symbolic Terrain",
          description: "Layered abstract valleys, warm storm light, and handwritten emotional markers.",
          actions: ["Refine palette", "Generate 4 more", "Display on frame"],
        },
        {
          type: "Poster",
          title: "Reflective Mood Map",
          description: "An elegant emotional landscape with short affirmations and subtle cartographic labels.",
          actions: ["Add quote", "Export print", "Share"],
        },
        {
          type: "Journal",
          title: "Prompted Reflection",
          description: "A companion page that turns the artwork into a guided self-reflection session.",
          actions: ["Open prompts", "Save session"],
        },
      ],
    },
  ],
  business: [
    {
      role: "user",
      tag: "Brief",
      text: "Create premium-looking visuals for this product without making it feel expensive.",
    },
    {
      role: "assistant",
      tag: "Campaign route",
      text:
        "I balanced premium cues with warmth and accessibility. Here are three outputs tuned for in-store screens, social placements, and quick promotional reuse.",
      outputs: [
        {
          type: "Visual",
          title: "Hero Product Still",
          description: "Soft directional lighting, tactile detail, and restrained composition to elevate perceived quality.",
          actions: ["Make warmer", "Add logo", "Export social"],
        },
        {
          type: "Signage",
          title: "Quiet Luxury Offer Card",
          description: "Minimal promotional language with refined typography so the value feels curated, not discounted.",
          actions: ["Shorten copy", "Resize for frame"],
        },
        {
          type: "Loop",
          title: "Ambient Product Motion",
          description: "A seamless visual loop for digital display with elegant movement and subtle product reveals.",
          actions: ["Add CTA", "Export MP4"],
        },
      ],
    },
  ],
};

const messageStream = document.getElementById("messageStream");
const promptInput = document.getElementById("promptInput");
const generateButton = document.getElementById("generateButton");
const quickPrompts = document.getElementById("quickPrompts");
const modeSummary = document.getElementById("modeSummary");
const memoryList = document.getElementById("memoryList");
const pathwayCard = document.getElementById("pathwayCard");
const messageTemplate = document.getElementById("messageTemplate");
const outputCardTemplate = document.getElementById("outputCardTemplate");

function initializeApp() {
  bindModeButtons();
  generateButton.addEventListener("click", handleGenerate);
  promptInput.addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
      handleGenerate();
    }
  });
  loadMode("home");
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
  const conversation = starterConversation[mode];

  modeSummary.textContent = content.summary;
  promptInput.value = content.prompts[0];
  renderMemory(content.memory);
  renderPathway(content.pathway);
  renderQuickPrompts(content.prompts);
  appState.messages = [...conversation];
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

function renderMessages() {
  messageStream.innerHTML = "";
  appState.messages.forEach((message) => {
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

    if (message.outputs) {
      message.outputs.forEach((output) => {
        outputGrid.appendChild(createOutputCard(output));
      });
    }

    messageStream.appendChild(fragment);
  });

  messageStream.lastElementChild?.scrollIntoView({ behavior: "smooth", block: "end" });
}

function createOutputCard(output) {
  const fragment = outputCardTemplate.content.cloneNode(true);
  fragment.querySelector(".output-type").textContent = output.type;
  fragment.querySelector(".output-title").textContent = output.title;
  fragment.querySelector(".output-description").textContent = output.description;

  const actionsContainer = fragment.querySelector(".output-actions");
  output.actions.forEach((actionLabel) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "mini-button";
    button.textContent = actionLabel;
    actionsContainer.appendChild(button);
  });

  return fragment;
}

function handleGenerate() {
  const prompt = promptInput.value.trim();
  if (!prompt) {
    promptInput.focus();
    return;
  }

  appState.messages.push({
    role: "user",
    tag: appState.mode === "home" ? "Prompt" : "Brief",
    text: prompt,
  });

  appState.messages.push(buildAssistantResponse(prompt, appState.mode));
  renderMessages();
}

function buildAssistantResponse(prompt, mode) {
  const lowerPrompt = prompt.toLowerCase();
  const isStory = lowerPrompt.includes("story") || lowerPrompt.includes("kids");
  const isPoster = lowerPrompt.includes("poster") || lowerPrompt.includes("signage");
  const isVideo = lowerPrompt.includes("video") || lowerPrompt.includes("loop");
  const primaryType = isVideo ? "Loop" : isPoster ? "Poster" : isStory ? "Story" : "Artwork";

  const outputs = [
    {
      type: primaryType,
      title: mode === "home" ? "Primary Concept" : "Primary Campaign Asset",
      description:
        mode === "home"
          ? "A polished first direction based on your words, mood, and likely visual intent."
          : "A lead creative treatment aligned to your brand intent, offer, and customer perception goals.",
      actions: ["Refine", "Generate variants", "Approve"],
    },
    {
      type: "Variation Set",
      title: mode === "home" ? "Alternate Interpretations" : "Channel Adaptations",
      description:
        mode === "home"
          ? "Additional directions that shift style, symbolism, and emotional emphasis."
          : "Ready-to-adapt versions for in-store display, social sharing, and customer messaging.",
      actions: ["Compare", "Mix styles"],
    },
    {
      type: mode === "home" ? "Memory" : "Deploy",
      title: mode === "home" ? "Taste Memory Update" : "Publishing Actions",
      description:
        mode === "home"
          ? "Learns from this request to personalize future visuals and suggestions."
          : "Queues this concept for frame display, email export, or campaign reuse across surfaces.",
      actions: mode === "home" ? ["Save preference"] : ["Frame", "Email", "Social"],
    },
  ];

  return {
    role: "assistant",
    tag: mode === "home" ? "Generated response" : "Asset response",
    text:
      mode === "home"
        ? `I interpreted "${prompt}" as a ${primaryType.toLowerCase()} request and prepared a main concept, alternates, and a memory update so future generations feel more like you.`
        : `I interpreted "${prompt}" as a brand-facing ${primaryType.toLowerCase()} request and prepared a lead asset, channel-ready adaptations, and deploy options for quick reuse.`,
    outputs,
  };
}

initializeApp();
