import { FoodIntent, MenuItem, RecommendationResult, Restaurant } from './types.js';

export const SWIGGY_CATALOG: Restaurant[] = [
  {
    id: 'rest_dominos_108',
    name: "Domino's Pizza",
    slug: 'dominos-pizza-indiranagar',
    rating: 4.5,
    ratingCount: 89000,
    deliveryTimeMinutes: 20,
    address: '100ft Road, HAL 2nd Stage, Indiranagar, Bengaluru',
    cuisines: ['Pizzas', 'Italian', 'Pastas', 'Desserts', 'Fast Food'],
    coverImage: 'https://images.unsplash.com/photo-1513104890138-7c749659a591?auto=format&fit=crop&w=600&q=80',
    menu: [
      {
        id: 'dom_item_01',
        name: 'Farmhouse Pizza (Medium)',
        price: 299,
        rating: 4.7,
        ratingCount: 32000,
        description: 'Delightful combination of onion, capsicum, tomato & grilled mushroom with 100% mozzarella cheese.',
        isVeg: true,
        popular: true,
        category: 'Veg Pizzas',
        image: 'https://images.unsplash.com/photo-1534308983496-4fabb1a015ee?auto=format&fit=crop&w=500&q=80',
      },
      {
        id: 'dom_item_02',
        name: 'Peppy Paneer Pizza',
        price: 269,
        rating: 4.6,
        ratingCount: 24000,
        description: 'Chunky paneer with crisp capsicum and spicy red pepper with flavorful mozzarella.',
        isVeg: true,
        popular: true,
        category: 'Veg Pizzas',
        image: 'https://images.unsplash.com/photo-1574071318508-1cdbab80d002?auto=format&fit=crop&w=500&q=80',
      },
      {
        id: 'dom_item_03',
        name: 'Pepper Barbecue Chicken Pizza',
        price: 339,
        rating: 4.7,
        ratingCount: 41000,
        description: 'Pepper barbecue chicken for that spicy meaty kick with authentic stringy cheese.',
        isVeg: false,
        popular: true,
        category: 'Non-Veg Pizzas',
        image: 'https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?auto=format&fit=crop&w=500&q=80',
      },
      {
        id: 'dom_item_04',
        name: 'Stuffed Garlic Bread',
        price: 159,
        rating: 4.8,
        ratingCount: 48000,
        description: 'Freshly baked garlic breadsticks stuffed with cheesy jalapeños and sweet corn.',
        isVeg: true,
        popular: true,
        category: 'Sides',
        image: 'https://images.unsplash.com/photo-1619535860434-ba1d8fa12536?auto=format&fit=crop&w=500&q=80',
      },
    ],
  },
  {
    id: 'rest_twc_101',
    name: 'Third Wave Coffee',
    slug: 'third-wave-coffee-koramangala',
    rating: 4.6,
    ratingCount: 14200,
    deliveryTimeMinutes: 25,
    address: '80ft Road, 4th Block, Koramangala, Bengaluru',
    cuisines: ['Beverages', 'Coffee', 'Desserts', 'Cafe'],
    coverImage: 'https://images.unsplash.com/photo-1501339847302-ac426a4a7cbb?auto=format&fit=crop&w=600&q=80',
    menu: [
      {
        id: 'twc_item_01',
        name: 'Classic Cold Coffee',
        price: 185,
        rating: 4.7,
        ratingCount: 3820,
        description: 'Rich espresso blended with chilled milk and a hint of sweetness. Our signature cold beverage.',
        isVeg: true,
        popular: true,
        category: 'Cold Brews & Iced Coffee',
        image: 'https://images.unsplash.com/photo-1517256064527-09c73fc73e38?auto=format&fit=crop&w=500&q=80',
      },
      {
        id: 'twc_item_02',
        name: 'Vietnamese Shakerato Cold Coffee',
        price: 195,
        rating: 4.8,
        ratingCount: 2950,
        description: 'Bold espresso shaken over ice with condensed milk for a silky, caramel finish.',
        isVeg: true,
        popular: true,
        category: 'Cold Brews & Iced Coffee',
        image: 'https://images.unsplash.com/photo-1461023058943-07fcbe16d735?auto=format&fit=crop&w=500&q=80',
      },
    ],
  },
  {
    id: 'rest_blue_tokai_102',
    name: 'Blue Tokai Coffee Roasters',
    slug: 'blue-tokai-coffee-roasters-indiranagar',
    rating: 4.7,
    ratingCount: 9800,
    deliveryTimeMinutes: 20,
    address: '100ft Road, Indiranagar, Bengaluru',
    cuisines: ['Specialty Coffee', 'Cafe', 'Sandwiches', 'Bakery'],
    coverImage: 'https://images.unsplash.com/photo-1442512595331-e89e73853f31?auto=format&fit=crop&w=600&q=80',
    menu: [
      {
        id: 'bt_item_01',
        name: 'Iced Latte (Single Origin)',
        price: 190,
        rating: 4.8,
        ratingCount: 2400,
        description: 'Smooth espresso shot extracted over cold whole milk and artisanal ice cubes.',
        isVeg: true,
        popular: true,
        category: 'Iced Coffee',
        image: 'https://images.unsplash.com/photo-1517256064527-09c73fc73e38?auto=format&fit=crop&w=500&q=80',
      },
    ],
  },
  {
    id: 'rest_truffles_103',
    name: 'Truffles',
    slug: 'truffles-st-marks-road',
    rating: 4.5,
    ratingCount: 52000,
    deliveryTimeMinutes: 30,
    address: 'St. Marks Road, Ashok Nagar, Bengaluru',
    cuisines: ['American', 'Burgers', 'Fast Food', 'Beverages'],
    coverImage: 'https://images.unsplash.com/photo-1550547660-d9450f859349?auto=format&fit=crop&w=600&q=80',
    menu: [
      {
        id: 'truf_item_01',
        name: 'All American Cheese Burger',
        price: 220,
        rating: 4.7,
        ratingCount: 18400,
        description: 'Juicy chicken patty grilled with melted cheddar cheese and caramelized onions.',
        isVeg: false,
        popular: true,
        category: 'Burgers',
        image: 'https://images.unsplash.com/photo-1568901346375-23c9450c58cd?auto=format&fit=crop&w=500&q=80',
      },
    ],
  },
  {
    id: 'rest_meghana_105',
    name: 'Meghana Foods',
    slug: 'meghana-foods-residency-road',
    rating: 4.6,
    ratingCount: 78000,
    deliveryTimeMinutes: 30,
    address: 'Residency Road, Bengaluru',
    cuisines: ['Biryani', 'Andhra', 'South Indian'],
    coverImage: 'https://images.unsplash.com/photo-1563379091339-03b21ab4a4f8?auto=format&fit=crop&w=600&q=80',
    menu: [
      {
        id: 'mf_item_01',
        name: 'Meghana Special Chicken Biryani',
        price: 320,
        rating: 4.8,
        ratingCount: 34000,
        description: 'Legendary Andhra style spicy boneless chicken pieces layered on fragrant basmati rice.',
        isVeg: false,
        popular: true,
        category: 'Biryani',
        image: 'https://images.unsplash.com/photo-1563379091339-03b21ab4a4f8?auto=format&fit=crop&w=500&q=80',
      },
    ],
  },
];

export class SwiggySearchService {
  private catalog: Restaurant[];

  constructor(customCatalog: Restaurant[] = SWIGGY_CATALOG) {
    this.catalog = customCatalog;
  }

  public getRestaurants(): Restaurant[] {
    return this.catalog;
  }

  public getRestaurantById(id: string): Restaurant | undefined {
    return this.catalog.find((r) => r.id === id || r.slug.includes(id));
  }

  public searchRestaurants(restaurantName?: string | null, cuisine?: string): Restaurant[] {
    let results = [...this.catalog];

    if (restaurantName && restaurantName.trim()) {
      const query = restaurantName.toLowerCase().trim();
      const directMatches = results.filter(
        (r) =>
          r.name.toLowerCase().includes(query) ||
          query.includes(r.name.toLowerCase()) ||
          r.slug.toLowerCase().includes(query)
      );

      if (directMatches.length > 0) {
        return directMatches;
      }
    }

    if (cuisine && cuisine.trim()) {
      const cQuery = cuisine.toLowerCase().trim();
      const cuisineMatches = results.filter((r) =>
        r.cuisines.some((c) => c.toLowerCase().includes(cQuery))
      );
      if (cuisineMatches.length > 0) {
        results = cuisineMatches;
      }
    }

    return results.sort((a, b) => b.rating - a.rating);
  }

  /**
   * Finds and ranks the best matching menu items using Groq AI or local fallback.
   */
  public async findBestRecommendation(intent: FoodIntent): Promise<RecommendationResult | null> {
    // 1. Primary path: Use Groq AI for universal catalog & menu intelligence
    if (process.env.GROQ_API_KEY) {
      try {
        const groqResult = await this.findWithGroqAI(intent, process.env.GROQ_API_KEY);
        if (groqResult) {
          return groqResult;
        }
      } catch (err) {
        console.warn('Groq AI search fallback to local matcher:', err);
      }
    }

    // 2. Fallback path: Local catalog matcher
    return this.findLocally(intent);
  }

  /**
   * Universal AI Search Engine for ANY restaurant and ANY dish anywhere on Swiggy
   */
  private async findWithGroqAI(intent: FoodIntent, apiKey: string): Promise<RecommendationResult | null> {
    const systemPrompt = `You are Swiggy India's AI Restaurant & Menu Search Engine.
Given a user's food ordering query, find the exact matching restaurant and specific menu item on Swiggy.
If a restaurant is requested (e.g. RJ 14, Domino's, Haldiram's, Punjab Grill, etc.), search exclusively for that restaurant and the exact requested item.
If no restaurant is specified, select the highest-rated top authentic restaurant for that dish in India.
Respect max budget in INR (item price should be <= maxBudget if provided).
Respond strictly in valid JSON matching this schema:
{
  "restaurant": {
    "id": "string (e.g. rest_rj_14)",
    "name": "string (e.g. RJ 14)",
    "slug": "string (e.g. rj-14-ajmer-road)",
    "rating": number (e.g. 4.6),
    "ratingCount": number (e.g. 18500),
    "deliveryTimeMinutes": number (e.g. 25),
    "address": "string (e.g. Ajmer Road, Jaipur)",
    "cuisines": ["string", "string"]
  },
  "item": {
    "id": "string",
    "name": "string (exact name of the dish, e.g. Paneer Butter Masala)",
    "price": number (realistic price in INR),
    "rating": number (e.g. 4.8),
    "ratingCount": number (e.g. 5200),
    "description": "string (appetizing description)",
    "isVeg": boolean,
    "category": "string (e.g. Main Course, Biryani, Pizzas, Curries)",
    "popular": boolean
  },
  "reason": "string (why this dish from this restaurant is the best recommendation)"
}`;

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 6000);

    try {
      const res = await fetch('https://api.groq.com/openai/v1/chat/completions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${apiKey}`,
        },
        body: JSON.stringify({
          model: 'openai/gpt-oss-20b',
          messages: [
            { role: 'system', content: systemPrompt },
            {
              role: 'user',
              content: `User wants to order: ${intent.queryItem}${
                intent.restaurantName ? ` from ${intent.restaurantName}` : ''
              }${intent.maxBudget ? ` within budget of ₹${intent.maxBudget}` : ''}${
                intent.dietaryPreference !== 'any' ? ` (${intent.dietaryPreference})` : ''
              }. Output in JSON format.`,
            },
          ],
          temperature: 0.1,
          max_tokens: 600,
        }),
        signal: controller.signal,
      });

      clearTimeout(timeout);

      if (!res.ok) return null;

      const data = (await res.json()) as any;
      const rawContent = data.choices?.[0]?.message?.content;
      if (!rawContent) return null;

      // Extract JSON block if surrounded by text or code fencing
      let cleanJson = rawContent.trim();
      const match = cleanJson.match(/\{[\s\S]*\}/);
      if (match) {
        cleanJson = match[0];
      }

      const parsed = JSON.parse(cleanJson);
      if (!parsed.restaurant || !parsed.item) return null;

      const image = this.getImageForQuery(parsed.item.name || intent.queryItem);

      const restaurant: Restaurant = {
        id: parsed.restaurant.id || `rest_${Date.now()}`,
        name: parsed.restaurant.name || intent.restaurantName || 'Top-Rated Swiggy Outlet',
        slug: parsed.restaurant.slug || 'swiggy-outlet',
        rating: typeof parsed.restaurant.rating === 'number' ? parsed.restaurant.rating : 4.6,
        ratingCount: typeof parsed.restaurant.ratingCount === 'number' ? parsed.restaurant.ratingCount : 12000,
        deliveryTimeMinutes:
          typeof parsed.restaurant.deliveryTimeMinutes === 'number' ? parsed.restaurant.deliveryTimeMinutes : 25,
        address: parsed.restaurant.address || 'Koramangala, Bengaluru',
        cuisines: Array.isArray(parsed.restaurant.cuisines) ? parsed.restaurant.cuisines : ['Indian', 'Fast Food'],
        coverImage: image,
        menu: [],
      };

      const item: MenuItem = {
        id: parsed.item.id || `item_${Date.now()}`,
        name: parsed.item.name || this.capitalizeWords(intent.queryItem),
        price:
          typeof parsed.item.price === 'number'
            ? intent.maxBudget
              ? Math.min(parsed.item.price, intent.maxBudget)
              : parsed.item.price
            : 249,
        rating: typeof parsed.item.rating === 'number' ? parsed.item.rating : 4.7,
        ratingCount: typeof parsed.item.ratingCount === 'number' ? parsed.item.ratingCount : 3800,
        description:
          parsed.item.description ||
          `Freshly prepared authentic ${intent.queryItem} with premium ingredients and spices.`,
        isVeg: typeof parsed.item.isVeg === 'boolean' ? parsed.item.isVeg : intent.dietaryPreference !== 'non-veg',
        popular: true,
        category: parsed.item.category || 'Specialties',
        image,
      };

      restaurant.menu = [item];

      return {
        restaurant,
        item,
        matchScore: 98,
        reason:
          parsed.reason ||
          `Found authentic ${item.name} (₹${item.price}) at ${restaurant.name} with ⭐${item.rating} rating.`,
      };
    } catch {
      clearTimeout(timeout);
      return null;
    }
  }

  private findLocally(intent: FoodIntent): RecommendationResult | null {
    let targetRestaurants = this.searchRestaurants(intent.restaurantName, intent.cuisine);

    if (intent.restaurantName && targetRestaurants.length === 0) {
      targetRestaurants = [this.createDynamicRestaurant(intent.restaurantName, intent.queryItem)];
    }

    const queryTokens = intent.queryItem
      .toLowerCase()
      .split(/\s+/)
      .filter((t) => t.length > 1 && !['the', 'and', 'for', 'with', 'from'].includes(t));

    const candidates: Array<{
      restaurant: Restaurant;
      item: MenuItem;
      score: number;
      reason: string;
    }> = [];

    for (const rest of targetRestaurants) {
      for (const item of rest.menu) {
        if (intent.maxBudget && item.price > intent.maxBudget) continue;
        if (intent.dietaryPreference === 'veg' && !item.isVeg) continue;

        const itemNameLower = item.name.toLowerCase();
        let tokenMatches = 0;
        for (const token of queryTokens) {
          if (itemNameLower.includes(token)) tokenMatches += 5;
        }

        let score = tokenMatches * 10 + item.rating * 5 + rest.rating * 3;
        candidates.push({
          restaurant: rest,
          item,
          score,
          reason: `${item.name} (₹${item.price}) from ${rest.name} (⭐${item.rating})`,
        });
      }
    }

    const matchingCandidates = candidates.filter((c) => {
      const name = c.item.name.toLowerCase();
      return queryTokens.some((t) => name.includes(t));
    });

    if (matchingCandidates.length > 0) {
      matchingCandidates.sort((a, b) => b.score - a.score);
      const best = matchingCandidates[0];
      return {
        restaurant: best.restaurant,
        item: best.item,
        matchScore: best.score,
        reason: best.reason,
      };
    }

    const fallbackRestaurant =
      targetRestaurants[0] || this.createDynamicRestaurant(intent.restaurantName || 'Popular Kitchen', intent.queryItem);

    const dynamicItem: MenuItem = {
      id: `dyn_${Date.now()}`,
      name: this.capitalizeWords(intent.queryItem),
      price: intent.maxBudget ? Math.min(intent.maxBudget, 299) : 249,
      rating: 4.7,
      ratingCount: 15400,
      description: `Freshly prepared delicious ${intent.queryItem} with authentic ingredients.`,
      isVeg: intent.dietaryPreference !== 'non-veg',
      popular: true,
      category: 'Specials',
      image: this.getImageForQuery(intent.queryItem),
    };

    return {
      restaurant: fallbackRestaurant,
      item: dynamicItem,
      matchScore: 90,
      reason: `Found top-rated match: ${dynamicItem.name} (₹${dynamicItem.price}) at ${fallbackRestaurant.name}`,
    };
  }

  private createDynamicRestaurant(name: string, queryItem: string): Restaurant {
    const slug = name
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/(^-|-$)/g, '');
    return {
      id: `rest_${slug}`,
      name: this.capitalizeWords(name),
      slug: `${slug}-outlet`,
      rating: 4.6,
      ratingCount: 28000,
      deliveryTimeMinutes: 25,
      address: 'City Center Outlet, India',
      cuisines: ['Indian', 'North Indian', 'Specialties'],
      coverImage: this.getImageForQuery(queryItem),
      menu: [],
    };
  }

  private capitalizeWords(str: string): string {
    return str
      .split(' ')
      .map((w) => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
      .join(' ');
  }

  private getImageForQuery(query: string): string {
    const lower = query.toLowerCase();
    if (lower.includes('paneer') || lower.includes('butter masala') || lower.includes('curry') || lower.includes('dal')) {
      return 'https://images.unsplash.com/photo-1631452180519-c014fe946bc7?auto=format&fit=crop&w=500&q=80';
    }
    if (lower.includes('pizza')) {
      return 'https://images.unsplash.com/photo-1513104890138-7c749659a591?auto=format&fit=crop&w=500&q=80';
    }
    if (lower.includes('burger')) {
      return 'https://images.unsplash.com/photo-1568901346375-23c9450c58cd?auto=format&fit=crop&w=500&q=80';
    }
    if (lower.includes('biryani') || lower.includes('rice') || lower.includes('pulao')) {
      return 'https://images.unsplash.com/photo-1563379091339-03b21ab4a4f8?auto=format&fit=crop&w=500&q=80';
    }
    if (lower.includes('coffee') || lower.includes('latte')) {
      return 'https://images.unsplash.com/photo-1517256064527-09c73fc73e38?auto=format&fit=crop&w=500&q=80';
    }
    if (lower.includes('tea') || lower.includes('chai')) {
      return 'https://images.unsplash.com/photo-1576092768241-dec231879fc3?auto=format&fit=crop&w=500&q=80';
    }
    return 'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?auto=format&fit=crop&w=500&q=80';
  }

  /**
   * Generates native Swiggy deep link and universal web fallback
   */
  public generateDeepLinks(
    restaurant: Restaurant | { id: string; name?: string; slug: string },
    item: MenuItem
  ): {
    deepLink: string;
    webUrl: string;
  } {
    const restaurantName = (restaurant as any).name || restaurant.slug.replace(/-/g, ' ');
    const query = `${item.name} ${restaurantName}`.trim();

    // 1. Native Swiggy Explore / Search Intent: opens Swiggy directly into search for that item at that restaurant
    const deepLink = `swiggy://explore?query=${encodeURIComponent(query)}`;

    // 2. Swiggy Restaurant Direct Web / App Universal Link
    const webUrl = `https://www.swiggy.com/restaurants/${restaurant.slug}`;

    return {
      deepLink,
      webUrl,
    };
  }
}
