# Using AI services with GhostWriter

Choose the services you already use and assign tasks in **AI services** (robot icon in the project overview; `D` in the text view). You do not need a new subscription to start. See [providers and roles](PROVIDERS.en.md) for the dated service catalog.

This guide reflects the German guide dated 1 November 2026. Provider menus and capabilities can change; check the provider's current instructions before setting up a service.

## Choose a route

| Service | Route | Work involved |
|---|---|---|
| The chat you use for GhostWriter | [Current chat](#current-chat) | None |
| Another chat app or website | [Copy the task](#another-chat-service-copy-the-task) | Copy and paste for each task |
| A model running on your computer | [Local models](#local-models) | Copy and paste; no web research |
| An API-only service | [API-only services](#api-only-services) | Technical setup; a GitHub secret |
| Research source | [Research sources](#research-sources) | Depends on the source |
| Queue agent | [Queue agents](#queue-agents) | Setup in GitHub |

## Current chat

If a task uses **Current chat**, or inherits a default set to the current chat, the assistant performs it in the conversation. Saving the result requires GitHub write access; see [connector setup](CONNECTOR-SETUP.en.md).

## Another chat service: copy the task

For example, select a second service for research in **AI services**. When you start research for a section, GhostWriter prepares an assignment containing the subject, rules and expected response format.

1. Start the task in the GhostWriter chat, for example **Research · Now** for a section.
2. Copy the complete assignment and paste it into a new chat with the selected service. Enable web search there for research and fact-checking if available.
3. Copy the whole response back into the GhostWriter chat, identifying the service and model if known.
4. GhostWriter checks the format and sources, summarizes the result and saves it through the normal workflow.

Research becomes a research run; brainstorming becomes a brainstorming run. Writing and revision produce a draft for one section that you review before saving. Fact-checking produces a report and does not automatically change the manuscript. Writing approval is required before drafting.

Use one assignment per section. A selected service must not be silently replaced by the current chat. Assignments can contain book material: review the other service's data handling before sharing it. Subscription chat use is not recorded as an individual GhostWriter API cost; background API calls are tracked separately when supported.

## Local models

Tools such as Ollama and LM Studio run on your computer. Copy the assignment into the local tool and return its response as above. They can help with brainstorming, writing and revision, but a local model without web access cannot verify online sources; unverified research claims must be marked accordingly.

## API-only services

Some providers offer APIs or model platforms rather than a chat. The current chat cannot directly call every such service. Never paste an API key into a chat. If the provider offers a playground, you may copy an assignment there; direct integration depends on the supported execution path. Store keys as GitHub secrets where an authorized GitHub Action needs them.

## API keys as GitHub secrets

Ordinary work in a subscribed chat does not itself require an API key. A background API action, agent or search API may need one. **Do not put a key in a chat, form, file or commit.** Store it as an encrypted repository secret; GhostWriter records only the secret's name.

1. In **AI services**, open the service settings, choose API-key access and note the proposed secret name.
2. Create a key with the provider and, where possible, set a spending limit.
3. In GitHub, open the repository's **Settings → Secrets and variables → Actions → New repository secret**. Enter the exact name and the key, then add the secret. Repository administration rights are required.
4. Save the service settings. The overview update can check secret names and report whether the expected name exists; it does not read secret values. If needed, run the overview update workflow again.

If a key was accidentally pasted into a chat, revoke it with the provider and create a new one. Some platforms also require a region or endpoint; record non-secret settings without including credentials. Provider-specific authentication and subscription options can change, so verify them with the provider.

## Research sources

Literature catalogs such as Semantic Scholar and OpenAlex can be named in a research assignment for a web-enabled service to search. Search APIs requiring keys need a supported integration; they can be configured for later use. Sources supplement the research service rather than writing the book themselves.

## Web research through the API (#462)

If a service with an API key is assigned to **research**, the workflow “Recherche” (`.github/workflows/research.yml`) researches on the web with that service's built-in search. Currently supported: **Anthropic**, **OpenAI** and **Google Gemini**. Further providers, and search APIs for services without their own web search, follow in part 2 of #462.

- **Which service:** the one assigned to research; otherwise the first selected service with API-key access that can research; if the book has no settings, a library's default-branch settings apply.
- **Key:** the secret named in the service settings (e.g. `GEMINI_API_KEY`). The workflow reads only that secret; only names ending in `_API_KEY` are accepted.
- **Start:** in the [Claude web app](https://github.com/ploeffler/GhostWriter/blob/main/apps/claude/README.md) via research → **With internet via …**, in the chat in the section view via **Research → Queue · with internet via …** or by asking for web research, or under *Actions → Recherche → Run workflow* on the book branch with the section ID.
- **Background queue (#476):** every start adds a job, so you can queue several research tasks in a row, also for different sections, and look at the results later. One run per book works through the jobs in book order and saves each result immediately; one failure does not stop the rest. Leftovers are picked up by the daily “GhostWriter aktualisieren” run.
- **Viewing and ordering the queue (#478):** “View queue” shows waiting, waiting-for-confirmation, failed and finished jobs. You can **move up** a waiting job (it runs before all others) or **cancel** it; a job that is already running cannot be stopped. The order follows fixed rules and the AI never reorders it: priority, then dependency (a job can wait for another), then book order, then time. **Retry (#554):** A failed job does not run again by itself. If the provider reports that the model is no longer available, the error line says what to do (change the model in the “AI services” form or update GhostWriter; GhostWriter never switches to another model on its own). Then “Retry”: the assistant removes the error and timestamp from the same job file (`python3 scripts/jobs.py . retry --request <path>`), no second job is created; question, provider and model of the job stay.
- **Prior knowledge (#478):** every job receives the research already done for the same section (results, contradictions, open questions, without the source list) and, shortened, for the other sections of the chapter, about 6000 characters at most, newest first. The provider is told not to repeat what is known, to name contradictions explicitly and to take up open questions. Jobs queued later therefore build on earlier ones, even when they run one after another in the same queue.
- **Result:** a research run with sources and a cost entry in the change set. The source list comes only from the web-search evidence (title, link, retrieval date), never from the model's text. Gemini returns temporary redirect links titled with the domain; the workflow resolves them to the real address and page title (if that fails, the redirect link stays). Nothing is applied without your confirmation.
- **Costs:** tokens and search requests are recorded for every run and count towards the AI budget. For an estimated amount, enter prices in the service settings: per million input and output tokens and per 1000 searches, in the project currency. Without prices the amount is “unavailable”. With less than 10 % of the budget left, a job waits for your confirmation (“Start anyway”); the budget is checked before every job.

## Colorizing images with your own Gemini access

With Google Gemini set up and the secret `GEMINI_API_KEY`, the workflow “Bild colorieren” colorizes black-and-white photos and keeps only the color ([colorizing photos](IMAGES-AND-REFERENCES.en.md#colorizing-photos-452)). To use another image model, enter it as the service's **model** (a name containing `image`, e.g. `gemini-2.5-flash-image`). Other image services with their own secret are not yet supported by the workflow.

## Queue agents

The task queue uses GitHub issues. An agent may work on an issue and propose a pull request; the default is manual processing in chat. Configure an agent in **AI services** and follow its provider's GitHub setup. An agent running in Actions may need an API-key secret. Approvals remain with you: completing an issue or an agent's work is not a book approval.

## Add or remove a service later

Open **AI services** from the project overview, expand the list of additional services and select the one you use. Configure access method, optional model, GitHub connection, plan, monthly subscription cost and non-secret notes. Assign its tasks and save. The change follows the normal apply-changes workflow. To stop using a service, deselect it and save; its tasks revert to the default.

---

<p align="right"><sub>Developed with support from Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a><br>Developed with support from Codex (OpenAI)</sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="../assets/logo-dark.svg"><img src="../assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
