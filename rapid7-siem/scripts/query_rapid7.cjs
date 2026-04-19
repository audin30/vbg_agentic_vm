const axios = require('axios');

/**
 * Rapid7 InsightIDR Query Script for Gemini CLI
 * 
 * Requirements:
 * - axios
 * 
 * Environment Variables:
 * - RAPID7_API_KEY: Your InsightIDR API Key.
 * - RAPID7_REGION: The region (e.g., 'us', 'eu', 'ca', 'au', 'jp').
 */

const REGION = process.env.RAPID7_REGION || 'us';
const API_BASE_URL = `https://${REGION}.api.insight.rapid7.com/idr/v1`;

async function searchInvestigations(target) {
  const url = `${API_BASE_URL}/investigations`;
  
  try {
    const response = await axios.get(url, {
      headers: { 
        'X-Api-Key': process.env.RAPID7_API_KEY,
        'Content-Type': 'application/json'
      },
      params: { 
        size: 5,
        sort: 'created_time,DESC'
      }
    });
    
    // Simple filter on the client side if the API doesn't support direct target search on list
    // In a real implementation, you'd use Log Search or specific Investigation search
    const results = response.data.data.filter(inv => 
      inv.title.includes(target) || 
      inv.description.includes(target)
    );

    return results;
  } catch (error) {
    throw new Error(`Error querying InsightIDR: ${error.message}`);
  }
}

async function main() {
  const args = process.argv.slice(2);
  const target = args[0];

  if (!process.env.RAPID7_API_KEY) {
    console.error('Error: RAPID7_API_KEY environment variable is not set.');
    process.exit(1);
  }

  if (!target) {
    console.log('Usage: node query_rapid7.cjs <target>');
    process.exit(1);
  }

  try {
    console.log(`Searching InsightIDR for: ${target}...`);
    const results = await searchInvestigations(target);
    console.log(JSON.stringify(results, null, 2));
  } catch (error) {
    console.error(error.message);
    process.exit(1);
  }
}

main();
