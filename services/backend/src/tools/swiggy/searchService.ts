import { getFoodImage } from './foodImageService.js';
import { FoodIntent, MenuItem, RecommendationResult, Restaurant } from './types.js';

export const SWIGGY_CATALOG: Restaurant[] = [
  {
    id: 'rest_blue_tokai_102',
    name: 'Blue Tokai Coffee Roasters',
    slug: 'blue-tokai-coffee-roasters-indiranagar',
    rating: 4.7,
    ratingCount: 14800,
    deliveryTimeMinutes: 20,
    address: '100ft Road, Indiranagar, Bengaluru',
    city: 'Bengaluru',
    cuisines: ['Specialty Coffee', 'Cafe', 'Sandwiches', 'Bakery', 'Desserts'],
    coverImage: 'https://images.unsplash.com/photo-1442512595331-e89e73853f31?auto=format&fit=crop&w=600&q=80',
    menu: [
      {
        id: 'bt_item_01',
        name: 'Cappuccino (Specialty Roast)',
        price: 210,
        rating: 4.8,
        ratingCount: 5200,
        description: 'Velvety double shot espresso extracted from artisanal beans, topped with perfectly steamed silky microfoam.',
        isVeg: true,
        popular: true,
        category: 'Hot Coffee',
        image: getFoodImage('cappuccino'),
      },
      {
        id: 'bt_item_02',
        name: 'Flat White',
        price: 230,
        rating: 4.8,
        ratingCount: 3100,
        description: 'Bold espresso blended with steamed whole milk with a velvety microfoam layer.',
        isVeg: true,
        popular: true,
        category: 'Hot Coffee',
        image: getFoodImage('flat white'),
      },
      {
        id: 'bt_item_03',
        name: 'Iced Latte (Single Origin)',
        price: 210,
        rating: 4.8,
        ratingCount: 4400,
        description: 'Smooth espresso shot extracted over cold whole milk and artisanal ice cubes.',
        isVeg: true,
        popular: true,
        category: 'Iced Coffee',
        image: getFoodImage('iced latte'),
      },
      {
        id: 'bt_item_04',
        name: 'Classic Cold Brew',
        price: 200,
        rating: 4.7,
        ratingCount: 2900,
        description: 'Steeped for 18 hours for a naturally sweet, low-acidity craft coffee experience.',
        isVeg: true,
        popular: true,
        category: 'Cold Brews',
        image: getFoodImage('cold brew'),
      },
      {
        id: 'bt_item_05',
        name: 'Almond Butter Croissant',
        price: 180,
        rating: 4.7,
        ratingCount: 1800,
        description: 'Flaky French style butter croissant filled with frangipane almond cream and toasted almond flakes.',
        isVeg: true,
        popular: true,
        category: 'Bakery',
        image: getFoodImage('croissant'),
      },
      {
        id: 'bt_item_06',
        name: 'Smoked Chicken & Pesto Sandwich',
        price: 290,
        rating: 4.7,
        ratingCount: 2100,
        description: 'Tender smoked chicken breast layered with fresh basil pesto and melted mozzarella on artisanal sourdough.',
        isVeg: false,
        popular: true,
        category: 'Sandwiches',
        image: getFoodImage('chicken sandwich'),
      },
    ],
  },
  {
    id: 'rest_twc_101',
    name: 'Third Wave Coffee',
    slug: 'third-wave-coffee-koramangala',
    rating: 4.6,
    ratingCount: 18200,
    deliveryTimeMinutes: 25,
    address: '80ft Road, 4th Block, Koramangala, Bengaluru',
    city: 'Bengaluru',
    cuisines: ['Beverages', 'Coffee', 'Desserts', 'Cafe', 'Bakery'],
    coverImage: 'https://images.unsplash.com/photo-1501339847302-ac426a4a7cbb?auto=format&fit=crop&w=600&q=80',
    menu: [
      {
        id: 'twc_item_01',
        name: 'Classic Cold Coffee',
        price: 185,
        rating: 4.7,
        ratingCount: 6820,
        description: 'Rich espresso blended with chilled milk and a hint of sweetness. Our signature cold beverage.',
        isVeg: true,
        popular: true,
        category: 'Cold Brews & Iced Coffee',
        image: getFoodImage('cold coffee'),
      },
      {
        id: 'twc_item_02',
        name: 'Classic Cappuccino',
        price: 195,
        rating: 4.7,
        ratingCount: 4200,
        description: 'Espresso poured with silky textured milk and topped with dense frothy foam and cocoa dusting.',
        isVeg: true,
        popular: true,
        category: 'Hot Coffee',
        image: getFoodImage('cappuccino'),
      },
      {
        id: 'twc_item_03',
        name: 'Vietnamese Shakerato Cold Coffee',
        price: 195,
        rating: 4.8,
        ratingCount: 3950,
        description: 'Bold espresso shaken over ice with condensed milk for a silky, caramel finish.',
        isVeg: true,
        popular: true,
        category: 'Cold Brews & Iced Coffee',
        image: getFoodImage('vietnamese cold coffee'),
      },
      {
        id: 'twc_item_04',
        name: 'Bagel with Cream Cheese',
        price: 165,
        rating: 4.6,
        ratingCount: 1540,
        description: 'Toasted multigrain bagel served with garlic and herb cream cheese spread.',
        isVeg: true,
        popular: true,
        category: 'Bakery',
        image: getFoodImage('bagel'),
      },
    ],
  },
  {
    id: 'rest_starbucks_104',
    name: 'Starbucks Coffee',
    slug: 'starbucks-coffee-indiranagar',
    rating: 4.6,
    ratingCount: 22000,
    deliveryTimeMinutes: 25,
    address: '100ft Road, Indiranagar, Bengaluru',
    city: 'Bengaluru',
    cuisines: ['Beverages', 'Coffee', 'Desserts', 'Cafe', 'Fast Food'],
    coverImage: 'https://images.unsplash.com/photo-1501339847302-ac426a4a7cbb?auto=format&fit=crop&w=600&q=80',
    menu: [
      {
        id: 'sb_item_01',
        name: 'Cappuccino (Grande)',
        price: 285,
        rating: 4.8,
        ratingCount: 6500,
        description: 'Dark, rich espresso lies in wait under a smoothed and stretched layer of thick milk foam.',
        isVeg: true,
        popular: true,
        category: 'Hot Coffee',
        image: getFoodImage('cappuccino'),
      },
      {
        id: 'sb_item_02',
        name: 'Caffe Latte',
        price: 295,
        rating: 4.8,
        ratingCount: 5800,
        description: 'Our dark, rich espresso balanced with steamed milk and a light layer of foam.',
        isVeg: true,
        popular: true,
        category: 'Hot Coffee',
        image: getFoodImage('latte'),
      },
      {
        id: 'sb_item_03',
        name: 'Java Chip Frappuccino',
        price: 375,
        rating: 4.9,
        ratingCount: 8900,
        description: 'Mocha sauce and Frappuccino chips blended with coffee, milk and ice, topped with whipped cream.',
        isVeg: true,
        popular: true,
        category: 'Frappuccino',
        image: getFoodImage('frappe'),
      },
    ],
  },
  {
    id: 'rest_dominos_108',
    name: "Domino's Pizza",
    slug: 'dominos-pizza-indiranagar',
    rating: 4.5,
    ratingCount: 89000,
    deliveryTimeMinutes: 20,
    address: '100ft Road, HAL 2nd Stage, Indiranagar, Bengaluru',
    city: 'Bengaluru',
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
        image: getFoodImage('farmhouse pizza'),
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
        image: getFoodImage('peppy paneer pizza'),
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
        image: getFoodImage('barbecue chicken pizza'),
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
        image: getFoodImage('stuffed garlic bread'),
      },
      {
        id: 'dom_item_05',
        name: 'Choco Lava Cake',
        price: 109,
        rating: 4.9,
        ratingCount: 52000,
        description: 'Warm chocolate cake with a delightfully rich, molten chocolate center.',
        isVeg: true,
        popular: true,
        category: 'Desserts',
        image: getFoodImage('choco lava cake'),
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
    city: 'Bengaluru',
    cuisines: ['American', 'Burgers', 'Fast Food', 'Beverages', 'Desserts'],
    coverImage: 'https://images.unsplash.com/photo-1550547660-d9450f859349?auto=format&fit=crop&w=600&q=80',
    menu: [
      {
        id: 'truf_item_01',
        name: 'All American Cheese Burger',
        price: 220,
        rating: 4.7,
        ratingCount: 18400,
        description: 'Juicy patty grilled with melted cheddar cheese, special sauce, and caramelized onions.',
        isVeg: false,
        popular: true,
        category: 'Burgers',
        image: getFoodImage('cheeseburger'),
      },
      {
        id: 'truf_item_02',
        name: 'Crispy Peri Peri Veg Burger',
        price: 175,
        rating: 4.6,
        ratingCount: 14200,
        description: 'Crispy potato patty tossed in spicy peri peri spice mix with lettuce and creamy mayo.',
        isVeg: true,
        popular: true,
        category: 'Burgers',
        image: getFoodImage('veg burger'),
      },
      {
        id: 'truf_item_03',
        name: 'Ferrero Rocher Thick Shake',
        price: 210,
        rating: 4.8,
        ratingCount: 11900,
        description: 'Creamy chocolate shake blended with genuine Ferrero Rocher pralines and hazelnut cream.',
        isVeg: true,
        popular: true,
        category: 'Beverages',
        image: getFoodImage('chocolate shake'),
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
    city: 'Bengaluru',
    cuisines: ['Biryani', 'Andhra', 'South Indian', 'North Indian'],
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
        image: getFoodImage('chicken biryani'),
      },
      {
        id: 'mf_item_02',
        name: 'Paneer Biryani',
        price: 280,
        rating: 4.6,
        ratingCount: 12500,
        description: 'Succulent marinated paneer cubes cooked in rich Andhra spices and dum basmati rice.',
        isVeg: true,
        popular: true,
        category: 'Biryani',
        image: getFoodImage('veg biryani'),
      },
      {
        id: 'mf_item_03',
        name: 'Andhra Chicken 65',
        price: 290,
        rating: 4.7,
        ratingCount: 22000,
        description: 'Spicy, deep-fried chicken tempered with curry leaves and green chillies.',
        isVeg: false,
        popular: true,
        category: 'Starters',
        image: getFoodImage('chicken wings'),
      },
    ],
  },
  {
    id: 'rest_haldiram_106',
    name: "Haldiram's",
    slug: 'haldirams-sweets-snacks',
    rating: 4.6,
    ratingCount: 65000,
    deliveryTimeMinutes: 25,
    address: 'Commercial Street, Bengaluru',
    city: 'Bengaluru',
    cuisines: ['North Indian', 'Street Food', 'Sweets', 'Chaat', 'Thali'],
    coverImage: 'https://images.unsplash.com/photo-1626132647523-66f5bf380027?auto=format&fit=crop&w=600&q=80',
    menu: [
      {
        id: 'hald_item_01',
        name: 'Special Chole Bhature (2 Pcs)',
        price: 180,
        rating: 4.8,
        ratingCount: 28000,
        description: 'Piping hot fluffy bhature served with rich, spicy Amritsari chole, pickled onions and green chili.',
        isVeg: true,
        popular: true,
        category: 'North Indian',
        image: getFoodImage('chole bhature'),
      },
      {
        id: 'hald_item_02',
        name: 'Raj Kachori',
        price: 130,
        rating: 4.7,
        ratingCount: 19500,
        description: 'Crisp giant kachori stuffed with diced potatoes, sprouts, sweetened yogurt, and tamarind chutney.',
        isVeg: true,
        popular: true,
        category: 'Chaat',
        image: getFoodImage('chaat'),
      },
      {
        id: 'hald_item_03',
        name: 'Gulab Jamun (2 Pcs)',
        price: 70,
        rating: 4.9,
        ratingCount: 31000,
        description: 'Soft, melt-in-mouth cottage cheese dumplings soaked in aromatic cardamom sugar syrup.',
        isVeg: true,
        popular: true,
        category: 'Sweets',
        image: getFoodImage('gulab jamun'),
      },
    ],
  },
  {
    id: 'rest_chaipoint_107',
    name: 'Chai Point',
    slug: 'chai-point-koramangala',
    rating: 4.5,
    ratingCount: 34000,
    deliveryTimeMinutes: 20,
    address: 'Koramangala 5th Block, Bengaluru',
    city: 'Bengaluru',
    cuisines: ['Tea', 'Beverages', 'Fast Food', 'Snacks'],
    coverImage: 'https://images.unsplash.com/photo-1576092768241-dec231879fc3?auto=format&fit=crop&w=600&q=80',
    menu: [
      {
        id: 'cp_item_01',
        name: 'Ginger Elaichi Chai (Mini Flask 500ml)',
        price: 149,
        rating: 4.7,
        ratingCount: 14200,
        description: 'Freshly brewed hot milk tea infused with crushed ginger and aromatic green cardamom.',
        isVeg: true,
        popular: true,
        category: 'Chai',
        image: getFoodImage('masala chai'),
      },
      {
        id: 'cp_item_02',
        name: 'Bun Maska',
        price: 65,
        rating: 4.6,
        ratingCount: 8900,
        description: 'Soft sweet bun generously layered with fresh creamy Amul butter.',
        isVeg: true,
        popular: true,
        category: 'Snacks',
        image: getFoodImage('bread'),
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

  public searchRestaurants(
    restaurantName?: string | null,
    cuisine?: string,
    city?: string
  ): Restaurant[] {
    let results = [...this.catalog];

    if (city && city.trim()) {
      const c = city.toLowerCase().trim();
      results = results.filter((r) => !r.city || r.city.toLowerCase() === c);
    }

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
      // If a specific restaurant was requested but not found in catalog for this city, return empty so dynamic synthesis activates
      return [];
    }

    if (cuisine && cuisine.trim()) {
      const cQuery = cuisine.toLowerCase().trim();
      const cuisineMatches = results.filter((r) =>
        r.cuisines.some((c) => c.toLowerCase().includes(cQuery))
      );
      if (cuisineMatches.length > 0) {
        results = cuisineMatches;
      } else {
        return [];
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
The user is ordering in **${intent.city}**, India. You MUST return a restaurant outlet that genuinely operates in ${intent.city}. Do NOT return a branch from a different city, even if it is the chain's most famous or highest-rated location elsewhere in India. If you cannot confidently identify a real outlet of the requested restaurant operating in ${intent.city}, respond with exactly {"restaurant": null} instead of guessing a branch from another city.

Given a user's food ordering query, find the exact matching restaurant and specific menu item on Swiggy in ${intent.city}.
If a restaurant is requested (e.g. Blue Tokai, Third Wave Coffee, Starbucks, RJ 14, Domino's, Haldiram's, Truffles, Punjab Grill, etc.), search exclusively for that restaurant in ${intent.city} and the exact requested item.
If no restaurant is specified, select the highest-rated top authentic restaurant for that dish in ${intent.city}, India.

PRICING INTELLIGENCE RULES (Indian Rupees - INR):
- Standard Specialty Cafe (Blue Tokai, Third Wave Coffee, Costa Coffee):
  * Cappuccino / Flat White / Latte: ₹190 - ₹230
  * Cold Brew / Iced Latte: ₹200 - ₹240
  * Espresso: ₹140 - ₹170
  * Sandwiches / Croissants: ₹170 - ₹290
- Premium Cafe (Starbucks):
  * Cappuccino / Latte: ₹280 - ₹320
  * Frappuccino: ₹350 - ₹420
- Fast Food & Burgers (Truffles, Burger King, McDonald's):
  * Burgers: ₹120 - ₹240
  * Fries: ₹90 - ₹140
  * Shakes: ₹160 - ₹220
- Biryani & Mughlai (Meghana Foods, Behrouz, Paradise):
  * Chicken Biryani: ₹290 - ₹360
  * Mutton Biryani: ₹380 - ₹480
  * Paneer / Veg Biryani: ₹240 - ₹300
- Pizza Outlets (Domino's, Pizza Hut, La Pino'z):
  * Medium Pizza: ₹260 - ₹420
  * Garlic Bread: ₹130 - ₹180
- South Indian (Sagar Ratna, Rameshwaram Cafe, Saravana Bhavan):
  * Masala Dosa: ₹90 - ₹160
  * Idli Vada: ₹70 - ₹120
  * Filter Coffee: ₹40 - ₹80
- Tea Outlets (Chai Point, Chaayos):
  * Chai: ₹50 - ₹90

Respect maxBudget if provided (item price MUST be <= maxBudget).
Respond strictly in valid JSON matching this schema (or {"restaurant": null} if no operating outlet in ${intent.city}):
{
  "restaurant": {
    "id": "string",
    "name": "string (e.g. Blue Tokai Coffee Roasters)",
    "slug": "string (e.g. blue-tokai-coffee-roasters-c-scheme-jaipur)",
    "rating": number (4.0 to 4.9),
    "ratingCount": number,
    "deliveryTimeMinutes": number (15 to 40),
    "address": "string (mention area and ${intent.city}, India)",
    "city": "${intent.city}",
    "cuisines": ["string"]
  },
  "item": {
    "id": "string",
    "name": "string (exact authentic dish name, e.g. Cappuccino)",
    "price": number (exact realistic menu price in INR),
    "rating": number (4.2 to 4.9),
    "ratingCount": number,
    "description": "string (genuine, appetizing description)",
    "isVeg": boolean,
    "category": "string (e.g. Hot Coffee, Iced Coffee, Pizzas, Biryani, Burgers, Desserts)",
    "popular": boolean
  },
  "reason": "string (why this dish from this restaurant in ${intent.city} is the best match)"
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
              content: `User is in ${intent.city}. Wants to order: ${intent.queryItem}${
                intent.restaurantName ? ` from ${intent.restaurantName}` : ''
              }${intent.maxBudget ? ` within budget of ₹${intent.maxBudget}` : ''}${
                intent.dietaryPreference !== 'any' ? ` (${intent.dietaryPreference})` : ''
              }. Provide exact Indian Swiggy menu item name, realistic price, and details in ${intent.city} in JSON format.`,
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

      // Extract JSON block if surrounded by text, markdown, or code fencing
      let cleanJson = rawContent.trim();
      const match = cleanJson.match(/\{[\s\S]*\}/);
      if (match) {
        cleanJson = match[0];
      }

      const parsed = JSON.parse(cleanJson);

      // If Groq explicitly indicates no operating outlet in this city
      if (parsed.restaurant === null || (parsed.restaurant && parsed.restaurant.name === null)) {
        return null;
      }

      // Flexible mapping for robust schema normalization
      const restData = parsed.restaurant || {
        id: `rest_${Date.now()}`,
        name: parsed.brand || parsed.restaurant_name || intent.restaurantName || `Top-Rated Outlet in ${intent.city}`,
        slug: (parsed.brand || parsed.restaurant_name || intent.restaurantName || `swiggy-${intent.city}`)
          .toLowerCase()
          .replace(/[^a-z0-9]+/g, '-')
          .replace(/(^-|-$)/g, ''),
        rating: 4.7,
        ratingCount: 12000,
        deliveryTimeMinutes: 25,
        address: `${intent.city}, India`,
        city: intent.city,
        cuisines: ['Cafe', 'Specialties'],
      };

      const itemData = parsed.item || {
        id: parsed.item_id || `item_${Date.now()}`,
        name: parsed.name || parsed.item_name || this.capitalizeWords(intent.queryItem),
        price: parsed.price || parsed.price_inr || parsed.priceInr || this.estimatePriceForQuery(intent.queryItem, intent.restaurantName, intent.maxBudget),
        rating: parsed.rating || 4.8,
        ratingCount: parsed.rating_count || parsed.ratingCount || 3800,
        description: parsed.description || `Freshly prepared authentic ${intent.queryItem} with premium ingredients.`,
        isVeg: typeof parsed.is_veg === 'boolean' ? parsed.is_veg : typeof parsed.isVeg === 'boolean' ? parsed.isVeg : intent.dietaryPreference !== 'non-veg',
        category: parsed.category || 'Specialties',
        popular: true,
      };

      const itemName = itemData.name || this.capitalizeWords(intent.queryItem);
      const image = getFoodImage(itemName, itemData.category, itemData.description);

      let finalPrice = typeof itemData.price === 'number' && itemData.price > 0
        ? itemData.price
        : this.estimatePriceForQuery(intent.queryItem, intent.restaurantName, intent.maxBudget);

      if (intent.maxBudget && finalPrice > intent.maxBudget) {
        finalPrice = intent.maxBudget;
      }

      let address = restData.address || `${intent.city}, India`;
      if (!address.toLowerCase().includes(intent.city.toLowerCase())) {
        address = `${address}, ${intent.city}`;
      }

      const restaurant: Restaurant = {
        id: restData.id || `rest_${Date.now()}`,
        name: restData.name || intent.restaurantName || `Top-Rated Outlet in ${intent.city}`,
        slug: restData.slug || 'swiggy-outlet',
        rating: typeof restData.rating === 'number' ? restData.rating : 4.6,
        ratingCount: typeof restData.ratingCount === 'number' ? restData.ratingCount : 12000,
        deliveryTimeMinutes:
          typeof restData.deliveryTimeMinutes === 'number' ? restData.deliveryTimeMinutes : 25,
        address,
        city: intent.city,
        cuisines: Array.isArray(restData.cuisines) ? restData.cuisines : ['Specialties'],
        coverImage: image,
        menu: [],
      };

      const item: MenuItem = {
        id: itemData.id || `item_${Date.now()}`,
        name: itemName,
        price: finalPrice,
        rating: typeof itemData.rating === 'number' ? itemData.rating : 4.7,
        ratingCount: typeof itemData.ratingCount === 'number' ? itemData.ratingCount : 3800,
        description:
          itemData.description ||
          `Freshly prepared authentic ${intent.queryItem} with premium ingredients.`,
        isVeg: typeof itemData.isVeg === 'boolean' ? itemData.isVeg : intent.dietaryPreference !== 'non-veg',
        popular: true,
        category: itemData.category || 'Specialties',
        image,
      };

      restaurant.menu = [item];

      return {
        restaurant,
        item,
        matchScore: 98,
        reason:
          parsed.reason ||
          `Found authentic ${item.name} (₹${item.price}) at ${restaurant.name} with ⭐${item.rating} rating in ${intent.city}.`,
      };
    } catch {
      clearTimeout(timeout);
      return null;
    }
  }

  private findLocally(intent: FoodIntent): RecommendationResult | null {
    let targetRestaurants = this.searchRestaurants(intent.restaurantName, intent.cuisine, intent.city);

    if (intent.restaurantName && targetRestaurants.length === 0) {
      targetRestaurants = [this.createDynamicRestaurant(intent.restaurantName, intent.queryItem, intent.city)];
    }

    const queryTokens = intent.queryItem
      .toLowerCase()
      .split(/\s+/)
      .filter((t) => t.length > 1 && !['the', 'and', 'for', 'with', 'from', 'get', 'me', 'order'].includes(t));

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
      targetRestaurants[0] ||
      this.createDynamicRestaurant(intent.restaurantName || 'Popular Kitchen', intent.queryItem, intent.city);

    const price = this.estimatePriceForQuery(intent.queryItem, fallbackRestaurant.name, intent.maxBudget);
    const image = getFoodImage(intent.queryItem);

    const dynamicItem: MenuItem = {
      id: `dyn_${Date.now()}`,
      name: this.capitalizeWords(intent.queryItem),
      price,
      rating: 4.7,
      ratingCount: 15400,
      description: `Freshly prepared delicious ${intent.queryItem} with authentic ingredients in ${intent.city}.`,
      isVeg: intent.dietaryPreference !== 'non-veg',
      popular: true,
      category: 'Specials',
      image,
    };

    return {
      restaurant: fallbackRestaurant,
      item: dynamicItem,
      matchScore: 90,
      reason: `Found top-rated match: ${dynamicItem.name} (₹${dynamicItem.price}) at ${fallbackRestaurant.name}`,
    };
  }

  private estimatePriceForQuery(queryItem: string, restaurantName?: string | null, maxBudget?: number): number {
    const base = this.getCategoryBasePrice(queryItem, restaurantName);
    if (maxBudget && maxBudget > 0) {
      return Math.min(base, maxBudget);
    }
    return base;
  }

  private getCategoryBasePrice(queryItem: string, restaurantName?: string | null): number {
    const q = queryItem.toLowerCase();
    const isPremium = restaurantName && /starbucks|blue tokai|third wave|smoke house|subko|paul/i.test(restaurantName);

    if (q.includes('cappuccino') || q.includes('flat white') || q.includes('latte') || q.includes('cortado')) {
      return isPremium ? 210 : 160;
    }
    if (q.includes('cold brew') || q.includes('iced coffee') || q.includes('frappe') || q.includes('frappuccino') || q.includes('cold coffee')) {
      return isPremium ? 210 : 185;
    }
    if (q.includes('espresso') || q.includes('americano') || q.includes('black coffee')) {
      return isPremium ? 160 : 120;
    }
    if (q.includes('chai') || q.includes('tea')) {
      return 65;
    }
    if (q.includes('shake') || q.includes('smoothie')) {
      return 190;
    }
    if (q.includes('biryani') || q.includes('rice')) {
      return q.includes('chicken') || q.includes('mutton') ? 320 : 260;
    }
    if (q.includes('pizza')) {
      return 299;
    }
    if (q.includes('burger')) {
      return q.includes('chicken') ? 220 : 175;
    }
    if (q.includes('sandwich') || q.includes('wrap') || q.includes('roll') || q.includes('shawarma')) {
      return 190;
    }
    if (q.includes('dosa') || q.includes('idli') || q.includes('vada')) {
      return 120;
    }
    if (q.includes('paneer') || q.includes('curry') || q.includes('dal') || q.includes('chicken')) {
      return 280;
    }
    if (q.includes('cake') || q.includes('pastry') || q.includes('brownie') || q.includes('dessert') || q.includes('ice cream') || q.includes('croissant')) {
      return 160;
    }
    return 210;
  }

  private createDynamicRestaurant(name: string, queryItem: string, city: string = 'Bengaluru'): Restaurant {
    const slug = name
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/(^-|-$)/g, '');
    return {
      id: `rest_${slug}_${city.toLowerCase().replace(/[^a-z0-9]+/g, '_')}`,
      name: this.capitalizeWords(name),
      slug: `${slug}-${city.toLowerCase().replace(/[^a-z0-9]+/g, '-')}`,
      rating: 4.6,
      ratingCount: 28000,
      deliveryTimeMinutes: 25,
      address: `${this.capitalizeWords(name)} — City Center, ${city}`,
      city,
      cuisines: ['Indian', 'Specialties'],
      coverImage: getFoodImage(queryItem),
      menu: [],
    };
  }

  private capitalizeWords(str: string): string {
    return str
      .split(' ')
      .map((w) => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
      .join(' ');
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
