/**
 * Mentrix wake-phrase matching (shared by Electron main + unit tests).
 */

function matchesWakePhrase(transcript, wakePhrase = "Hey Mentrix") {
  const t = (transcript || "").toLowerCase().trim();
  const wp = (wakePhrase || "Hey Mentrix").toLowerCase();
  return (
    t.includes(wp) ||
    t.includes("hey mentrix") ||
    t.includes("mentrix engage") ||
    t === "mentrix" ||
    t.startsWith("mentrix ")
  );
}

module.exports = { matchesWakePhrase };
