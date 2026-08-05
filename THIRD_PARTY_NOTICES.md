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
