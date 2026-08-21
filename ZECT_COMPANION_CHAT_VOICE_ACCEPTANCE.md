# Companion Chat / Voice acceptance (PR0)

## Operator-visible

- Chat tab always shows **Good to see you** (`mentrix-greeting`) and the transcript (`mentrix-companion-chat`), including Display mode.
- Live `perf:` log is behind **Events** (`mentrix-events-toggle`); default closed so logs do not cover replies.
- Speak replies checked: clone TTS when Voice is off; when Connect Voice is on, Realtime owns audio; if no chunk within 2.5s, **silent-fallback** clone TTS once (`mentrix-tts-playback`).
- Speakers picker is independent of the Jabra **Mic** picker.

## Tests

- Vitest: `companionChatVoice.test.ts`, `MentrixCompanion.layout.test.tsx`
- Headed: `e2e/mentrix-companion.spec.ts` greeting + events drawer
