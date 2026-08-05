# Third-party notices

ZECT uses replaceable third-party components behind ZECT-owned adapter
interfaces. Product UI, routes, and public APIs do not brand these
components. Attribution required by applicable licenses is preserved here.

## Remote coding Agent Server (optional Phase 2 provider)

When `ZECT_CODING_ENGINE=remote`, ZECT's backend may call an independently
running Agent Server over HTTP/WebSocket (credentials never reach the
browser). Compatible upstream packaging is typically distributed under the
MIT License (OpenHands Software Agent SDK / Agent Server).

Pin a released version in deployment docs; do not install from an unpinned
`main` branch in production.

Copyright (c) OpenHands contributors and/or respective authors.
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

Source references (implementation detail, not product branding):
- https://github.com/OpenHands/software-agent-sdk
- https://github.com/OpenHands/OpenHands

## Monaco Editor (Phase 3 Developer Workspace)

The Developer Workspace embeds the Monaco editor via `monaco-editor` and
`@monaco-editor/react` for in-browser code editing. This is an editor
component, not a product brand in ZECT UI.

Monaco Editor is licensed under the MIT License.
Copyright (c) Microsoft Corporation.

https://github.com/microsoft/monaco-editor

## Browser automation engine (Phase 7)

ZECT Mentrix may drive a local Chromium instance through an internal
browser-automation adapter for DOM fill/click/snapshot. The product UI
exposes this as Mentrix Browser Automation — not under a third-party brand.

When Playwright (Apache-2.0) is installed as the implementation library,
its copyright and license terms apply to that dependency only.

https://github.com/microsoft/playwright

## Voice / realtime media (Phase 6)

Mentrix Realtime voice may use cloud realtime speech APIs or local TTS
clone engines configured via environment and Secrets Manager. Adapter
boundaries keep provider names out of ZECT routes and UI labels.

## Detection / endpoint / forensics adapters (Phase 9)

ZECT Security Incidents use a ZECT-owned **Detection Provider** interface.
Optional external SIEM/EDR/forensic collectors may be wired behind that
interface; product UI, routes, and models never brand those vendors.
Attribution for any installed connector libraries belongs here when added.

Current built-in provider: audit-trail anomaly scan (ZECT-native).


The optional desktop shell uses Electron (MIT) for windowing. App identity
is `com.zinnia.zect`. See `docs/RELEASE.md` for packaging gates.
