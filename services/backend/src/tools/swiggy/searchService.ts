import { FoodIntent, MenuItem, RecommendationResult, Restaurant } from './types.js';

export const SWIGGY_CATALOG: Restaurant[] = [
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
      {
        id: 'twc_item_03',
        name: 'Iced Spanish Latte',
        price: 210,
        rating: 4.6,
        ratingCount: 1540,
        description: 'Sweetened textured milk with a double shot of dark roast espresso over crushed ice.',
        isVeg: true,
        popular: false,
        category: 'Cold Brews & Iced Coffee',
        image: 'https://images.unsplash.com/photo-1553909489-cd47e0907980?auto=format&fit=crop&w=500&q=80',
      },
      {
        id: 'twc_item_04',
        name: 'Almond Croissant',
        price: 160,
        rating: 4.5,
        ratingCount: 890,
        description: 'Flaky buttery pastry filled with sweet almond frangipane and topped with toasted almonds.',
        isVeg: true,
        popular: false,
        category: 'Bakery',
        image: 'https://images.unsplash.com/photo-1555507036-ab1f4038808a?auto=format&fit=crop&w=500&q=80',
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
      {
        id: 'bt_item_02',
        name: 'Original Cold Brew Bottle (200ml)',
        price: 175,
        rating: 4.6,
        ratingCount: 3100,
        description: 'Steeped for 18 hours in cold filtered water. Zero bitterness, high caffeine kick.',
        isVeg: true,
        popular: true,
        category: 'Cold Brews',
        image: 'https://images.unsplash.com/photo-1517701550927-30cf4ba1dba5?auto=format&fit=crop&w=500&q=80',
      },
      {
        id: 'bt_item_03',
        name: 'Hazelnut Cold Coffee',
        price: 205,
        rating: 4.7,
        ratingCount: 1650,
        description: 'Cold espresso with creamy hazelnut syrup and farm fresh milk.',
        isVeg: true,
        popular: false,
        category: 'Iced Coffee',
        image: 'https://images.unsplash.com/photo-1461023058943-07fcbe16d735?auto=format&fit=crop&w=500&q=80',
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
    cuisines: ['American', 'Burgers', 'Fast Food', 'Beverages', 'Desserts'],
    coverImage: 'https://images.unsplash.com/photo-1550547660-d9450f859349?auto=format&fit=crop&w=600&q=80',
    menu: [
      {
        id: 'truf_item_01',
        name: 'All American Cheese Burger',
        price: 220,
        rating: 4.7,
        ratingCount: 18400,
        description: 'Juicy chicken patty grilled with melted cheddar cheese, caramelized onions, and house sauce.',
        isVeg: false,
        popular: true,
        category: 'Burgers',
        image: 'https://images.unsplash.com/photo-1568901346375-23c9450c58cd?auto=format&fit=crop&w=500&q=80',
      },
      {
        id: 'truf_item_02',
        name: 'Crunchy Veg Burger',
        price: 170,
        rating: 4.5,
        ratingCount: 9400,
        description: 'Crispy seasoned vegetable patty topped with lettuce, spicy mayo, and pickles.',
        isVeg: true,
        popular: true,
        category: 'Burgers',
        image: 'https://images.unsplash.com/photo-1520072959219-c595dc870360?auto=format&fit=crop&w=500&q=80',
      },
      {
        id: 'truf_item_03',
        name: 'Belgian Chocolate Milkshake',
        price: 195,
        rating: 4.6,
        ratingCount: 8200,
        description: 'Thick creamy milkshake made with real Belgian dark cocoa and vanilla ice cream.',
        isVeg: true,
        popular: true,
        category: 'Beverages',
        image: 'https://images.unsplash.com/photo-1572490122747-3968b75cc699?auto=format&fit=crop&w=500&q=80',
      },
      {
        id: 'truf_item_04',
        name: 'Truffles Thick Cold Coffee',
        price: 155,
        rating: 4.6,
        ratingCount: 6200,
        description: 'Creamy blended cold coffee crowned with chocolate syrup and cocoa powder.',
        isVeg: true,
        popular: true,
        category: 'Beverages',
        image: 'https://images.unsplash.com/photo-1517256064527-09c73fc73e38?auto=format&fit=crop&w=500&q=80',
      },
    ],
  },
  {
    id: 'rest_starbucks_104',
    name: 'Starbucks Coffee',
    slug: 'starbucks-coffee-church-street',
    rating: 4.4,
    ratingCount: 22000,
    deliveryTimeMinutes: 25,
    address: 'Church Street, Shanthala Nagar, Bengaluru',
    cuisines: ['Beverages', 'Cafe', 'Bakery', 'Coffee'],
    coverImage: 'https://images.unsplash.com/photo-1509042239860-f550ce710b93?auto=format&fit=crop&w=600&q=80',
    menu: [
      {
        id: 'sb_item_01',
        name: 'Signature Iced Caffe Latte (Tall)',
        price: 245,
        rating: 4.5,
        ratingCount: 4300,
        description: 'Our dark, rich espresso balanced with steamed milk and a light layer of foam over ice.',
        isVeg: true,
        popular: true,
        category: 'Cold Coffee',
        image: 'https://images.unsplash.com/photo-1517256064527-09c73fc73e38?auto=format&fit=crop&w=500&q=80',
      },
      {
        id: 'sb_item_02',
        name: 'Cold Brew Black (Tall)',
        price: 220,
        rating: 4.4,
        ratingCount: 2100,
        description: 'Handcrafted in small batches daily, slow-steeped in cool water for 20 hours.',
        isVeg: true,
        popular: false,
        category: 'Cold Brews',
        image: 'https://images.unsplash.com/photo-1517701550927-30cf4ba1dba5?auto=format&fit=crop&w=500&q=80',
      },
      {
        id: 'sb_item_03',
        name: 'Double Chocolate Chip Cookie',
        price: 185,
        rating: 4.3,
        ratingCount: 1200,
        description: 'Rich dark cookie loaded with Belgian chocolate chips and butter.',
        isVeg: true,
        popular: false,
        category: 'Bakery',
        image: 'https://images.unsplash.com/photo-1499636136210-6f4ee915583e?auto=format&fit=crop&w=500&q=80',
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
        image: 'https://images.unsplash.com/photo-1563379091339-03b21ab4a4f8?auto=format&fit=crop&w=500&q=80',
      },
      {
        id: 'mf_item_02',
        name: 'Paneer Biryani',
        price: 260,
        rating: 4.4,
        ratingCount: 9200,
        description: 'Fresh cottage cheese cubes marinated in Andhra spices served with flavored basmati rice.',
        isVeg: true,
        popular: true,
        category: 'Biryani',
        image: 'https://images.unsplash.com/photo-1589302168068-964664d93dc0?auto=format&fit=crop&w=500&q=80',
      },
      {
        id: 'mf_item_03',
        name: 'Lemon Chicken (Starter)',
        price: 290,
        rating: 4.5,
        ratingCount: 8100,
        description: 'Tender chicken tossed in tangy lemon seasoning, green chilies, and curry leaves.',
        isVeg: false,
        popular: false,
        category: 'Starters',
        image: 'https://images.unsplash.com/photo-1626082927389-6cd097cdc6ec?auto=format&fit=crop&w=500&q=80',
      },
    ],
  },
  {
    id: 'rest_california_burrito_106',
    name: 'California Burrito',
    slug: 'california-burrito-mg-road',
    rating: 4.5,
    ratingCount: 26000,
    deliveryTimeMinutes: 25,
    address: '1 MG-Lido Mall, Trinity Circle, Bengaluru',
    cuisines: ['Mexican', 'Salads', 'Healthy Food', 'Bowls'],
    coverImage: 'https://images.unsplash.com/photo-1565299585323-38d6b0865b47?auto=format&fit=crop&w=600&q=80',
    menu: [
      {
        id: 'cb_item_01',
        name: 'Crispy Mushroom Rice Bowl',
        price: 199,
        rating: 4.6,
        ratingCount: 4200,
        description: 'Cilantro lime rice with black beans, roasted salsa, crispy seasoned mushrooms, and sour cream.',
        isVeg: true,
        popular: true,
        category: 'Burrito Bowls',
        image: 'https://images.unsplash.com/photo-1543339308-43e59d6b73a6?auto=format&fit=crop&w=500&q=80',
      },
      {
        id: 'cb_item_02',
        name: 'Grilled Chicken Burrito',
        price: 239,
        rating: 4.6,
        ratingCount: 6800,
        description: 'Smoky grilled chicken wrapped in a warm flour tortilla with salsa, pinto beans, and jack cheese.',
        isVeg: false,
        popular: true,
        category: 'Burritos',
        image: 'https://images.unsplash.com/photo-1626700051175-6818013e1d4f?auto=format&fit=crop&w=500&q=80',
      },
      {
        id: 'cb_item_03',
        name: 'Nachos with Fresh Guacamole',
        price: 179,
        rating: 4.5,
        ratingCount: 3100,
        description: 'Warm crispy corn tortilla chips served with handcrafted Hass avocado guacamole.',
        isVeg: true,
        popular: false,
        category: 'Sides',
        image: 'https://images.unsplash.com/photo-1513456852971-30c0b8199d4d?auto=format&fit=crop&w=500&q=80',
      },
    ],
  },
  {
    id: 'rest_chai_point_107',
    name: 'Chai Point',
    slug: 'chai-point-indiranagar',
    rating: 4.4,
    ratingCount: 31000,
    deliveryTimeMinutes: 18,
    address: '12th Main Road, Indiranagar, Bengaluru',
    cuisines: ['Tea', 'Beverages', 'Fast Food', 'Snacks'],
    coverImage: 'https://images.unsplash.com/photo-1576092768241-dec231879fc3?auto=format&fit=crop&w=600&q=80',
    menu: [
      {
        id: 'cp_item_01',
        name: 'Iced Ginger Chai Latte',
        price: 130,
        rating: 4.5,
        ratingCount: 3900,
        description: 'Refreshing chilled milk tea infused with fresh crushed ginger and aromatic spices.',
        isVeg: true,
        popular: true,
        category: 'Iced Chai',
        image: 'https://images.unsplash.com/photo-1576092768241-dec231879fc3?auto=format&fit=crop&w=500&q=80',
      },
      {
        id: 'cp_item_02',
        name: 'Classic Cold Coffee Bottle',
        price: 145,
        rating: 4.5,
        ratingCount: 5200,
        description: 'Brewed robust chicory-coffee blend shaken with chilled sweet milk in a reusable flask.',
        isVeg: true,
        popular: true,
        category: 'Cold Coffee',
        image: 'https://images.unsplash.com/photo-1517256064527-09c73fc73e38?auto=format&fit=crop&w=500&q=80',
      },
      {
        id: 'cp_item_03',
        name: 'Bun Maska',
        price: 65,
        rating: 4.6,
        ratingCount: 7800,
        description: 'Soft warm bakery bun generously buttered with salted Amul butter.',
        isVeg: true,
        popular: true,
        category: 'Snacks',
        image: 'https://images.unsplash.com/photo-1509440159596-0249088772ff?auto=format&fit=crop&w=500&q=80',
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

  /**
   * Finds restaurants matching the search criteria or restaurant name
   */
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

    // Default to sorting by rating descending
    return results.sort((a, b) => b.rating - a.rating);
  }

  /**
   * Finds and ranks the best matching menu items given a FoodIntent
   */
  public findBestRecommendation(intent: FoodIntent): RecommendationResult | null {
    // 1. Determine candidate restaurants
    const targetRestaurants = this.searchRestaurants(intent.restaurantName, intent.cuisine);
    if (targetRestaurants.length === 0) {
      return null;
    }

    const queryTokens = intent.queryItem
      .toLowerCase()
      .split(/\s+/)
      .filter((t) => t.length > 1);

    const candidates: Array<{
      restaurant: Restaurant;
      item: MenuItem;
      score: number;
      reason: string;
    }> = [];

    let itemsEvaluatedCount = 0;

    for (const rest of targetRestaurants) {
      for (const item of rest.menu) {
        itemsEvaluatedCount++;

        // Budget filter check
        if (intent.maxBudget !== undefined && intent.maxBudget !== null && intent.maxBudget > 0) {
          if (item.price > intent.maxBudget) {
            continue; // Exceeds budget
          }
        }

        // Dietary preference filter check
        if (intent.dietaryPreference === 'veg' && !item.isVeg) {
          continue;
        }
        if (intent.dietaryPreference === 'non-veg' && item.isVeg) {
          // Allow or softly downrank if specifically non-veg requested
        }

        // Compute relevance match score
        const itemNameLower = item.name.toLowerCase();
        const itemDescLower = item.description.toLowerCase();
        const itemCatLower = item.category.toLowerCase();

        let tokenMatches = 0;
        for (const token of queryTokens) {
          if (itemNameLower.includes(token)) {
            tokenMatches += 3;
          } else if (itemCatLower.includes(token)) {
            tokenMatches += 2;
          } else if (itemDescLower.includes(token)) {
            tokenMatches += 1;
          }
        }

        // If query is specific and tokens don't match, downrank or skip
        if (queryTokens.length > 0 && tokenMatches === 0) {
          // Check if the restaurant matches cuisine/style
          if (!rest.cuisines.some((c) => queryTokens.some((t) => c.toLowerCase().includes(t)))) {
            continue;
          }
        }

        // Calculate score based on relevance, item rating, restaurant rating, popularity, and budget fit
        let score = (tokenMatches * 10) + (item.rating * 5) + (rest.rating * 3);
        if (item.popular) score += 4;

        // Give boost if within budget comfortably
        if (intent.maxBudget && intent.maxBudget > 0) {
          const budgetRatio = item.price / intent.maxBudget;
          if (budgetRatio <= 1.0) {
            score += 5; // Valid budget bonus
          }
        }

        const reason = `${item.name} (₹${item.price}) from ${rest.name} has a ⭐${item.rating} rating with ${item.ratingCount.toLocaleString()} reviews.`;

        candidates.push({
          restaurant: rest,
          item,
          score,
          reason,
        });
      }
    }

    if (candidates.length === 0) {
      // If strict filter yielded nothing, fallback to the top item under budget from the top restaurant
      for (const rest of targetRestaurants) {
        for (const item of rest.menu) {
          if (intent.maxBudget && item.price > intent.maxBudget) continue;
          if (intent.dietaryPreference === 'veg' && !item.isVeg) continue;
          return {
            restaurant: rest,
            item,
            matchScore: 50,
            reason: `Best available option within ₹${intent.maxBudget ?? 'budget'}: ${item.name} (₹${item.price}) at ${rest.name}`,
          };
        }
      }
      return null;
    }

    // Sort by highest score
    candidates.sort((a, b) => b.score - a.score);
    const best = candidates[0];

    return {
      restaurant: best.restaurant,
      item: best.item,
      matchScore: best.score,
      reason: best.reason,
    };
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
