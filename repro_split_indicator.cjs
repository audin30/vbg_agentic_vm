const IP_REGEX = /\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b/g;

function parseIndicators(text) {
  const indicators = [];
  const ipMatches = text.match(IP_REGEX);
  if (ipMatches) {
    ipMatches.forEach((ip) => indicators.push({ type: 'ip', value: ip }));
  }
  return indicators;
}

const chunk1 = "The attacker used IP 192.16";
const chunk2 = "8.1.1 for the attack.";

console.log("Chunk 1 indicators:", parseIndicators(chunk1));
console.log("Chunk 2 indicators:", parseIndicators(chunk2));

const accumulated = chunk1 + chunk2;
console.log("Accumulated indicators:", parseIndicators(accumulated));

if (parseIndicators(chunk1).length === 0 && parseIndicators(chunk2).length === 0 && parseIndicators(accumulated).length > 0) {
    console.log("REPRODUCTION SUCCESSFUL: Indicator split across chunks is only detected in accumulated text.");
} else {
    console.log("REPRODUCTION FAILED.");
}
