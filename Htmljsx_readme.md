<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>AI Content Research OS Prototype</title>
    <!-- React and ReactDOM CDN -->
    <script crossorigin src="https://unpkg.com/react@18/umd/react.development.js"></script>
    <script crossorigin src="https://unpkg.com/react-dom@18/umd/react-dom.development.js"></script>
    <!-- Babel for JSX transformation in browser -->
    <script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
    <style>
        /* src/assets/index.css - FROZEN */
        body {
            margin: 0;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen',
                'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue',
                sans-serif;
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
        }

        code {
            font-family: source-code-pro, Menlo, Monaco, Consolas, 'Courier New',
                monospace;
        }

        /* Basic Tailwind-like utilities for demonstration */
        .min-h-screen { min-height: 100vh; }
        .bg-gray-100 { background-color: #f3f4f6; }
        .p-4 { padding: 1rem; }
        .font-sans { font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Noto Sans", sans-serif, "Apple Color Emoji", "Segoe UI Emoji", "Segoe UI Symbol", "Noto Color Emoji"; }
        .max-w-4xl { max-width: 56rem; }
        .mx-auto { margin-left: auto; margin-right: auto; }
        .bg-white { background-color: #ffffff; }
        .shadow-lg { box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05); }
        .rounded-lg { border-radius: 0.5rem; }
        .p-6 { padding: 1.5rem; }
        .text-3xl { font-size: 1.875rem; line-height: 2.25rem; }
        .font-bold { font-weight: 700; }
        .text-gray-800 { color: #1f2937; }
        .mb-6 { margin-bottom: 1.5rem; }
        .text-center { text-align: center; }
        .mb-4 { margin-bottom: 1rem; }
        .space-y-4 > *:not([hidden]) ~ *:not([hidden]) { margin-top: 1rem; }
        .block { display: block; }
        .text-gray-700 { color: #374151; }
        .text-sm { font-size: 0.875rem; line-height: 1.25rem; }
        .mb-2 { margin-bottom: 0.5rem; }
        .shadow { box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06); }
        .appearance-none { appearance: none; }
        .border { border-width: 1px; border-color: #e5e7eb; }
        .rounded { border-radius: 0.25rem; }
        .w-full { width: 100%; }
        .py-2 { padding-top: 0.5rem; padding-bottom: 0.5rem; }
        .px-3 { padding-left: 0.75rem; padding-right: 0.75rem; }
        .leading-tight { line-height: 1.25; }
        .focus\:outline-none:focus { outline: 2px solid transparent; outline-offset: 2px; }
        .focus\:shadow-outline:focus { box-shadow: 0 0 0 3px rgba(66, 153, 225, 0.5); } /* Blue outline */
        .flex { display: flex; }
        .flex-col { flex-direction: column; }
        .flex-1 { flex: 1 1 0%; }
        .sm\:flex-row { flex-direction: row; }
        .sm\:space-x-4 > *:not([hidden]) ~ *:not([hidden]) { margin-left: 1rem; }
        .sm\:space-y-0 > *:not([hidden]) ~ *:not([hidden]) { margin-top: 0; }
        .bg-blue-600 { background-color: #2563eb; }
        .hover\:bg-blue-700:hover { background-color: #1d4ed8; }
        .text-white { color: #ffffff; }
        .px-4 { padding-left: 1rem; padding-right: 1rem; }
        .rounded { border-radius: 0.25rem; }
        .opacity-50 { opacity: 0.5; }
        .cursor-not-allowed { cursor: not-allowed; }
        .text-center { text-align: center; }
        .py-4 { padding-top: 1rem; padding-bottom: 1rem; }
        .text-blue-500 { color: #3b82f6; }

        /* Loader specific styles */
        .loader {
            border-top-color: #3b82f6; /* Blue for the loading indicator */
            animation: spin 1s linear infinite;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .h-12 { height: 3rem; }
        .w-12 { width: 3rem; }
        .mb-4 { margin-bottom: 1rem; }
        .mx-auto { margin-left: auto; margin-right: auto; }

        /* Error alert styles */
        .bg-red-100 { background-color: #fee2e2; }
        .border-red-400 { border-color: #f87171; }
        .text-red-700 { color: #b91c1c; }
        .relative { position: relative; }
        .block { display: block; }
        .sm\:inline { display: inline; }

        /* Results section */
        .mt-8 { margin-top: 2rem; }
        .space-y-8 > *:not([hidden]) ~ *:not([hidden]) { margin-top: 2rem; }
        .text-2xl { font-size: 1.5rem; line-height: 2rem; }
        .border-b { border-bottom-width: 1px; border-color: #e5e7eb; }
        .pb-2 { padding-bottom: 0.5rem; }
        .text-xl { font-size: 1.25rem; line-height: 1.75rem; }
        .font-semibold { font-weight: 600; }
        .text-gray-700 { color: #374151; }
        .list-disc { list-style-type: disc; }
        .list-inside { list-style-position: inside; }
        .text-gray-600 { color: #4b5563; }
        .space-y-3 > *:not([hidden]) ~ *:not([hidden]) { margin-top: 0.75rem; }
        .bg-gray-50 { background-color: #f9fafb; }
        .p-3 { padding: 0.75rem; }
        .rounded-md { border-radius: 0.375rem; }
        .border-gray-200 { border-color: #e5e7eb; }
        .font-medium { font-weight: 500; }
        .text-sm { font-size: 0.875rem; line-height: 1.25rem; }
        .grid { display: grid; }
        .grid-cols-2 { grid-template-columns: repeat(2, minmax(0, 1fr)); }
        .gap-2 { gap: 0.5rem; }
        .mt-4 { margin-top: 1rem; }
        .pt-4 { padding-top: 1rem; }
        .border-t { border-top-width: 1px; border-color: #e5e7eb; }
        .text-gray-500 { color: #6b7280; }
        .bg-red-50 { background-color: #fef2f2; }
        .border-red-300 { border-color: #fca5a5; }
        .text-red-600 { color: #dc2626; }

        /* Mobile UI (basic example, extend in index.css for full responsiveness) */
        @media (max-width: 640px) {
            .mobile-ui .flex-col.sm\:flex-row {
                flex-direction: column;
            }
            .mobile-ui .sm\:space-x-4 > *:not([hidden]) ~ *:not([hidden]) {
                margin-left: 0;
                margin-top: 1rem; /* Adjust as needed for vertical spacing */
            }
            .mobile-ui .sm\:space-y-0 > *:not([hidden]) ~ *:not([hidden]) {
                margin-top: 1rem; /* Ensure vertical spacing */
            }
        }
    </style>
</head>
<body>
    <div id="root"></div>

    <script type="text/babel">
        // --- src/providers/llmRouter.js ---
        // This file abstracts communication with various LLM providers.
        // It handles provider selection, model routing, error handling, and response normalization.

        // Placeholder for API Keys🔥 - in a real app, these would be managed securely (e.g., environment variables, backend)
        const API_KEYS = {
            openrouter: "YOUR_OPENROUTER_API_KEY",
            googleAIStudio: "YOUR_GOOGLE_AI_STUDIO_API_KEY",
            huggingface: "YOUR_HUGGINGFACE_API_KEY",
            cloudflareAI: "YOUR_CLOUDFLARE_WORKERS_AI_TOKEN" // For Cloudflare Workers AI
            // Add other provider API keys here
        };

        const DEFAULT_TIMEOUT = 15000; // Default timeout for LLM calls

        // LLM Provider configurations 🎯
        const providersConfig = {
            openrouter: {
                name: "OpenRouter",
                endpoint: "https://openrouter.ai/api/v1/chat/completions",
                models: [
                    { id: "openai/gpt-4o", name: "GPT-4o (OpenRouter)" },
                    { id: "google/gemini-pro", name: "Gemini Pro (OpenRouter)" },
                    { id: "anthropic/claude-3-haiku", name: "Claude 3 Haiku (OpenRouter)" }
                ],
                headers: (apiKey) => ({
                    "Authorization": `Bearer ${apiKey}`,
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://example.com", // Replace with your actual app URL
                    "X-Title": "AI Content Research OS"
                }),
                // Adapter for OpenRouter specific request/response
                adapter: async (prompt, options, apiKey) => {
                    const response = await fetch(providersConfig.openrouter.endpoint, {
                        method: "POST",
                        headers: providersConfig.openrouter.headers(apiKey),
                        body: JSON.stringify({
                            model: options.model,
                            messages: [{ role: "user", content: prompt }],
                            response_format: options.outputSchema ? { type: "json_object" } : undefined,
                            temperature: 0.7,
                            max_tokens: 1000
                        }),
                        signal: options.signal
                    });
                    return response.json();
                },
                normalize: (rawResponse, options) => {
                    if (rawResponse.choices && rawResponse.choices.length > 0) {
                        const content = rawResponse.choices[0].message.content;
                        try {
                            const data = options.outputSchema ? JSON.parse(content) : content;
                            return { success: true, data, provider: "openrouter", model: options.model, metadata: { latency: options.latency } };
                        } catch (e) {
                            return { success: false, error: "Failed to parse JSON response from OpenRouter.", provider: "openrouter", model: options.model, metadata: { latency: options.latency } };
                        }
                    }
                    return { success: false, error: rawResponse.error?.message || "OpenRouter: Unknown error", provider: "openrouter", model: options.model, metadata: { latency: options.latency } };
                }
            },
            googleAIStudio: {
                name: "Google AI Studio",
                endpoint: "https://generativelanguage.googleapis.com/v1beta/models/",
                models: [
                    { id: "gemini-pro", name: "Gemini Pro" }
                ],
                headers: (apiKey) => ({
                    "Content-Type": "application/json"
                }),
                adapter: async (prompt, options, apiKey) => {
                    const endpoint = `${providersConfig.googleAIStudio.endpoint}${options.model}:generateContent?key=${apiKey}`;
                    const response = await fetch(endpoint, {
                        method: "POST",
                        headers: providersConfig.googleAIStudio.headers(apiKey),
                        body: JSON.stringify({
                            contents: [{ parts: [{ text: prompt }] }],
                            generationConfig: options.outputSchema ? { response_mime_type: "application/json" } : undefined,
                            safetySettings: [ // Basic safety settings for demonstration
                              { category: "HARM_CATEGORY_HARASSMENT", threshold: "BLOCK_MEDIUM_AND_ABOVE" },
                              { category: "HARM_CATEGORY_HATE_SPEECH", threshold: "BLOCK_MEDIUM_AND_ABOVE" },
                              { category: "HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold: "BLOCK_MEDIUM_AND_ABOVE" },
                              { category: "HARM_CATEGORY_DANGEROUS_CONTENT", threshold: "BLOCK_MEDIUM_AND_ABOVE" },
                            ],
                        }),
                        signal: options.signal
                    });
                    return response.json();
                },
                normalize: (rawResponse, options) => {
                    if (rawResponse.candidates && rawResponse.candidates.length > 0) {
                        const content = rawResponse.candidates[0].content.parts[0].text;
                        try {
                            const data = options.outputSchema ? JSON.parse(content) : content;
                            return { success: true, data, provider: "googleAIStudio", model: options.model, metadata: { latency: options.latency } };
                        } catch (e) {
                            return { success: false, error: "Failed to parse JSON response from Google AI Studio.", provider: "googleAIStudio", model: options.model, metadata: { latency: options.latency } };
                        }
                    }
                    return { success: false, error: rawResponse.promptFeedback?.blockReason || rawResponse.error?.message || "Google AI Studio: Unknown error or blocked content", provider: "googleAIStudio", model: options.model, metadata: { latency: options.latency } };
                }
            },
            // Add other LLM providers here (e.g., HuggingFace Inference, Cloudflare Workers AI)
            // Example structure for a generic API (e.g., some HuggingFace endpoints or custom local LLM)
            genericAPI: {
                name: "Generic API",
                endpoint: "http://localhost:11434/api/generate", // Example Ollama endpoint
                models: [{ id: "llama2", name: "Llama 2 (Ollama)" }],
                headers: () => ({
                    "Content-Type": "application/json"
                }),
                adapter: async (prompt, options, apiKey) => {
                    // This adapter assumes a simple API that takes a prompt and returns a JSON response
                    const response = await fetch(options.endpoint || providersConfig.genericAPI.endpoint, {
                        method: "POST",
                        headers: providersConfig.genericAPI.headers(),
                        body: JSON.stringify({
                            model: options.model,
                            prompt: prompt,
                            stream: false,
                            format: options.outputSchema ? "json" : undefined // Ollama specific JSON format
                        }),
                        signal: options.signal
                    });
                    return response.json();
                },
                normalize: (rawResponse, options) => {
                    // This normalization is highly dependent on the generic API's response structure
                    if (rawResponse.response) {
                        try {
                            const data = options.outputSchema ? JSON.parse(rawResponse.response) : rawResponse.response;
                            return { success: true, data, provider: "genericAPI", model: options.model, metadata: { latency: options.latency } };
                        } catch (e) {
                            return { success: false, error: "Failed to parse JSON response from Generic API.", provider: "genericAPI", model: options.model, metadata: { latency: options.latency } };
                        }
                    }
                    return { success: false, error: rawResponse.error || "Generic API: Unknown error", provider: "genericAPI", model: options.model, metadata: { latency: options.latency } };
                }
            }
        };
       // let currentProviderName = "genericAPI"; can change before 🔥
        let currentProviderName = "openrouter"; // Default provider

        // AIProvider Interface
        const AIProvider = {
            // Analyzes a prompt using the selected LLM provider and model.
            async analyze(prompt, options = {}) {
                const { providerName = currentProviderName, model, timeout = DEFAULT_TIMEOUT, outputSchema } = options;
                const provider = providersConfig[providerName];
                const apiKey = API_KEYS[providerName];

                if (!provider) {
                    return { success: false, error: `Provider "${providerName}" not configured.`, provider: providerName, model, metadata: { latency: 0 } };
                }
                if (!apiKey || apiKey === `YOUR_${providerName.toUpperCase()}_API_KEY`) {
                    return { success: false, error: `API Key for ${providerName} is not configured.`, provider: providerName, model, metadata: { latency: 0 } };
                }
                if (!model) {
                    return { success: false, error: `No model selected for provider "${providerName}".`, provider: providerName, model, metadata: { latency: 0 } };
                }

                const controller = new AbortController();
                const signal = controller.signal;
                const timer = setTimeout(() => controller.abort(), timeout);
                const startTime = Date.now();

                try {
                    const rawResponse = await provider.adapter(prompt, { ...options, model, signal }, apiKey);
                    clearTimeout(timer);
                    const latency = Date.now() - startTime;
                    return provider.normalize(rawResponse, { ...options, model, latency });
                } catch (err) {
                    clearTimeout(timer);
                    const latency = Date.now() - startTime;
                    let errorMessage = err.name === 'AbortError' ? `Request timed out after ${timeout}ms.` : err.message;
                    return { success: false, error: `${providerName}: ${errorMessage}`, provider: providerName, model, metadata: { latency } };
                }
            },

            // Sets the active LLM provider.
            setProvider(name) {
                if (providersConfig[name]) {
                    currentProviderName = name;
                    return true;
                }
                console.warn(`Provider "${name}" not found.`);
                return false;
            },

            // Gets the name of the current active provider.
            getCurrentProviderName() {
                return currentProviderName;
            },

            // Lists all configured providers and their available models.
            listProviders() {
                return providersConfig;
            }
        };

        // --- src/agents/discoveryAgent.js ---
        // Runs the Discovery Agent to find viral content opportunities.

        async function runDiscovery({ task, platform, providerName, model, timeout }) {
          const agentStartTime = Date.now();
          let agentOutput = {
            agent: "DiscoveryAgent",
            version: "1.0.0",
            capability: [
              "viral discovery",
              "trend analysis",
              "keyword extraction"
            ],
            result: {
              videoCandidates: [],
              trendSignals: [],
              keywords: []
            },
            metadata: {
              provider: "N/A",
              model: "N/A",
              latency: 0,
              timestamp: new Date().toISOString()
            },
            error: null
          };

          try {
            const prompt = `Based on the topic "${task}" for platform "${platform}", identify potential viral video opportunities. Provide a list of video candidates, key trend signals, and relevant SEO keywords. Ensure the output is concise and actionable for content creation.`;

            const llmResponse = await AIProvider.analyze(prompt, {
              providerName,
              model,
              timeout,
              outputSchema: {
                type: "object",
                properties: {
                  videoCandidates: {
                    type: "array",
                    items: { type: "string" },
                    description: "List of viral video ideas or titles"
                  },
                  trendSignals: {
                    type: "array",
                    items: { type: "string" },
                    description: "Key trends and insights related to the topic"
                  },
                  keywords: {
                    type: "array",
                    items: { type: "string" },
                    description: "Relevant SEO keywords for the content"
                  }
                },
                required: ["videoCandidates", "trendSignals", "keywords"]
              }
            });

            if (llmResponse.success) {
              const llmData = llmResponse.data;
              agentOutput.result.videoCandidates = Array.isArray(llmData?.videoCandidates) ? llmData.videoCandidates : [];
              agentOutput.result.trendSignals = Array.isArray(llmData?.trendSignals) ? llmData.trendSignals : [];
              agentOutput.result.keywords = Array.isArray(llmData?.keywords) ? llmData.keywords : [];

              agentOutput.metadata.provider = llmResponse.provider || "Unknown";
              agentOutput.metadata.model = llmResponse.model || "Unknown";
              agentOutput.metadata.latency = llmResponse.metadata?.latency || (Date.now() - agentStartTime);
              agentOutput.metadata.timestamp = llmResponse.metadata?.timestamp || new Date().toISOString();
              agentOutput.metadata.capabilities = llmResponse.metadata?.capabilities || [];

            } else {
              agentOutput.error = llmResponse.error || `LLM analysis failed for Discovery Agent with provider ${providerName || 'default'}.`;
              console.error(`Discovery Agent LLM Call Failed: ${agentOutput.error}`);
            }

          } catch (err) {
            agentOutput.error = `Discovery Agent execution error: ${err.message}`;
            console.error(`Discovery Agent Error:`, err);
          } finally {
            agentOutput.metadata.latency = Date.now() - agentStartTime;
          }

          return agentOutput;
        }

        // --- src/agents/scoringAgent.js ---
        // Runs the Scoring Agent to calculate content quality scores.

        async function runScoring({ contentDescription, platform, providerName, model, timeout }) {
          const agentStartTime = Date.now();
          const scoringWeights = {
            viral: 0.25,
            emotion: 0.20,
            trend: 0.15,
            hook: 0.15,
            replay: 0.10,
            rarity: 0.10,
            competition: 0.05
          };

          let agentOutput = {
            agent: "ScoringAgent",
            version: "1.0.0",
            capability: [
              "viral scoring",
              "content evaluation",
              "retention analysis"
            ],
            result: {
              viralScore: 0,
              emotionScore: 0,
              trendScore: 0,
              hookScore: 0,
              replayScore: 0,
              rarityScore: 0,
              competitionScore: 0,
              finalScore: 0,
              reasoning: "Scores not calculated due to an error or incomplete data."
            },
            metadata: {
              provider: "N/A",
              model: "N/A",
              latency: 0,
              timestamp: new Date().toISOString()
            },
            error: null
          };

          try {
            const prompt = `Analyze the content idea "${contentDescription}" for platform "${platform || 'general'}" and provide individual scores (0-100) for its virality, emotional impact, trend relevance, hook effectiveness, replay value, rarity/uniqueness, and competitive landscape. Also provide a brief reasoning for these scores.`;

            const llmResponse = await AIProvider.analyze(prompt, {
              providerName,
              model,
              timeout,
              outputSchema: {
                type: "object",
                properties: {
                  viralScore: { type: "integer", minimum: 0, maximum: 100 },
                  emotionScore: { type: "integer", minimum: 0, maximum: 100 },
                  trendScore: { type: "integer", minimum: 0, maximum: 100 },
                  hookScore: { type: "integer", minimum: 0, maximum: 100 },
                  replayScore: { type: "integer", minimum: 0, maximum: 100 },
                  rarityScore: { type: "integer", minimum: 0, maximum: 100 },
                  competitionScore: { type: "integer", minimum: 0, maximum: 100 },
                  reasoning: { type: "string" }
                },
                required: ["viralScore", "emotionScore", "trendScore", "hookScore", "replayScore", "rarityScore", "competitionScore", "reasoning"]
              }
            });

            if (llmResponse.success && llmResponse.data) {
              const llmData = llmResponse.data;

              // Validate and assign scores, defaulting to 0 if missing or out of range
              const getValidScore = (score) => Math.min(100, Math.max(0, parseInt(score, 10) || 0));

              agentOutput.result.viralScore = getValidScore(llmData.viralScore);
              agentOutput.result.emotionScore = getValidScore(llmData.emotionScore);
              agentOutput.result.trendScore = getValidScore(llmData.trendScore);
              agentOutput.result.hookScore = getValidScore(llmData.hookScore);
              agentOutput.result.replayScore = getValidScore(llmData.replayScore);
              agentOutput.result.rarityScore = getValidScore(llmData.rarityScore);
              agentOutput.result.competitionScore = getValidScore(llmData.competitionScore);
              agentOutput.result.reasoning = llmData.reasoning || "No specific reasoning provided by LLM.";

              // Calculate finalScore using weighted formula
              agentOutput.result.finalScore = Math.round(
                (agentOutput.result.viralScore * scoringWeights.viral) +
                (agentOutput.result.emotionScore * scoringWeights.emotion) +
                (agentOutput.result.trendScore * scoringWeights.trend) +
                (agentOutput.result.hookScore * scoringWeights.hook) +
                (agentOutput.result.replayScore * scoringWeights.replay) +
                (agentOutput.result.rarityScore * scoringWeights.rarity) +
                (agentOutput.result.competitionScore * scoringWeights.competition)
              );

              // Populate metadata from LLM response
              agentOutput.metadata.provider = llmResponse.provider || "Unknown";
              agentOutput.metadata.model = llmResponse.model || "Unknown";
              agentOutput.metadata.latency = llmResponse.metadata?.latency || (Date.now() - agentStartTime);
              agentOutput.metadata.timestamp = llmResponse.metadata?.timestamp || new Date().toISOString();
              agentOutput.metadata.capabilities = llmResponse.metadata?.capabilities || [];

            } else {
              agentOutput.error = llmResponse.error || `LLM analysis failed for Scoring Agent with provider ${providerName || 'default'}.`;
              console.error(`Scoring Agent LLM Call Failed: ${agentOutput.error}`);
            }

          } catch (err) {
            agentOutput.error = `Scoring Agent execution error: ${err.message}`;
            console.error(`Scoring Agent Error:`, err);
          } finally {
            agentOutput.metadata.latency = Date.now() - agentStartTime;
          }

          return agentOutput;
        }

        // --- src/agents/rankingAgent.js ---
        // Runs the Ranking Agent to generate a 6-Rank content structure and predict retention.

        async function runRanking({ contentDescription, platform, providerName, model, timeout }) {
          const agentStartTime = Date.now();
          let agentOutput = {
            agent: "RankingAgent",
            version: "1.0.0",
            capability: [
              "content ranking",
              "retention prediction",
              "narrative structuring",
              "6-rank viral framework",
              "retention optimization" // Added capability
            ],
            result: {
              rankOrder: [],
              retentionPrediction: "No ranking performed due to an error or incomplete data."
            },
            metadata: {
              provider: "N/A",
              model: "N/A",
              latency: 0,
              timestamp: new Date().toISOString()
            },
            error: null
          };

          try {
            const prompt = `Given the content idea: "${contentDescription}" (targeting ${platform || 'general platforms'}), create a 6-rank narrative structure for optimal viewer retention. The structure should go from #6 (Hook) to #1 (Payoff), defining each segment's purpose. Also, provide a brief prediction about overall content retention.

            Use the following ranks and segments:
            #6: Hook (Initial grab)
            #5: Interest (Build curiosity)
            #4: Context (Provide background)
            #3: Escalation (Increase tension/stakes)
            #2: False Winner (Introduce a twist or misleading resolution)
            #1: Payoff (Satisfying conclusion/main value)

            Provide the output in a structured JSON format with segments and a retention prediction.`;

            const llmResponse = await AIProvider.analyze(prompt, {
              providerName,
              model,
              timeout,
              outputSchema: {
                type: "object",
                properties: {
                  rankOrder: {
                    type: "array",
                    items: {
                      type: "object",
                      properties: {
                        rank: { type: "string", pattern: "^#([1-6])$" },
                        segment: { type: "string" },
                        content: { type: "string" }
                      },
                      required: ["rank", "segment", "content"]
                    },
                    minItems: 6,
                    maxItems: 6,
                    description: "Ordered array of 6 rank segments from #6 to #1"
                  },
                  retentionPrediction: {
                    type: "string",
                    description: "A textual prediction about content retention based on the structure."
                  }
                },
                required: ["rankOrder", "retentionPrediction"]
              }
            });

            if (llmResponse.success && llmResponse.data) {
              const llmData = llmResponse.data;

              // Basic validation for rankOrder structure
              let validatedRankOrder = [];
              if (Array.isArray(llmData.rankOrder) && llmData.rankOrder.length === 6) {
                // Ensure ranks are correctly parsed and sorted
                const parsedRanks = llmData.rankOrder.map(rankItem => {
                  const rankNum = parseInt(rankItem.rank?.replace('#', ''), 10);
                  return {
                    ...rankItem,
                    rankNum: isNaN(rankNum) ? 0 : rankNum // Guard against invalid rank format
                  };
                }).filter(item => item.rankNum > 0); // Filter out invalid ranks

                // Sort by rank number descending (for #6 to #1)
                parsedRanks.sort((a, b) => b.rankNum - a.rankNum);

                // Re-map to remove temporary rankNum and check for exactly 6 unique ranks
                const uniqueRanks = new Set();
                validatedRankOrder = parsedRanks.filter(item => {
                  if (item.rankNum >= 1 && item.rankNum <= 6 && !uniqueRanks.has(item.rankNum)) {
                    uniqueRanks.add(item.rankNum);
                    return true;
                  }
                  return false;
                }).map(({ rankNum, ...rest }) => rest); // Remove temporary rankNum

                // If after validation and unique check, we don't have exactly 6, consider it invalid for now.
                if (validatedRankOrder.length !== 6) {
                  agentOutput.error = "LLM did not return a valid 6-rank structure. Missing or duplicate ranks.";
                  validatedRankOrder = []; // Clear invalid structure
                }

              } else {
                agentOutput.error = "LLM did not return a valid 6-rank structure. Incorrect array length or format.";
              }

              agentOutput.result.rankOrder = validatedRankOrder;
              agentOutput.result.retentionPrediction = llmData.retentionPrediction || "Retention prediction unavailable.";

              agentOutput.metadata.provider = llmResponse.provider || "Unknown";
              agentOutput.metadata.model = llmResponse.model || "Unknown";
              agentOutput.metadata.latency = llmResponse.metadata?.latency || (Date.now() - agentStartTime);
              agentOutput.metadata.timestamp = llmResponse.metadata?.timestamp || new Date().toISOString();
              agentOutput.metadata.capabilities = llmResponse.metadata?.capabilities || [];

            } else {
              agentOutput.error = llmResponse.error || `LLM analysis failed for Ranking Agent with provider ${providerName || 'default'}.`;
              console.error(`Ranking Agent LLM Call Failed: ${agentOutput.error}`);
            }

          } catch (err) {
            agentOutput.error = `Ranking Agent execution error: ${err.message}`;
            console.error(`Ranking Agent Error:`, err);
          } finally {
            agentOutput.metadata.latency = Date.now() - agentStartTime;
          }

          return agentOutput;
        }

        // --- src/agents/seoAgent.js ---
        // Runs the SEO Agent to generate optimized titles, descriptions, keywords, and hashtags.

        async function runSeo({ contentDescription, platform, language = 'en', providerName, model, timeout }) {
          const agentStartTime = Date.now();
          let agentOutput = {
            agent: "SEOAgent",
            version: "1.0.0",
            capability: [
              "seo generation",
              "keyword optimization",
              "content discoverability"
            ],
            result: {
              title: "Optimized Content Title", // Default fallback content
              description: "Optimized content description for discoverability.", // Default fallback content
              keywords: [],
              hashtags: [],
              generated: false, // Indicates if content was AI generated or fallback
              source: "fallback" // Source of the content: llm/fallback
            },
            metadata: {
              provider: "N/A",
              model: "N/A",
              latency: 0,
              timestamp: new Date().toISOString()
            },
            error: null
          };

          try {
            const prompt = `Generate an SEO optimized title (under 60 chars), a meta description (under 160 chars), 5-10 relevant keywords, and 3-5 relevant hashtags for the following content idea: "${contentDescription}"
            Target platform: ${platform || 'general'}. Language: ${language}.
            Ensure titles are catchy and descriptions are informative. Keywords should be high-value.`;

            const llmResponse = await AIProvider.analyze(prompt, {
              providerName,
              model,
              timeout,
              outputSchema: {
                type: "object",
                properties: {
                  title: { type: "string", description: "SEO optimized title (max 60 characters)", maxLength: 60 },
                  description: { type: "string", description: "SEO optimized meta description (max 160 characters)", maxLength: 160 },
                  keywords: {
                    type: "array",
                    items: { type: "string" },
                    minItems: 5,
                    maxItems: 10,
                    description: "List of relevant SEO keywords"
                  },
                  hashtags: {
                    type: "array",
                    items: { type: "string", pattern: "^#.*" },
                    minItems: 3,
                    maxItems: 5,
                    description: "List of relevant hashtags"
                  }
                },
                required: ["title", "description", "keywords", "hashtags"]
              }
            });

            if (llmResponse.success && llmResponse.data) {
              const llmData = llmResponse.data;

              agentOutput.result.title = llmData.title ? llmData.title.substring(0, 60) : agentOutput.result.title;
              agentOutput.result.description = llmData.description ? llmData.description.substring(0, 160) : agentOutput.result.description;
              agentOutput.result.keywords = Array.isArray(llmData.keywords) ? llmData.keywords.slice(0, 10) : agentOutput.result.keywords;
              agentOutput.result.hashtags = Array.isArray(llmData.hashtags) ? llmData.hashtags.filter(tag => tag.startsWith('#')).slice(0, 5) : agentOutput.result.hashtags;

              agentOutput.result.generated = true;
              agentOutput.result.source = "llm";

              agentOutput.metadata.provider = llmResponse.provider || "Unknown";
              agentOutput.metadata.model = llmResponse.model || "Unknown";
              agentOutput.metadata.latency = llmResponse.metadata?.latency || (Date.now() - agentStartTime);
              agentOutput.metadata.timestamp = llmResponse.metadata?.timestamp || new Date().toISOString();
              agentOutput.metadata.capabilities = llmResponse.metadata?.capabilities || [];

            } else {
              agentOutput.error = llmResponse.error || `LLM analysis failed for SEO Agent with provider ${providerName || 'default'}. Using fallback content.`;
              console.error(`SEO Agent LLM Call Failed: ${agentOutput.error}`);
            }

          } catch (err) {
            agentOutput.error = `SEO Agent execution error: ${err.message}. Using fallback content.`;
            console.error(`SEO Agent Error:`, err);
          } finally {
            agentOutput.metadata.latency = Date.now() - agentStartTime;
          }

          return agentOutput;
        }

        // --- src/agents/competitorAgent.js ---
        // Runs the Competitor Analysis Agent to analyze competitor patterns.

        async function runCompetitorAnalysis({ topic, platform, providerName, model, timeout }) {
          const agentStartTime = Date.now();
          let agentOutput = {
            agent: "CompetitorAgent",
            version: "1.0.0",
            capability: [
              "competitor analysis",
              "pattern extraction",
              "winning format identification",
              "content gap analysis"
            ],
            result: {
              competitorPatterns: [],
              contentGaps: [],
              winningFormatsSummary: []
            },
            metadata: {
              provider: "N/A",
              model: "N/A",
              latency: 0,
              timestamp: new Date().toISOString()
            },
            error: null
          };

          try {
            const prompt = `Perform a competitor analysis for content related to the topic: "${topic}" on platform "${platform || 'general'}.
            Identify key competitor patterns, successful content formats, and potential content gaps or underserved niches.
            Provide analysis for at least 3 distinct competitor patterns.`;

            const llmResponse = await AIProvider.analyze(prompt, {
              providerName,
              model,
              timeout,
              outputSchema: {
                type: "object",
                properties: {
                  competitorPatterns: {
                    type: "array",
                    items: {
                      type: "object",
                      properties: {
                        name: { type: "string", description: "Name or type of competitor/pattern" },
                        strategy: { type: "string", description: "Their content or posting strategy" },
                        winningFormats: { type: "string", description: "Formats that perform well for them" },
                        keywords: { type: "array", items: { type: "string" }, description: "Keywords they frequently target" }
                      },
                      required: ["name", "strategy", "winningFormats"]
                    },
                    minItems: 3,
                    description: "Detailed analysis of competitor patterns"
                  },
                  contentGaps: {
                    type: "array",
                    items: { type: "string" },
                    description: "Identified content gaps or underserved niches"
                  },
                  winningFormatsSummary: {
                    type: "array",
                    items: { type: "string" },
                    description: "Summary of overall winning content formats"
                  }
                },
                required: ["competitorPatterns", "contentGaps", "winningFormatsSummary"]
              }
            });

            if (llmResponse.success && llmResponse.data) {
              const llmData = llmResponse.data;

              agentOutput.result.competitorPatterns = Array.isArray(llmData.competitorPatterns) ? llmData.competitorPatterns : [];
              agentOutput.result.contentGaps = Array.isArray(llmData.contentGaps) ? llmData.contentGaps : [];
              agentOutput.result.winningFormatsSummary = Array.isArray(llmData.winningFormatsSummary) ? llmData.winningFormatsSummary : [];

              agentOutput.metadata.provider = llmResponse.provider || "Unknown";
              agentOutput.metadata.model = llmResponse.model || "Unknown";
              agentOutput.metadata.latency = llmResponse.metadata?.latency || (Date.now() - agentStartTime);
              agentOutput.metadata.timestamp = llmResponse.metadata?.timestamp || new Date().toISOString();
              agentOutput.metadata.capabilities = llmResponse.metadata?.capabilities || [];

            } else {
              agentOutput.error = llmResponse.error || `LLM analysis failed for Competitor Agent with provider ${providerName || 'default'}.`;
              console.error(`Competitor Agent LLM Call Failed: ${agentOutput.error}`);
            }

          } catch (err) {
            agentOutput.error = `Competitor Agent execution error: ${err.message}`;
            console.error(`Competitor Agent Error:`, err);
          } finally {
            agentOutput.metadata.latency = Date.now() - agentStartTime;
          }

          return agentOutput;
        }

        // --- src/router/agentRouter.js ---
        // The central Agent Router for the Multi AI Agent System.

        const AgentRegistry = {
          discovery: {
            agentFunction: runDiscovery,
            version: "1.0.0",
            capability: ["viral discovery", "trend analysis", "keyword extraction"]
          },
          scoring: {
            agentFunction: runScoring,
            version: "1.0.0",
            capability: ["viral scoring", "content evaluation", "retention analysis"]
          },
          ranking: {
            agentFunction: runRanking,
            version: "1.0.0",
            capability: ["content ranking", "retention prediction", "narrative structuring", "6-rank viral framework", "retention optimization"]
          },
          seo: {
            agentFunction: runSeo,
            version: "1.0.0",
            capability: ["seo generation", "keyword optimization", "content discoverability"]
          },
          competitor: {
            agentFunction: runCompetitorAnalysis,
            version: "1.0.0",
            capability: ["competitor analysis", "pattern extraction", "winning format identification", "content gap analysis"]
          }
        };

        const AgentRouter = {
          async routeTask(task, agentType, options = {}) {
            const startTime = Date.now();
            const agentConfig = AgentRegistry[agentType.toLowerCase()];

            let agentResult = {
              agent: agentType,
              version: agentConfig?.version || "N/A",
              capability: agentConfig?.capability || [],
              task: task,
              result: null,
              error: null,
              metadata: {
                totalLatency: 0,
                success: false,
                timestamp: new Date().toISOString()
              }
            };

            if (!agentConfig || typeof agentConfig.agentFunction !== 'function') {
              agentResult.error = `Agent type "${agentType}" not found or not properly configured in AgentRegistry.`;
              console.error(agentResult.error);
              return agentResult;
            }

            try {
              const individualAgentOutput = await agentConfig.agentFunction({
                contentDescription: task,
                task,
                platform: options.platform,
                providerName: options.providerName,
                model: options.model,
                timeout: options.timeout
              });

              agentResult.result = individualAgentOutput.result;
              agentResult.error = individualAgentOutput.error;
              agentResult.metadata = {
                ...agentResult.metadata,
                ...individualAgentOutput.metadata,
                success: !individualAgentOutput.error
              };
              agentResult.agent = individualAgentOutput.agent;
              agentResult.version = individualAgentOutput.version;
              agentResult.capability = individualAgentOutput.capability;


            } catch (err) {
              console.error(`Error during ${agentType} agent execution:`, err.message);
              agentResult.error = err.message;
              agentResult.metadata.success = false;
            } finally {
              agentResult.metadata.totalLatency = Date.now() - startTime;
            }

            return agentResult;
          },

          listAgentTypes() {
            return Object.keys(AgentRegistry).map(key => ({
              type: key,
              version: AgentRegistry[key].version,
              capability: AgentRegistry[key].capability
            }));
          }
        };


        // --- src/App.jsx ---
        const { useState, useEffect } = React; // Destructure React for use in Babel-transformed script

        function App() {
          const [topic, setTopic] = useState('');
          const [platform, setPlatform] = useState('YouTube');
          const [loading, setLoading] = useState(false);
          const [error, setError] = useState(null);
          const [results, setResults] = useState(null);
          const [activeProvider, setActiveProvider] = useState(AIProvider.getCurrentProviderName());
          const [availableModels, setAvailableModels] = useState([]);
          const [selectedModel, setSelectedModel] = useState('');

          useEffect(() => {
            const fetchProviderConfig = async () => {
              const config = AIProvider.listProviders();
              const currentProviderName = AIProvider.getCurrentProviderName();
              const currentProvider = config[currentProviderName];

              if (currentProvider) {
                setActiveProvider(currentProviderName);
                setAvailableModels(currentProvider.models || []);
                setSelectedModel(currentProvider.models?.[0]?.id || '');
              } else {
                const firstProviderName = Object.keys(config)[0];
                if (firstProviderName) {
                  AIProvider.setProvider(firstProviderName);
                  setActiveProvider(firstProviderName);
                  setAvailableModels(config[firstProviderName].models || []);
                  setSelectedModel(config[firstProviderName].models?.[0]?.id || '');
                }
              }
            };
            fetchProviderConfig();
          }, []);

          const handleProviderChange = (e) => {
            const newProviderName = e.target.value;
            AIProvider.setProvider(newProviderName);
            const newProviderConfig = AIProvider.listProviders()[newProviderName];
            setActiveProvider(newProviderName);
            setAvailableModels(newProviderConfig?.models || []);
            setSelectedModel(newProviderConfig?.models?.[0]?.id || '');
          };

          const handleModelChange = (e) => {
            setSelectedModel(e.target.value);
          };

          const handleResearch = async () => {
            setLoading(true);
            setError(null);
            setResults(null);

            if (!topic.trim()) {
              setError("Please enter a topic to research.");
              setLoading(false);
              return;
            }

            try {
              const options = { platform, providerName: activeProvider, model: selectedModel, timeout: 30000 };
              const allAgentResults = {};

              const discoveryOutput = await AgentRouter.routeTask(topic, 'discovery', options);
              if (discoveryOutput.error) throw new Error(`Discovery Agent: ${discoveryOutput.error}`);
              allAgentResults.discovery = discoveryOutput;

              const scoringOutput = await AgentRouter.routeTask(topic, 'scoring', options);
              if (scoringOutput.error) throw new Error(`Scoring Agent: ${scoringOutput.error}`);
              allAgentResults.scoring = scoringOutput;

              const rankingOutput = await AgentRouter.routeTask(topic, 'ranking', options);
              if (rankingOutput.error) throw new Error(`Ranking Agent: ${rankingOutput.error}`);
              allAgentResults.ranking = rankingOutput;

              const seoOutput = await AgentRouter.routeTask(topic, 'seo', options);
              if (seoOutput.error) throw new Error(`SEO Agent: ${seoOutput.error}`);
              allAgentResults.seo = seoOutput;

              const competitorOutput = await AgentRouter.routeTask(topic, 'competitor', options);
              if (competitorOutput.error) throw new Error(`Competitor Agent: ${competitorOutput.error}`);
              allAgentResults.competitor = competitorOutput;

              setResults(allAgentResults);

            } catch (err) {
              console.error("Orchestration error:", err);
              setError(err.message || "An unknown error occurred during content research.");
            } finally {
              setLoading(false);
            }
          };

          return (
            <div className="min-h-screen bg-gray-100 p-4 font-sans mobile-ui">
              <div className="max-w-4xl mx-auto bg-white shadow-lg rounded-lg p-6">
                <h1 className="text-3xl font-bold text-gray-800 mb-6 text-center">AI Content Research OS</h1>

                <div className="mb-6 space-y-4">
                  <div>
                    <label htmlFor="topic" className="block text-gray-700 text-sm font-bold mb-2">
                      Content Topic / Idea:
                    </label>
                    <input
                      type="text"
                      id="topic"
                      value={topic}
                      onChange={(e) => setTopic(e.target.value)}
                      placeholder="e.g., 'How to grow a YouTube channel fast'"
                      className="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline"
                      disabled={loading}
                    />
                  </div>

                  <div className="flex flex-col sm:flex-row sm:space-x-4 space-y-4 sm:space-y-0">
                    <div className="flex-1">
                      <label htmlFor="platform" className="block text-gray-700 text-sm font-bold mb-2">
                        Target Platform:
                      </label>
                      <select
                        id="platform"
                        value={platform}
                        onChange={(e) => setPlatform(e.target.value)}
                        className="shadow border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline"
                        disabled={loading}
                      >
                        <option value="YouTube">YouTube</option>
                        <option value="TikTok">TikTok</option>
                        <option value="Instagram">Instagram</option>
                        <option value="Reddit">Reddit</option>
                        <option value="Facebook">Facebook</option>
                      </select>
                    </div>

                    <div className="flex-1">
                      <label htmlFor="provider" className="block text-gray-700 text-sm font-bold mb-2">
                        LLM Provider:
                      </label>
                      <select
                        id="provider"
                        value={activeProvider}
                        onChange={handleProviderChange}
                        className="shadow border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline"
                        disabled={loading || Object.keys(AIProvider.listProviders()).length === 0}
                      >
                        {Object.keys(AIProvider.listProviders()).map(key => (
                          <option key={key} value={key}>{AIProvider.listProviders()[key].name}</option>
                        ))}
                      </select>
                    </div>

                    <div className="flex-1">
                      <label htmlFor="model" className="block text-gray-700 text-sm font-bold mb-2">
                        LLM Model:
                      </label>
                      <select
                        id="model"
                        value={selectedModel}
                        onChange={handleModelChange}
                        className="shadow border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline"
                        disabled={loading || availableModels.length === 0}
                      >
                        {availableModels.map(model => (
                          <option key={model.id} value={model.id}>{model.name}</option>
                        ))}
                      </select>
                    </div>
                  </div>

                  <button
                    onClick={handleResearch}
                    className={`w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded focus:outline-none focus:shadow-outline ${loading ? 'opacity-50 cursor-not-allowed' : ''}`}
                    disabled={loading}
                  >
                    {loading ? 'Researching...' : 'Generate Content Research'}
                  </button>
                </div>

                {loading && (
                  <div className="text-center py-4">
                    <p className="text-blue-500">Running AI Agents...</p>
                    <div className="loader ease-linear rounded-full border-4 border-t-4 border-gray-200 h-12 w-12 mb-4 mx-auto"></div>
                  </div>
                )}
                {error && (
                  <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative mb-4" role="alert">
                    <strong className="font-bold">Error! </strong>
                    <span className="block sm:inline">{error}</span>
                  </div>
                )}

                {results && (
                  <div className="mt-8 space-y-8">
                    <h2 className="text-2xl font-bold text-gray-800 border-b pb-2 mb-4">Research Results</h2>

                    <AgentResultCard agentName="Discovery Agent" output={results.discovery}>
                      <h3 className="text-xl font-semibold mb-2 text-gray-700">Viral Opportunities:</h3>
                      <ul className="list-disc list-inside text-gray-600 mb-2">
                        {results.discovery.result?.videoCandidates?.map((item, i) => <li key={i}>{item}</li>)}
                      </ul>
                      <h3 className="text-xl font-semibold mb-2 text-gray-700">Trend Signals:</h3>
                      <ul className="list-disc list-inside text-gray-600 mb-2">
                        {results.discovery.result?.trendSignals?.map((item, i) => <li key={i}>{item}</li>)}
                      </ul>
                      <h3 className="text-xl font-semibold mb-2 text-gray-700">Keywords:</h3>
                      <ul className="list-disc list-inside text-gray-600">
                        {results.discovery.result?.keywords?.map((item, i) => <li key={i}>{item}</li>)}
                      </ul>
                    </AgentResultCard>

                    <AgentResultCard agentName="Scoring Agent" output={results.scoring}>
                      <h3 className="text-xl font-semibold mb-2 text-gray-700">Content Score: {results.scoring.result?.finalScore || 'N/A'} / 100</h3>
                      <p className="text-gray-600 mb-2">Reasoning: {results.scoring.result?.reasoning}</p>
                      <div className="grid grid-cols-2 gap-2 text-gray-600">
                        <p>Viral: {results.scoring.result?.viralScore || 'N/A'}</p>
                        <p>Emotion: {results.scoring.result?.emotionScore || 'N/A'}</p>
                        <p>Trend: {results.scoring.result?.trendScore || 'N/A'}</p>
                        <p>Hook: {results.scoring.result?.hookScore || 'N/A'}</p>
                        <p>Replay: {results.scoring.result?.replayScore || 'N/A'}</p>
                        <p>Rarity: {results.scoring.result?.rarityScore || 'N/A'}</p>
                        <p>Competition: {results.scoring.result?.competitionScore || 'N/A'}</p>
                      </div>
                    </AgentResultCard>

                    <AgentResultCard agentName="Ranking Agent (6-Rank Structure)" output={results.ranking}>
                      <h3 className="text-xl font-semibold mb-2 text-gray-700">Retention Prediction:</h3>
                      <p className="text-gray-600 mb-4">{results.ranking.result?.retentionPrediction}</p>
                      <h3 className="text-xl font-semibold mb-2 text-gray-700">6-Rank Structure:</h3>
                      <div className="space-y-3">
                        {results.ranking.result?.rankOrder?.map((rank, i) => (
                          <div key={i} className="bg-gray-50 p-3 rounded-md border border-gray-200">
                            <p className="font-medium text-gray-800">{rank.rank}: {rank.segment}</p>
                            <p className="text-sm text-gray-600">{rank.content}</p>
                          </div>
                        ))}
                      </div>
                    </AgentResultCard>

                    <AgentResultCard agentName="SEO Agent" output={results.seo}>
                      <h3 className="text-xl font-semibold mb-2 text-gray-700">Title:</h3>
                      <p className="text-gray-600 mb-2">{results.seo.result?.title}</p>
                      <h3 className="text-xl font-semibold mb-2 text-gray-700">Description:</h3>
                      <p className="text-gray-600 mb-2">{results.seo.result?.description}</p>
                      <h3 className="text-xl font-semibold mb-2 text-gray-700">Keywords:</h3>
                      <ul className="list-disc list-inside text-gray-600 mb-2">
                        {results.seo.result?.keywords?.map((item, i) => <li key={i}>{item}</li>)}
                      </ul>
                      <h3 className="text-xl font-semibold mb-2 text-gray-700">Hashtags:</h3>
                      <ul className="list-disc list-inside text-gray-600">
                        {results.seo.result?.hashtags?.map((item, i) => <li key={i}>{item}</li>)}
                      </ul>
                    </AgentResultCard>

                    <AgentResultCard agentName="Competitor Analysis Agent (Predator Mode)" output={results.competitor}>
                      <h3 className="text-xl font-semibold mb-2 text-gray-700">Competitor Patterns:</h3>
                      <div className="space-y-3 mb-4">
                        {results.competitor.result?.competitorPatterns?.map((pattern, i) => (
                          <div key={i} className="bg-gray-50 p-3 rounded-md border border-gray-200">
                            <p className="font-medium text-gray-800">Competitor: {pattern.name}</p>
                            <p className="text-sm text-gray-600">Strategy: {pattern.strategy}</p>
                            <p className="text-sm text-gray-600">Winning Formats: {pattern.winningFormats}</p>
                            <p className="text-sm text-gray-600">Keywords: {pattern.keywords?.join(', ')}</p>
                          </div>
                        ))}
                      </div>
                      <h3 className="text-xl font-semibold mb-2 text-gray-700">Content Gaps:</h3>
                      <ul className="list-disc list-inside text-gray-600 mb-2">
                        {results.competitor.result?.contentGaps?.map((item, i) => <li key={i}>{item}</li>)}
                      </ul>
                      <h3 className="text-xl font-semibold mb-2 text-gray-700">Winning Formats Summary:</h3>
                      <ul className="list-disc list-inside text-gray-600">
                        {results.competitor.result?.winningFormatsSummary?.map((item, i) => <li key={i}>{item}</li>)}
                      </ul>
                    </AgentResultCard>
                  </div>
                )}
              </div>
            </div>
          );
        }

        const AgentResultCard = ({ agentName, output, children }) => {
          return (
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-5">
              <h2 className="text-2xl font-bold text-gray-800 mb-3">{agentName}</h2>
              {output.error ? (
                <div className="bg-red-50 border border-red-300 text-red-600 px-4 py-3 rounded relative">
                  <strong className="font-bold">Agent Error: </strong>
                  <span className="block sm:inline">{output.error}</span>
                </div>
              ) : (
                <>
                  {children}
                  <div className="mt-4 pt-4 border-t border-gray-200 text-sm text-gray-500">
                    <p>Version: {output.version} | Capabilities: {output.capability.join(', ')}</p>
                    <p>LLM Provider: {output.metadata?.provider} | Model: {output.metadata?.model}</p>
                    <p>Latency: {output.metadata?.latency}ms | Timestamp: {new Date(output.metadata?.timestamp).toLocaleString()}</p>
                  </div>
                </>
              )}
            </div>
          );
        };

        ReactDOM.render(<App />, document.getElementById('root'));
    </script>
</body>
</html>
