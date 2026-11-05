# Connecting GhostWriter to GitHub

This is a translation of the setup procedure documented on 31 October 2026. **The proposed GitHub App authentication and ChatGPT write path were not fully tested in GhostWriter.** App menus, supported plans, OAuth requirements and permissions can change. Check the provider's current documentation before granting access. Report GhostWriter-specific results in [issue #22](https://github.com/ploeffler/GhostWriter/issues/22).

## Overview

GhostWriter keeps the book in a GitHub repository. A chat needs suitable access to save changes. Depending on the chat and connection, a built-in GitHub integration may be read-only. The procedure below describes a custom connection to GitHub's MCP server, `https://api.githubcopilot.com/mcp/`, using a GitHub App. Set up only the chat application you intend to use.

You need a GitHub account, an existing book repository and a chat account that supports the relevant custom connector. You will need the GitHub App's client ID and client secret. The **client secret is confidential**: never put it in a chat, email, issue, repository file or commit.

## 1. Create and install a GitHub App

1. In GitHub, open your profile menu → **Settings → Developer settings → GitHub Apps → New GitHub App**.
2. Give the app a unique name and use your book repository URL as its homepage. For Claude, the historical guide specifies `https://claude.ai/api/mcp/auth_callback` as a callback URL. Add the actual callback shown by the chat application when required.
3. In the historical setup, expiring user authorization tokens remains enabled; installation-time OAuth, device flow and the webhook are disabled.
4. Under **Repository permissions**, set **Contents** and **Pull requests** to **Read and write** and **Metadata** to **Read-only**. Leave other permissions at no access. Limit installation to your account.
5. Create the app. Copy its client ID, then generate a client secret. GitHub displays the secret only once.
6. In **Install App**, install it on **Only select repositories**, choosing only the intended book repository. Review the requested access before confirming.

These permissions allow the app to change files in the selected repository. Select no additional repositories unless you intend to grant access to them.

## 2. Configure a custom connector in Claude

The historical procedure uses **Customize → Connectors → Add custom connector**, with the MCP server URL above. Under advanced OAuth settings, enter the app's client ID and secret. Add and connect the connector, then inspect GitHub's authorization screen and authorize only the intended access. Organization plans may require an administrator to configure connectors.

The original guide marked GitHub App authentication through this MCP server as **untested**. If it fails, inspect the callback URL and provider documentation; do not assume a successful connection grants the tools needed to write.

## 3. Use the connection

In a new chat, enable the connector and send the book repository link. Check that the assistant can read the correct repository and identify which write tools are available. Review any write-approval prompts. GhostWriter's normal workflow collects changes on a working branch and applies them to the book after the required confirmation, unless immediate application has been explicitly enabled.

## 4. Optional ChatGPT setup

The historical guide describes enabling developer mode under **Settings → Apps → Advanced settings**, creating an app with OAuth and the MCP server URL, and registering the callback URL displayed by ChatGPT in the GitHub App. It explicitly marked plan availability and write support as **untested or uncertain**. Current menus and availability may differ. Verify the actual connection and available actions in the session; do not assume that a successful read test proves write or merge access.

## Troubleshooting and security

- **Dynamic client registration or authorization fails:** Check the configured OAuth client and current connector requirements.
- **Redirect URI mismatch:** The callback registered in GitHub must match the one supplied by the chat application.
- **Reading works but writing fails:** Check installation on the intended repository, permissions and whether changed permissions must be accepted again. Also check which tools the chat session actually exposes.
- **Alternative OAuth App:** The historical guide suggests this as a fallback but warns that an OAuth App can receive broader repository access than a GitHub App restricted to selected repositories. Review the actual requested access before authorizing it.
- **Secret exposed:** Revoke or delete it at GitHub, create a replacement and update the connection securely.
- **Disconnect:** Remove the connector in the chat application and revoke its authorization in GitHub. To stop using the GitHub App entirely, uninstall and delete it in GitHub settings.

For the original detailed, dated procedure and its source links, see [CONNECTOR-SETUP.md](CONNECTOR-SETUP.md).

---

<p align="right"><sub>Entwickelt mit Unterstützung von Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a></sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="../assets/logo-dark.svg"><img src="../assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
