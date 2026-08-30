import { describe, expect, it } from 'vitest';
import { IntentExtractor } from '../src/agent/intentExtractor.js';
import { PipelineOrchestrator } from '../src/agent/pipelineOrchestrator.js';
import { SwiggySearchService } from '../src/tools/swiggy/searchService.js';
import { FoodIntent } from '../src/tools/swiggy/types.js';

describe('1. IntentExtractor', () => {
  it('extracts food item, budget, and restaurant from natural language input', async () => {
    const prompt = 'Find the best-rated iced latte under 200';
    const intent = await IntentExtractor.extract(prompt);

    expect(intent.queryItem.toLowerCase()).toContain('latte');
    expect(intent.maxBudget).toBe(200);
  });

  it('extracts specific restaurant and budget correctly', async () => {
    const prompt = 'Order chicken burger from Truffles within 250 rs';
    const intent = await IntentExtractor.extract(prompt);

    expect(intent.restaurantName).toBe('Truffles');
    expect(intent.maxBudget).toBe(250);
    expect(intent.dietaryPreference).toBe('non-veg');
  });

  it('handles vegetarian preference flags', async () => {
    const prompt = 'Find pure veg cold coffee under 180 from Third Wave Coffee';
    const intent = await IntentExtractor.extract(prompt);

    expect(intent.restaurantName).toBe('Third Wave Coffee');
    expect(intent.maxBudget).toBe(180);
    expect(intent.dietaryPreference).toBe('veg');
  });
});

describe('2. SwiggySearchService', () => {
  const searchService = new SwiggySearchService();

  it('returns candidate restaurants matching name query', () => {
    const results = searchService.searchRestaurants('Third Wave Coffee');
    expect(results.length).toBeGreaterThan(0);
    expect(results[0].name).toBe('Third Wave Coffee');
  });

  it('filters items strictly within the budget limit', async () => {
    const intent: FoodIntent = {
      queryItem: 'cold coffee',
      city: 'Bengaluru',
      maxBudget: 190,
      restaurantName: null,
      dietaryPreference: 'any',
    };

    const recommendation = await searchService.findBestRecommendation(intent);
    expect(recommendation).toBeDefined();
    expect(recommendation!.item.price).toBeLessThanOrEqual(190);
  });

  it('ensures recommendation result has address and city matching intent.city', async () => {
    const intent: FoodIntent = {
      queryItem: 'sweet corn pizza',
      city: 'Jaipur',
      restaurantName: 'La Pinoz',
      dietaryPreference: 'any',
    };

    const recommendation = await searchService.findBestRecommendation(intent);
    expect(recommendation).toBeDefined();
    expect(recommendation!.restaurant.city).toBe('Jaipur');
    expect(recommendation!.restaurant.address.toLowerCase()).toContain('jaipur');
  });

  it('proves different cities produce distinct restaurant id and address for the same restaurantName and dish', async () => {
    const jaipurIntent: FoodIntent = {
      queryItem: 'sweet corn pizza',
      city: 'Jaipur',
      restaurantName: 'La Pinoz',
      dietaryPreference: 'any',
    };
    const mumbaiIntent: FoodIntent = {
      queryItem: 'sweet corn pizza',
      city: 'Mumbai',
      restaurantName: 'La Pinoz',
      dietaryPreference: 'any',
    };

    const jaipurResult = await searchService.findBestRecommendation(jaipurIntent);
    const mumbaiResult = await searchService.findBestRecommendation(mumbaiIntent);

    expect(jaipurResult).toBeDefined();
    expect(mumbaiResult).toBeDefined();
    expect(jaipurResult!.restaurant.id).not.toBe(mumbaiResult!.restaurant.id);
    expect(jaipurResult!.restaurant.address).not.toBe(mumbaiResult!.restaurant.address);
    expect(jaipurResult!.restaurant.address).toContain('Jaipur');
    expect(mumbaiResult!.restaurant.address).toContain('Mumbai');
  });

  it('generates valid Swiggy native deep links and web fallback URLs', () => {
    const rest = searchService.getRestaurants()[0];
    const item = rest.menu[0];
    const { deepLink, webUrl } = searchService.generateDeepLinks(rest, item);

    expect(deepLink).toContain('swiggy://');
    expect(webUrl).toContain('https://www.swiggy.com/restaurants/');
  });
});

describe('3. PipelineOrchestrator', () => {
  it('executes full pipeline and emits sequential stages', async () => {
    const orchestrator = new PipelineOrchestrator();
    const sessionId = orchestrator.createSession('Get me cold coffee under 200', 'Bengaluru');

    // Wait for pipeline stages to progress
    await new Promise((resolve) => setTimeout(resolve, 5000));

    const state = orchestrator.getSessionState(sessionId);
    expect(state).toBeDefined();
    expect(state?.stage).toBe('AWAITING_APPROVAL');
    expect(state?.city).toBe('Bengaluru');
    expect(state?.recommendedItem).toBeDefined();
    expect(state?.recommendedItem?.price).toBeLessThanOrEqual(200);

    // Approve the order
    const approvalResult = await orchestrator.approveOrder(sessionId, true);
    expect(approvalResult.success).toBe(true);
    expect(approvalResult.deepLink).toContain('swiggy://');

    const updatedState = orchestrator.getSessionState(sessionId);
    expect(updatedState?.stage).toBe('COMPLETED');
  });
});
