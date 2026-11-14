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

Research becomes a research run; brainstorming becomes a brainstorming run. Writing and revision produce a draft for one section that you review before saving. Fact-checking produces a report and does not automatically change the manuscript. Writing approval is required before storing text as manuscript; an external draft may be shown in chat for review.

Use one clearly scoped assignment, normally for one section. For chapter work, follow the external dialogue workflow and existing chapter prerequisites; do not print entire chapters in chat. A selected service must not be silently replaced by the current chat. Assignments can contain book material: review the other service's data handling before sharing it. Subscription chat use is not recorded as an individual GhostWriter API cost; background API calls are tracked separately when supported.

For multiple dialogue turns rather than a single response, use the [external AI dialogue workflow](EXTERNAL-AI-DIALOG.en.md): prepare an assignment, return the conversation and receive an analysis with a recommendation.

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

## Queue agents

The task queue uses GitHub issues. An agent may work on an issue and propose a pull request; the default is manual processing in chat. Configure an agent in **AI services** and follow its provider's GitHub setup. An agent running in Actions may need an API-key secret. Approvals remain with you: completing an issue or an agent's work is not a book approval.

## Add or remove a service later

Open **AI services** from the project overview, expand the list of additional services and select the one you use. Configure access method, optional model, GitHub connection, plan, monthly subscription cost and non-secret notes. Assign its tasks and save. The change follows the normal apply-changes workflow. To stop using a service, deselect it and save; its tasks revert to the default.

---

<p align="right"><sub>Developed with support from Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a><br>Developed with support from Codex (OpenAI)</sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="../assets/logo-dark.svg"><img src="../assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
