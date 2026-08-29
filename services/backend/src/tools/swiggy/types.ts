import { z } from 'zod';

export const DietaryPreferenceEnum = z.enum(['veg', 'non-veg', 'any']);
export type DietaryPreference = z.infer<typeof DietaryPreferenceEnum>;

export const FoodIntentSchema = z.object({
  queryItem: z.string().describe('Target food item or beverage, e.g. "cold coffee", "burger", "biryani"'),
  maxBudget: z.number().optional().describe('Maximum budget in INR, e.g. 200'),
  restaurantName: z.string().nullable().optional().describe('Specific restaurant name if mentioned, or null'),
  dietaryPreference: DietaryPreferenceEnum.optional().default('any').describe('Dietary filter preference'),
  cuisine: z.string().optional().describe('Cuisine type, e.g. "Continental", "Indian", "Beverages"'),
  notes: z.string().optional().describe('Special instructions or flavor notes'),
});

export type FoodIntent = z.infer<typeof FoodIntentSchema>;

export interface MenuItem {
  id: string;
  name: string;
  price: number;
  rating: number;
  ratingCount: number;
  description: string;
  isVeg: boolean;
  image: string;
  category: string;
  popular?: boolean;
}

export interface Restaurant {
  id: string;
  name: string;
  slug: string;
  rating: number;
  ratingCount: number;
  deliveryTimeMinutes: number;
  address: string;
  cuisines: string[];
  coverImage: string;
  menu: MenuItem[];
}

export type PipelineStage =
  | 'PARSING_INTENT'
  | 'SEARCHING_RESTAURANTS'
  | 'FILTERING_MENU'
  | 'AWAITING_APPROVAL'
  | 'APPROVED'
  | 'COMPLETED'
  | 'FAILED';

export interface PipelineEvent {
  sessionId: string;
  stage: PipelineStage;
  status: 'in_progress' | 'completed' | 'failed';
  message: string;
  timestamp: number;
  data?: {
    intent?: FoodIntent;
    restaurantsCount?: number;
    matchedRestaurants?: Array<{ id: string; name: string; rating: number }>;
    itemsEvaluated?: number;
    recommendation?: {
      item: MenuItem;
      restaurant: Omit<Restaurant, 'menu'>;
    };
    deepLink?: string;
    webUrl?: string;
    error?: string;
    [key: string]: any;
  };
}

export interface PipelineState {
  sessionId: string;
  stage: PipelineStage;
  prompt: string;
  createdAt: number;
  updatedAt: number;
  intent?: FoodIntent;
  restaurantsFound?: number;
  itemsEvaluated?: number;
  recommendedItem?: MenuItem;
  recommendedRestaurant?: Restaurant;
  deepLink?: string;
  webUrl?: string;
  approved?: boolean;
  error?: string;
  logs: string[];
}

export interface RecommendationResult {
  restaurant: Restaurant;
  item: MenuItem;
  matchScore: number;
  reason: string;
}

export interface ApprovalPayload {
  sessionId: string;
  approved: boolean;
  selectedItemId?: string;
}

export interface DeepLinkResponse {
  success: boolean;
  sessionId: string;
  deepLink: string;
  webUrl: string;
  item: MenuItem;
  restaurant: Omit<Restaurant, 'menu'>;
  message: string;
}
