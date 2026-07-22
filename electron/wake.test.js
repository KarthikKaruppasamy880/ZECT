/** Node assert tests for Mentrix wake phrases — run: node electron/wake.test.js */
const assert = require("assert");
const { matchesWakePhrase } = require("./wake");

assert.strictEqual(matchesWakePhrase("Hey Mentrix"), true);
assert.strictEqual(matchesWakePhrase("please hey mentrix open"), true);
assert.strictEqual(matchesWakePhrase("Mentrix engage"), true);
assert.strictEqual(matchesWakePhrase("mentrix"), true);
assert.strictEqual(matchesWakePhrase("hello world"), false);
assert.strictEqual(matchesWakePhrase(""), false);
console.log("wake.test.js OK");
