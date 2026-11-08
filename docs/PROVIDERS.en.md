# AI providers and selection

[Deutsch](PROVIDERS.md) · English

GhostWriter is independent of any provider. Each book project assigns an AI provider to each task. The machine-readable list is in [`providers.yml`](../providers.yml); the book's selection is under `ai_providers` in [`ghostwriter.yml`](../ghostwriter.yml).

> This is a translation of the list dated 31 October 2026. Features, models, prices and privacy terms change. The list helps with selection and is not a recommendation; check the provider before use.

## Start with what you have

You do not need new subscriptions for GhostWriter. The setup conversation asks which AI services you already use; only those are recorded in `ai_providers.available` and assigned tasks. If you do not name a service, the current chat handles everything.

You can add services later through **AI services** in the project overview (`D` in the text view). Select the services you have and assign tasks. Each service has a **Guide** link explaining [how to use it](AI-SERVICES.en.md), a **Website** link, and settings for access method, model, GitHub connection, plan, monthly cost and notes. For API access, record only the GitHub secret's name. See [connector setup](CONNECTOR-SETUP.en.md) for chat connections.

The configuration is stored in `ai_providers.services`. Validation reports tasks assigned to a service outside `available`, and settings for services you have not selected.

```yaml
ai_providers:
  available: [anthropic, perplexity]
  services:
    anthropic: { access: app, model: "", github_connected: true, plan: "Max", monthly_cost: 90 }
    perplexity: { access: app, model: "sonar-pro", github_connected: false, plan: "Pro", note: "research only" }
  default: { provider: "anthropic", model: "" }
  research: { provider: "perplexity", model: "" }
```

## Roles

| Role | Task | What matters |
|---|---|---|
| `research` | Research for sections | Web research; real, accessible sources |
| `brainstorming` | Ideas, arguments, examples | Creativity and context length |
| `writing` | Manuscript drafting | German-language quality, adherence to style, long texts |
| `revision` | Revision | Consistent style and precise corrections |
| `fact_check` | A report checking claims | Preferably a provider independent of the writing provider; web research |
| `queue_processing` | Processing GitHub issues | Whether the agent can work with GitHub technically |

Unassigned roles inherit `default`. The special value `chat` means the assistant in the current conversation.

## Example configuration

```yaml
ai_providers:
  default:       { provider: "chat", model: "" }
  research:      { provider: "perplexity", model: "", search_tools: ["semantic_scholar"] }
  brainstorming: { provider: "chat", model: "" }
  writing:       { provider: "anthropic", model: "" }
  revision:      { provider: "anthropic", model: "" }
  fact_check:    { provider: "google", model: "" }
  queue_processing: { agent: "github_copilot_agent", model: "" }
```

## Language-model providers

| ID | Provider | Based in | Access | Web search | Suitable roles |
|---|---|---|---|---|---|
| `openai` | OpenAI (ChatGPT / API) | US | App, API | Built in | All roles |
| `anthropic` | Anthropic (Claude / API) | US | App, API | Built in | All roles |
| `google` | Google (Gemini / API) | US | App, API | Built in | All roles |
| `mistral` | Mistral AI (Le Chat / API) | FR | App, API | Via tool | Research through fact-checking; European provider |
| `xai` | xAI (Grok / API) | US | App, API | Built in | Research through fact-checking |
| `perplexity` | Perplexity (App / Sonar API) | US | App, API | Built in | Research, fact-checking |
| `microsoft_copilot` | Microsoft Copilot | US | App | Built in | Research, brainstorming, writing, revision |
| `cohere` | Cohere (Command / API) | CA | API | Via tool | Research using your own documents, revision, fact-checking |
| `deepseek` | DeepSeek | CN | App, API | Via tool | Brainstorming, writing, revision; check privacy |
| `qwen` | Alibaba Qwen | CN | App, API | Via tool | Brainstorming, writing, revision |
| `moonshot` | Moonshot AI (Kimi) | CN | App, API | Via tool | Brainstorming, writing, revision |
| `meta_llama` | Meta Llama (open models) | US | Platforms or local | None | Brainstorming, writing, revision |

## Platforms, aggregators and local models

| ID | Name | Note |
|---|---|---|
| `openrouter` | OpenRouter | One key for many models; specify the model in `model` |
| `aws_bedrock` | Amazon Bedrock | Multiple providers; data center region can be selected |
| `azure_ai_foundry` | Microsoft Azure AI Foundry | Multiple providers; data center region can be selected |
| `google_vertex` | Google Cloud Vertex AI | Gemini and other models; data center region can be selected |
| `local_ollama` | Ollama | Local, offline, no recurring cost or web search |
| `local_lmstudio` | LM Studio | Local, offline, no recurring cost or web search |

## Additional research sources (`search_tools`)

These provide search results and sources rather than writing text. They supplement the research provider.

| ID | Name | Strength |
|---|---|---|
| `brave_search` | Brave Search API | Own index, independent of Google |
| `tavily` | Tavily | Search API built for AI agents |
| `exa` | Exa | Semantic search and similar pages |
| `parallel` | Parallel | Excerpts prepared for LLMs |
| `perplexity_sonar` | Perplexity Sonar API | Cited answers with sources |
| `serpapi` | SerpAPI | Conventional search engines, including Google Scholar |
| `semantic_scholar` | Semantic Scholar API | Scientific literature, free |
| `openalex` | OpenAlex | Open publication catalog, free |

## Queue agents (`queue_agents`)

For the queue, the agent's ability to work with the repository matters: it reads an issue, edits files and creates a pull request. Book approvals remain with the user in the chat; see [`workflow.yml`](../workflow.yml).

| ID | Agent | Provider | Note |
|---|---|---|---|
| `github_copilot_agent` | GitHub Copilot Coding Agent | Microsoft/GitHub | Assign an issue in GitHub to obtain a pull request |
| `openai_codex` | OpenAI Codex | OpenAI | Can also be assigned as a GitHub partner agent, depending on Copilot plan |
| `claude_code` | Claude Code | Anthropic | Can also be assigned as a GitHub partner agent, depending on Copilot plan |
| `google_jules` | Jules | Google | Asynchronous agent for GitHub repositories |
| `gemini_cli` | Gemini CLI | Google | Usable in GitHub Actions, for example |
| `manual` | Manual in chat | — | Default; no automatic processing |

## Rules

- Global AI rules (`strict`, `required`, `explicit`, etc.) apply to every provider. Switching providers never relaxes them.
- Every research, brainstorming or fact-checking run and each cost entry records `provider` and `model`.
- If the selected provider cannot be called directly, the assistant prepares an assignment for you to run there. It must not silently substitute another provider.
- A provider without web research may perform `research` only if every claim is explicitly marked as unverified.

## Maintaining the list

Add providers to `providers.yml` with a unique `id` and the appropriate fields, and update the corresponding documentation tables. Update `checked_at` when checking a provider. Keep the German and English versions in sync.

---

<p align="right"><sub>Developed with support from Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a><br>Developed with support from Codex (OpenAI)</sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="../assets/logo-dark.svg"><img src="../assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
