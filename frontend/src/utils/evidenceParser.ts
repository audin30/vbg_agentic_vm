export interface DiscoveredIndicator {
  type: 'ip' | 'domain' | 'hash';
  value: string;
}

const IP_REGEX = /\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b/g;
const DOMAIN_REGEX = /\b(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}\b/gi;
const HASH_REGEX = /\b[A-Fa-f0-9]{64}\b/g;

export const parseIndicators = (text: string): DiscoveredIndicator[] => {
  const indicators: DiscoveredIndicator[] = [];

  // Use a local copy of regex for execution to avoid state issues with global flag if reused
  const ipMatches = text.match(IP_REGEX);
  if (ipMatches) {
    ipMatches.forEach((ip) => indicators.push({ type: 'ip', value: ip }));
  }

  const domainMatches = text.match(DOMAIN_REGEX);
  if (domainMatches) {
    domainMatches.forEach((domain) => {
        // Simple filter to avoid some false positives
        if (!domain.includes('..') && domain.split('.').every(part => part.length > 0)) {
            // Avoid adding things that look like IPs as domains
            if (!/^[0-9.]+$/.test(domain)) {
                indicators.push({ type: 'domain', value: domain.toLowerCase() });
            }
        }
    });
  }

  const hashMatches = text.match(HASH_REGEX);
  if (hashMatches) {
    hashMatches.forEach((hash) => indicators.push({ type: 'hash', value: hash.toLowerCase() }));
  }

  return indicators;
};
