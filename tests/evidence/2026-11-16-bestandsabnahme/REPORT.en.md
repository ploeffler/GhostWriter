# Baseline acceptance progress towards v1.0

16 November 2026. [Deutsch](BERICHT.md).
Base: `007f529b9b38543b019e9859f195aaf5cb96cff2`, program version 0.6.1.
A version number does not establish complete acceptance; the remaining
intermediate release sequence is still a proposal.

## Implemented and verified locally

A new fictitious book lifecycle covers creation, structure, drafting, revision,
completion, post-completion text changes, reopening, renewed writing permission,
renewed completion, local merge and proof/edition DOCX/EPUB export. The library
main branch, another book and a local edition tag remain intact. Confirmations
are simulated by the test driver; this is not real user/client acceptance.

Open WebUI and both cleanup Action paths now use GitHub GraphQL `updateRefs`
with the expected `beforeOid`. Version-branch deletion also atomically verifies
the preservation tag. Concurrent commits or changed tags prevent deletion.
GraphQL errors and uncertain responses are not success. There is no unconditional
deletion fallback or automatic retry. Preview mode sends no deletion mutation;
unconfirmed deletions are counted separately.

The historical test plan now keeps the library view for one book and refers to
the manifest version. An initially suspected version discrepancy was withdrawn:
the checked main tree already declares 0.6.1.

## B04: confirmed gap and account decision

The local [`b04_probe.py`](b04_probe.py) diagnostic changes ledger `by` names in a
fictitious completed book without authenticating a person. Validation/assembly
still accept unchanged content; a later manuscript change is detected by both.
With simulated HTTP transport, the current Open WebUI `commit_files` also accepts
a request without requester identity on either work or book branches.
[`b04-befund.json`](b04-befund.json) records these observations. No real GitHub
access or bypass of configured repository permissions was tested. The diagnostic
does not define the undesired behaviour as a regression requirement.

The user confirmed **personal GitHub accounts for collaboration**. Under D03,
content approval belongs to the owner or explicitly designated approvers. Shared
privileged tokens, chat/profile names and a free-form `by` field do not prove
individual authority.

Identity binding is **not yet implemented or accepted**. Next: bind writes to
personal credentials without a shared privileged fallback; verify the actual
GitHub identity; establish a protected ownership/delegation source; cover all
accepted-book/publication paths, including external Git tools and manual Actions.
Self-authored PRs, organizations and local limits require separate verification.
No new account-management service has been commissioned.

## Evidence and remaining limits

| Check | Result |
|---|---|
| Full suite with B03 fix and A02 tests | 556 tests, no errors, 16 skipped |
| Focused B03 run | 56 tests passed |
| B04 documentation/start/approval-button tests | 27 tests passed, none skipped |
| Documentation check | Passed, without external UI verification |
| Website, offline bundle and Wiki | Local builds passed; Wiki 43 pages, version 0.6.1 |
| Cleanup Action | Actual shell steps against local bare remotes; gh substitute models the documented atomic condition with real Git transactions |

These runs overlap; do not add the counts. The 16 skipped cases remain open,
including missing PDF/typesetting and practical client/role/visual acceptance.
Real GitHub/token acceptance of conditional deletion is still outstanding.
No real remote branch was deleted during verification. The documentation updates
do not change the verified product code.

The combined upload package is checked again locally; final results are recorded
in the PR description. This package is not a product release, deployment, book
update or full A01/A02 acceptance. Personal handovers, raw logs, patch archives
and generated test books are excluded.

After installing the project's test dependencies and optional Open WebUI
libraries, reproduce the diagnostic with:

```sh
python3 tests/evidence/2026-11-16-bestandsabnahme/b04_probe.py \
  --source . --output /tmp/b04-befund.json
```

Sources: [GitHub atomic ref updates](https://docs.github.com/en/graphql/reference/git#updaterefs),
[Open WebUI user context](https://docs.openwebui.com/features/extensibility/plugin/development/reserved-args/),
[GitHub code owners](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners).

---

Developed with support from Claude (Anthropic)
Developed with support from Codex (OpenAI)
