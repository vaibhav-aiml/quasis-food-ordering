/**
 * Semantic Food & Beverage Image Engine
 * Maps culinary search queries, dish names, categories, and descriptions to
 * curated, ultra-high-quality authentic food photography from Unsplash.
 */

interface FoodImageMapping {
  keywords: string[];
  imageUrl: string;
}

const FOOD_IMAGE_CATALOG: FoodImageMapping[] = [
  // --- Coffee & Hot Beverages ---
  {
    keywords: ['cappuccino', 'flat white', 'cortado', 'latte art'],
    imageUrl: 'https://images.unsplash.com/photo-1572442388796-11668a67e53d?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['iced latte', 'latte', 'vanilla latte', 'caramel latte', 'hazelnut latte'],
    imageUrl: 'https://images.unsplash.com/photo-1517256064527-09c73fc73e38?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['cold coffee', 'cold brew', 'iced coffee', 'vietnamese cold coffee', 'shakerato'],
    imageUrl: 'https://images.unsplash.com/photo-1461023058943-07fcbe16d735?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['espresso', 'americano', 'black coffee', 'long black', 'ristretto', 'macchiato', 'doppio'],
    imageUrl: 'https://images.unsplash.com/photo-1514432324607-a09d9b4aefdd?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['mocha', 'hot chocolate', 'cacao', 'chocolate drink'],
    imageUrl: 'https://images.unsplash.com/photo-1542990253-0d0f5be5f0ed?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['frappe', 'frappuccino', 'java chip', 'blended coffee'],
    imageUrl: 'https://images.unsplash.com/photo-1572490122747-3968b75cc699?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['coffee', 'filter coffee', 'kaapi'],
    imageUrl: 'https://images.unsplash.com/photo-1517256064527-09c73fc73e38?auto=format&fit=crop&w=600&q=80',
  },

  // --- Tea & Chai ---
  {
    keywords: ['chai', 'masala chai', 'ginger chai', 'adrak chai', 'elaichi chai', 'cutting chai', 'milk tea', 'karak'],
    imageUrl: 'https://images.unsplash.com/photo-1576092768241-dec231879fc3?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['green tea', 'lemon tea', 'iced tea', 'herbal tea', 'black tea', 'earl grey', 'jasmine tea'],
    imageUrl: 'https://images.unsplash.com/photo-1556679343-c7306c1976bc?auto=format&fit=crop&w=600&q=80',
  },

  // --- Cold Drinks, Shakes & Juices ---
  {
    keywords: ['milkshake', 'thick shake', 'oreo shake', 'chocolate shake', 'kitkat shake', 'strawberry shake', 'shake'],
    imageUrl: 'https://images.unsplash.com/photo-1572490122747-3968b75cc699?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['smoothie', 'mango smoothie', 'berry smoothie', 'smoothie bowl'],
    imageUrl: 'https://images.unsplash.com/photo-1505252585461-04db1eb84625?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['juice', 'fresh juice', 'orange juice', 'watermelon juice', 'mango juice', 'sugarcane'],
    imageUrl: 'https://images.unsplash.com/photo-1613478223719-2ab802602423?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['lassi', 'sweet lassi', 'mango lassi', 'chaas', 'buttermilk'],
    imageUrl: 'https://images.unsplash.com/photo-1626082927389-6cd097cdc6ec?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['mojito', 'mocktail', 'virgin mojito', 'lemonade', 'cooler', 'soda'],
    imageUrl: 'https://images.unsplash.com/photo-1513558161293-cdaf765ed2fd?auto=format&fit=crop&w=600&q=80',
  },

  // --- Pizzas & Breads ---
  {
    keywords: ['margherita', 'cheese pizza', 'farmhouse', 'veg pizza', 'mushroom pizza'],
    imageUrl: 'https://images.unsplash.com/photo-1534308983496-4fabb1a015ee?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['peppy paneer', 'paneer pizza'],
    imageUrl: 'https://images.unsplash.com/photo-1574071318508-1cdbab80d002?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['pepperoni', 'chicken pizza', 'barbecue chicken pizza', 'meat pizza', 'non veg pizza'],
    imageUrl: 'https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['pizza'],
    imageUrl: 'https://images.unsplash.com/photo-1513104890138-7c749659a591?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['garlic bread', 'cheese garlic bread', 'stuffed garlic bread', 'breadsticks'],
    imageUrl: 'https://images.unsplash.com/photo-1619535860434-ba1d8fa12536?auto=format&fit=crop&w=600&q=80',
  },

  // --- Burgers & Sandwiches ---
  {
    keywords: ['chicken burger', 'crispy chicken burger', 'zinger', 'whopper chicken', 'non veg burger'],
    imageUrl: 'https://images.unsplash.com/photo-1568901346375-23c9450c58cd?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['burger', 'cheeseburger', 'veg burger', 'aloo tikki burger', 'whopper'],
    imageUrl: 'https://images.unsplash.com/photo-1550547660-d9450f859349?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['sandwich', 'club sandwich', 'grilled sandwich', 'cheese toast', 'panini', 'subway', 'sub'],
    imageUrl: 'https://images.unsplash.com/photo-1528735602780-2552fd46c7af?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['wrap', 'kathi roll', 'shawarma', 'chicken roll', 'paneer roll', 'roll', 'frankie', 'burrito'],
    imageUrl: 'https://images.unsplash.com/photo-1626700051175-6818013e1d4f?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['taco', 'quesadilla'],
    imageUrl: 'https://images.unsplash.com/photo-1551504734-5ee1c4a1479b?auto=format&fit=crop&w=600&q=80',
  },

  // --- Biryanis & Rice ---
  {
    keywords: ['chicken biryani', 'mutton biryani', 'dum biryani', 'hyderabadi biryani', 'andhra biryani', 'meghana biryani'],
    imageUrl: 'https://images.unsplash.com/photo-1563379091339-03b21ab4a4f8?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['veg biryani', 'paneer biryani', 'pulao', 'jeera rice', 'curd rice', 'khichdi'],
    imageUrl: 'https://images.unsplash.com/photo-1642821373181-696a54913e93?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['biryani', 'rice'],
    imageUrl: 'https://images.unsplash.com/photo-1563379091339-03b21ab4a4f8?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['fried rice', 'schezwan fried rice', 'egg fried rice', 'chicken fried rice'],
    imageUrl: 'https://images.unsplash.com/photo-1603133872878-684f208fb84b?auto=format&fit=crop&w=600&q=80',
  },

  // --- Indian Curries & Gravies ---
  {
    keywords: ['paneer butter masala', 'shahi paneer', 'kadhai paneer', 'palak paneer', 'matar paneer', 'paneer tikka', 'paneer'],
    imageUrl: 'https://images.unsplash.com/photo-1631452180519-c014fe946bc7?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['butter chicken', 'chicken tikka masala', 'chicken curry', 'mutton curry', 'rogan josh', 'korma'],
    imageUrl: 'https://images.unsplash.com/photo-1603894584373-5ac82b2ae398?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['dal makhani', 'dal tadka', 'dal', 'chole', 'rajma', 'chana masala'],
    imageUrl: 'https://images.unsplash.com/photo-1546833999-b9f581a1996d?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['naan', 'butter naan', 'garlic naan', 'roti', 'tandoori roti', 'paratha', 'kulcha', 'laccha paratha'],
    imageUrl: 'https://images.unsplash.com/photo-1626074353765-517a681e40be?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['chole bhature', 'bhatura', 'poori bhaji', 'puri'],
    imageUrl: 'https://images.unsplash.com/photo-1626132647523-66f5bf380027?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['samosa', 'kachori', 'pakora', 'bhajiya'],
    imageUrl: 'https://images.unsplash.com/photo-1601050690597-df0568f70950?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['pani puri', 'gol gappe', 'sev puri', 'bhel puri', 'chaat', 'papdi chaat', 'dahi bhalla'],
    imageUrl: 'https://images.unsplash.com/photo-1606491956689-2ea866880c84?auto=format&fit=crop&w=600&q=80',
  },

  // --- South Indian ---
  {
    keywords: ['dosa', 'masala dosa', 'mysore masala dosa', 'plain dosa', 'ghee roast', 'uttapam', 'paper dosa'],
    imageUrl: 'https://images.unsplash.com/photo-1668236543090-82eba5ee5976?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['idli', 'vada', 'medu vada', 'idli sambar', 'sambar vada'],
    imageUrl: 'https://images.unsplash.com/photo-1589301760014-d929f3979dbc?auto=format&fit=crop&w=600&q=80',
  },

  // --- Italian & Continental Pastas ---
  {
    keywords: ['alfredo', 'white sauce pasta', 'carbonara', 'creamy pasta'],
    imageUrl: 'https://images.unsplash.com/photo-1645112411341-6c4fd023714a?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['pasta', 'arrabbiata', 'red sauce pasta', 'penne arrabiata', 'lasagna', 'spaghetti'],
    imageUrl: 'https://images.unsplash.com/photo-1621996346565-e3d5d6281220?auto=format&fit=crop&w=600&q=80',
  },

  // --- Chinese & Asian ---
  {
    keywords: ['noodles', 'hakka noodles', 'chow mein', 'ramen', 'pad thai', 'schezwan noodles', 'udon'],
    imageUrl: 'https://images.unsplash.com/photo-1612927601601-6638404737ce?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['momos', 'dim sum', 'dumplings', 'steamed momos', 'fried momos', 'kurkure momos', 'bao'],
    imageUrl: 'https://images.unsplash.com/photo-1534422298391-e4f8c172dddb?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['manchurian', 'chilli chicken', 'chilli paneer', 'crispy corn', 'spring roll'],
    imageUrl: 'https://images.unsplash.com/photo-1569718212165-3a8278d5f624?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['sushi', 'california roll', 'sashimi'],
    imageUrl: 'https://images.unsplash.com/photo-1579871494447-9811cf80d66c?auto=format&fit=crop&w=600&q=80',
  },

  // --- Snacks, Sides & Fast Food ---
  {
    keywords: ['french fries', 'fries', 'peri peri fries', 'potato wedges'],
    imageUrl: 'https://images.unsplash.com/photo-1576107232684-1279f3908594?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['chicken wings', 'hot wings', 'bbq wings', 'nuggets', 'chicken tenders', 'fried chicken', 'popcorn chicken'],
    imageUrl: 'https://images.unsplash.com/photo-1567620832903-9fc6debc209f?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['nachos', 'tortilla chips'],
    imageUrl: 'https://images.unsplash.com/photo-1513456852971-30c0b8199d4d?auto=format&fit=crop&w=600&q=80',
  },

  // --- Bakery, Desserts & Sweets ---
  {
    keywords: ['croissant', 'almond croissant', 'butter croissant', 'pain au chocolat', 'danish', 'bagel', 'donut', 'doughnut'],
    imageUrl: 'https://images.unsplash.com/photo-1555507036-ab1f4038808a?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['brownie', 'sizzling brownie', 'choco lava cake', 'lava cake', 'fudge'],
    imageUrl: 'https://images.unsplash.com/photo-1606313564200-e75d5e30476c?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['cake', 'pastry', 'cheesecake', 'red velvet', 'black forest', 'chocolate cake', 'truffle cake'],
    imageUrl: 'https://images.unsplash.com/photo-1578985545062-69928b1d9587?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['ice cream', 'sundae', 'gelato', 'belgian chocolate', 'vanilla ice cream'],
    imageUrl: 'https://images.unsplash.com/photo-1501443762994-82bd5dace89a?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['waffle', 'pancake', 'crepe', 'belgian waffle'],
    imageUrl: 'https://images.unsplash.com/photo-1562376552-0d160a2f238d?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['gulab jamun', 'rasgulla', 'rasmalai', 'jalebi', 'kaju katli', 'kulfi', 'halwa', 'mithai', 'sweets'],
    imageUrl: 'https://images.unsplash.com/photo-1601050690117-94f5f6fa8bd7?auto=format&fit=crop&w=600&q=80',
  },

  // --- Salads & Soups ---
  {
    keywords: ['salad', 'caesar salad', 'greek salad', 'fruit salad'],
    imageUrl: 'https://images.unsplash.com/photo-1512621776951-a57141f2eefd?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['soup', 'tomato soup', 'manchow soup', 'hot and sour soup', 'sweet corn soup', 'ramen soup'],
    imageUrl: 'https://images.unsplash.com/photo-1547592166-23ac45744acd?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['poke bowl', 'meal bowl', 'healthy bowl', 'buddha bowl'],
    imageUrl: 'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?auto=format&fit=crop&w=600&q=80',
  },
];

export function getFoodImage(queryItem: string, category?: string, description?: string): string {
  const text = `${queryItem} ${category || ''} ${description || ''}`.toLowerCase();

  // 1. Direct Multi-word keyword matches (scored by specificity)
  let bestMatchUrl: string | null = null;
  let highestScore = 0;

  for (const entry of FOOD_IMAGE_CATALOG) {
    for (const kw of entry.keywords) {
      if (text.includes(kw)) {
        // Longer keyword matches get higher score for precision (e.g. 'iced latte' > 'latte')
        const score = kw.length * 10;
        if (score > highestScore) {
          highestScore = score;
          bestMatchUrl = entry.imageUrl;
        }
      }
    }
  }

  if (bestMatchUrl) {
    return bestMatchUrl;
  }

  // 2. Tokenized word overlap fallback
  const tokens = queryItem
    .toLowerCase()
    .split(/[^a-z0-9]+/)
    .filter((t) => t.length > 2);

  for (const entry of FOOD_IMAGE_CATALOG) {
    for (const kw of entry.keywords) {
      const kwTokens = kw.split(/\s+/);
      const overlap = tokens.filter((t) => kwTokens.includes(t)).length;
      if (overlap > 0 && overlap * 5 > highestScore) {
        highestScore = overlap * 5;
        bestMatchUrl = entry.imageUrl;
      }
    }
  }

  if (bestMatchUrl) {
    return bestMatchUrl;
  }

  // 3. Fallback to appetizing hot meal platter
  return 'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?auto=format&fit=crop&w=600&q=80';
}
