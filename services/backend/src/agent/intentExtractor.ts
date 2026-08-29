import { FoodIntent, FoodIntentSchema } from '../tools/swiggy/types.js';

export class IntentExtractor {
  /**
   * Extracts structured FoodIntent from natural language prompt or voice transcript.
   */
  public static async extract(inputPrompt: string): Promise<FoodIntent> {
    const prompt = inputPrompt.trim();
    if (!prompt) {
      return FoodIntentSchema.parse({
        queryItem: 'coffee',
        maxBudget: 200,
        restaurantName: null,
        dietaryPreference: 'any',
      });
    }

    // Attempt rule-based heuristic extraction first for instant speed & zero-dependency local execution
    const extracted = this.extractWithRules(prompt);
    return FoodIntentSchema.parse(extracted);
  }

  /**
   * Deterministic NLP/Regex extraction for local and production resilience.
   */
  public static extractWithRules(prompt: string): FoodIntent {
    const lower = prompt.toLowerCase();

    // 1. Extract Budget (e.g., "under 200", "within 250", "₹200", "200 rs", "under ₹180", "budget 300", "<200")
    let maxBudget: number | undefined = undefined;
    const budgetPatterns = [
      /(?:under|below|within|less\s+than|budget(?:\s+of)?|max|upto|up\s+to|<=?)\s*(?:rs\.?|inr|₹)?\s*(\d+)/i,
      /(?:rs\.?|inr|₹)\s*(\d+)/i,
      /(\d+)\s*(?:rs|rupees|inr|bucks)/i,
      /\bunder\s*(\d+)\b/i,
    ];

    for (const pattern of budgetPatterns) {
      const match = prompt.match(pattern);
      if (match && match[1]) {
        const val = parseInt(match[1], 10);
        if (!isNaN(val) && val > 0) {
          maxBudget = val;
          break;
        }
      }
    }

    // 2. Extract Restaurant Name if mentioned (e.g., "from Third Wave Coffee", "at Truffles", "Starbucks", "Blue Tokai")
    let restaurantName: string | null = null;
    const knownRestaurants = [
      { name: 'Third Wave Coffee', aliases: ['third wave coffee', 'third wave', 'twc'] },
      { name: 'Blue Tokai Coffee Roasters', aliases: ['blue tokai coffee roasters', 'blue tokai', 'bt'] },
      { name: 'Truffles', aliases: ['truffles', 'truffle'] },
      { name: 'Starbucks Coffee', aliases: ['starbucks coffee', 'starbucks'] },
      { name: 'Meghana Foods', aliases: ['meghana foods', 'meghana biryani', 'meghana'] },
      { name: 'California Burrito', aliases: ['california burrito'] },
      { name: 'Chai Point', aliases: ['chai point'] },
    ];

    for (const rest of knownRestaurants) {
      if (rest.aliases.some((alias) => lower.includes(alias))) {
        restaurantName = rest.name;
        break;
      }
    }

    // If not matched by known list, check prepositions "from [Restaurant]", "at [Restaurant]"
    if (!restaurantName) {
      const fromMatch = prompt.match(/(?:from|at|in)\s+([A-Za-z0-9\s'&]+?)(?:\s+(?:under|within|below|for|with|less|<=)|$)/i);
      if (fromMatch && fromMatch[1]) {
        const candidate = fromMatch[1].trim();
        if (candidate.length > 2 && !['swiggy', 'zomato', 'here', 'nearby', 'anywhere'].includes(candidate.toLowerCase())) {
          restaurantName = candidate;
        }
      }
    }

    // 3. Extract Dietary Preference
    let dietaryPreference: 'veg' | 'non-veg' | 'any' = 'any';
    if (/\b(pure\s+veg|vegetarian|veg)\b/i.test(prompt) && !/\b(non-veg|nonveg)\b/i.test(prompt)) {
      dietaryPreference = 'veg';
    } else if (/\b(non-veg|nonveg|chicken|mutton|egg|meat)\b/i.test(prompt)) {
      dietaryPreference = 'non-veg';
    }

    // 4. Extract Query Item
    let queryItem = prompt;

    // Remove noise phrases
    const noisePhrases = [
      /find(?:\s+me)?/gi,
      /get(?:\s+me)?/gi,
      /order(?:\s+me)?/gi,
      /buy(?:\s+me)?/gi,
      /search(?:\s+for)?/gi,
      /i\s+want(?:\s+to\s+order)?/gi,
      /best-?rated/gi,
      /best/gi,
      /top-?rated/gi,
      /cheap(?:est)?/gi,
      /good/gi,
      /please/gi,
    ];

    for (const phrase of noisePhrases) {
      queryItem = queryItem.replace(phrase, '');
    }

    // Remove budget substring from query item
    for (const pattern of budgetPatterns) {
      queryItem = queryItem.replace(pattern, '');
    }

    // Remove restaurant mentions from query item
    if (restaurantName) {
      queryItem = queryItem.replace(new RegExp(`(?:from|at)?\\s*${restaurantName}`, 'gi'), '');
    }
    for (const rest of knownRestaurants) {
      for (const alias of rest.aliases) {
        queryItem = queryItem.replace(new RegExp(`(?:from|at)?\\s*${alias}`, 'gi'), '');
      }
    }

    // Clean punctuation and excess whitespace
    queryItem = queryItem
      .replace(/[^\w\s-]/g, ' ')
      .replace(/\s+/g, ' ')
      .trim();

    if (!queryItem || queryItem.length < 2) {
      queryItem = 'cold coffee';
    }

    return {
      queryItem,
      maxBudget,
      restaurantName,
      dietaryPreference,
    };
  }
}
