import { FoodIntent, FoodIntentSchema } from '../tools/swiggy/types.js';

export class IntentExtractor {
  /**
   * Extracts structured FoodIntent from natural language prompt or voice transcript.
   * Prioritizes Groq API (GROQ_API_KEY) if available, or falls back to robust local rules.
   */
  public static async extract(inputPrompt: string): Promise<FoodIntent> {
    const prompt = inputPrompt.trim();
    if (!prompt) {
      return FoodIntentSchema.parse({
        queryItem: 'cold coffee',
        maxBudget: 200,
        restaurantName: null,
        dietaryPreference: 'any',
      });
    }

    // 1. If GROQ_API_KEY is configured, use Groq's high-speed model
    if (process.env.GROQ_API_KEY) {
      try {
        const groqIntent = await this.extractWithGroq(prompt, process.env.GROQ_API_KEY);
        if (groqIntent) {
          return FoodIntentSchema.parse(groqIntent);
        }
      } catch (err) {
        console.warn('Groq extraction fallback to rules:', err);
      }
    }

    // 2. Fallback to deterministic NLP / Regex extraction
    const extracted = this.extractWithRules(prompt);
    return FoodIntentSchema.parse(extracted);
  }

  /**
   * High-speed LLM extraction via Groq API (OpenAI-compatible)
   */
  private static async extractWithGroq(prompt: string, apiKey: string): Promise<FoodIntent | null> {
    const systemPrompt = `You are a food ordering intent parser for Swiggy India.
Extract the target food/beverage item, maximum budget in INR (numbers only), specific restaurant name (if mentioned, otherwise null), and dietary preference ('veg', 'non-veg', or 'any').
Important: Do not include articles like 'a', 'an', 'the' in queryItem.
Respond strictly in valid JSON matching this schema:
{
  "queryItem": "string (e.g. farmhouse pizza, cold coffee, chicken burger, biryani)",
  "maxBudget": number or null (e.g. 200),
  "restaurantName": "string or null (e.g. Domino's Pizza, Third Wave Coffee, Truffles)",
  "dietaryPreference": "veg" | "non-veg" | "any"
}`;

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 3500);

    try {
      const res = await fetch('https://api.groq.com/openai/v1/chat/completions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${apiKey}`,
        },
        body: JSON.stringify({
          model: 'qwen/qwen3.6-27b',
          messages: [
            { role: 'system', content: systemPrompt },
            { role: 'user', content: prompt },
          ],
          response_format: { type: 'json_object' },
          temperature: 0.1,
          max_tokens: 150,
        }),
        signal: controller.signal,
      });

      clearTimeout(timeout);

      if (!res.ok) {
        return null;
      }

      const json = (await res.json()) as any;
      const content = json.choices?.[0]?.message?.content;
      if (!content) return null;

      const parsed = JSON.parse(content);
      let queryItem = (parsed.queryItem || '').replace(/^(?:a|an|the)\s+/i, '').trim();
      if (!queryItem) queryItem = 'farmhouse pizza';

      return {
        queryItem,
        maxBudget: typeof parsed.maxBudget === 'number' ? parsed.maxBudget : undefined,
        restaurantName: parsed.restaurantName || null,
        dietaryPreference: ['veg', 'non-veg', 'any'].includes(parsed.dietaryPreference)
          ? parsed.dietaryPreference
          : 'any',
      };
    } catch {
      clearTimeout(timeout);
      return null;
    }
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

    // 2. Extract Restaurant Name if mentioned
    let restaurantName: string | null = null;
    const knownRestaurants = [
      { name: "Domino's Pizza", aliases: ["domino's pizza", 'dominos pizza', "domino's", 'dominos'] },
      { name: 'Pizza Hut', aliases: ['pizza hut'] },
      { name: 'Burger King', aliases: ['burger king', 'bk'] },
      { name: "McDonald's", aliases: ["mcdonald's", 'mcdonalds', 'mcd'] },
      { name: 'KFC', aliases: ['kfc', 'kentucky fried chicken'] },
      { name: 'Subway', aliases: ['subway'] },
      { name: 'Third Wave Coffee', aliases: ['third wave coffee', 'third wave', 'twc'] },
      { name: 'Blue Tokai Coffee Roasters', aliases: ['blue tokai coffee roasters', 'blue tokai', 'bt'] },
      { name: 'Truffles', aliases: ['truffles', 'truffle'] },
      { name: 'Starbucks Coffee', aliases: ['starbucks coffee', 'starbucks'] },
      { name: 'Meghana Foods', aliases: ['meghana foods', 'meghana biryani', 'meghana'] },
      { name: 'California Burrito', aliases: ['california burrito'] },
      { name: 'Chai Point', aliases: ['chai point'] },
      { name: 'Behrouz Biryani', aliases: ['behrouz biryani', 'behrouz'] },
      { name: "Haldiram's", aliases: ["haldiram's", 'haldirams'] },
    ];

    for (const rest of knownRestaurants) {
      if (rest.aliases.some((alias) => lower.includes(alias))) {
        restaurantName = rest.name;
        break;
      }
    }

    // If not matched by known list, check prepositions "from [Restaurant]", "at [Restaurant]"
    if (!restaurantName) {
      const fromMatch = prompt.match(
        /(?:from|at|in)\s+([A-Za-z0-9\s'&]+?)(?:\s+(?:under|within|below|for|with|less|<=)|$)/i
      );
      if (fromMatch && fromMatch[1]) {
        const candidate = fromMatch[1].trim();
        if (
          candidate.length > 2 &&
          !['swiggy', 'zomato', 'here', 'nearby', 'anywhere'].includes(candidate.toLowerCase())
        ) {
          restaurantName = candidate;
        }
      }
    }

    // 3. Extract Dietary Preference
    let dietaryPreference: 'veg' | 'non-veg' | 'any' = 'any';
    if (/\b(pure\s+veg|vegetarian|veg)\b/i.test(prompt) && !/\b(non-veg|nonveg)\b/i.test(prompt)) {
      dietaryPreference = 'veg';
    } else if (/\b(non-veg|nonveg|chicken|mutton|egg|meat|beef|pork)\b/i.test(prompt)) {
      dietaryPreference = 'non-veg';
    }

    // 4. Extract Query Item
    let queryItem = prompt;

    // Remove noise phrases
    const noisePhrases = [
      /order\s+(?:me\s+)?(?:a|an|the)?/gi,
      /find\s+(?:me\s+)?(?:a|an|the)?/gi,
      /get\s+(?:me\s+)?(?:a|an|the)?/gi,
      /buy\s+(?:me\s+)?(?:a|an|the)?/gi,
      /search\s+(?:for\s+)?(?:a|an|the)?/gi,
      /i\s+want\s+(?:to\s+order\s+)?(?:a|an|the)?/gi,
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
      .replace(/^(?:a|an|the)\s+/i, '')
      .replace(/\s+/g, ' ')
      .trim();

    if (!queryItem || queryItem.length < 2) {
      queryItem = 'pizza';
    }

    return {
      queryItem,
      maxBudget,
      restaurantName,
      dietaryPreference,
    };
  }
}
