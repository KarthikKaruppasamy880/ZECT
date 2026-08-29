/**
 * Mentrix wake-phrase matching (shared by Electron main + unit tests).
 */

function matchesWakePhrase(transcript, wakePhrase = "Hey Mentrix") {
  const t = (transcript || "").toLowerCase().trim();
  const wp = (wakePhrase || "Hey Mentrix").toLowerCase();
  // Common STT mishears for Mentrix
  const fuzzy =
    /\b(mentrix|matrix|mentrics|mentricks|mentrisk)\b/.test(t) ||
    t.includes("hey mentrix") ||
    t.includes("hey matrix") ||
    t.includes("wake mentrix") ||
    t.includes("mentrix engage");
  return (
    fuzzy ||
    t.includes(wp) ||
    t === "mentrix" ||
    t.startsWith("mentrix ")
  );
}

module.exports = { matchesWakePhrase };
