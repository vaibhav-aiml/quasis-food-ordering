import { EventEmitter } from 'events';
import { nanoid } from 'nanoid';
import { SwiggySearchService } from '../tools/swiggy/searchService.js';
import {
  DeepLinkResponse,
  FoodIntent,
  MenuItem,
  PipelineEvent,
  PipelineState,
  PipelineStage,
  Restaurant,
} from '../tools/swiggy/types.js';
import { IntentExtractor } from './intentExtractor.js';

export class PipelineOrchestrator {
  private sessions: Map<string, PipelineState> = new Map();
  private eventEmitters: Map<string, EventEmitter> = new Map();
  private eventHistory: Map<string, PipelineEvent[]> = new Map();
  private searchService: SwiggySearchService;

  constructor(searchService?: SwiggySearchService) {
    this.searchService = searchService || new SwiggySearchService();
  }

  public createSession(prompt: string, customSessionId?: string): string {
    const sessionId = customSessionId || `session_${nanoid(10)}`;
    const now = Date.now();

    const initialState: PipelineState = {
      sessionId,
      stage: 'PARSING_INTENT',
      prompt,
      createdAt: now,
      updatedAt: now,
      logs: [`Pipeline initialized for prompt: "${prompt}"`],
    };

    this.sessions.set(sessionId, initialState);
    this.eventEmitters.set(sessionId, new EventEmitter());
    this.eventHistory.set(sessionId, []);

    // Start asynchronous pipeline execution
    this.executePipeline(sessionId, prompt).catch((err) => {
      this.emitEvent(sessionId, 'FAILED', 'failed', `Pipeline execution error: ${err.message}`, {
        error: err.message,
      });
    });

    return sessionId;
  }

  public getSessionState(sessionId: string): PipelineState | undefined {
    return this.sessions.get(sessionId);
  }

  public getSessionEvents(sessionId: string): PipelineEvent[] {
    return this.eventHistory.get(sessionId) || [];
  }

  public subscribe(sessionId: string, listener: (event: PipelineEvent) => void): () => void {
    const emitter = this.eventEmitters.get(sessionId);
    if (!emitter) {
      // Create emitter if not already present
      const newEmitter = new EventEmitter();
      this.eventEmitters.set(sessionId, newEmitter);
      newEmitter.on('event', listener);
      return () => newEmitter.off('event', listener);
    }

    emitter.on('event', listener);
    return () => emitter.off('event', listener);
  }

  private emitEvent(
    sessionId: string,
    stage: PipelineStage,
    status: 'in_progress' | 'completed' | 'failed',
    message: string,
    data?: PipelineEvent['data']
  ): PipelineEvent {
    const session = this.sessions.get(sessionId);
    const timestamp = Date.now();

    if (session) {
      session.stage = stage;
      session.updatedAt = timestamp;
      session.logs.push(`[${new Date(timestamp).toISOString()}] [${stage}] ${message}`);
    }

    const event: PipelineEvent = {
      sessionId,
      stage,
      status,
      message,
      timestamp,
      data,
    };

    const history = this.eventHistory.get(sessionId) || [];
    history.push(event);
    this.eventHistory.set(sessionId, history);

    const emitter = this.eventEmitters.get(sessionId);
    if (emitter) {
      emitter.emit('event', event);
    }

    return event;
  }

  private async sleep(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  private async executePipeline(sessionId: string, prompt: string): Promise<void> {
    const session = this.sessions.get(sessionId);
    if (!session) return;

    // --- STAGE 1: Intent Extraction ---
    this.emitEvent(
      sessionId,
      'PARSING_INTENT',
      'in_progress',
      'Parsing natural language intent and budget constraints...',
      {}
    );

    await this.sleep(400);

    const intent: FoodIntent = await IntentExtractor.extract(prompt);
    session.intent = intent;

    this.emitEvent(
      sessionId,
      'PARSING_INTENT',
      'completed',
      `Extracted: "${intent.queryItem}"${
        intent.maxBudget ? ` | Budget: ≤ ₹${intent.maxBudget}` : ''
      }${intent.restaurantName ? ` | Restaurant: ${intent.restaurantName}` : ''}${
        intent.dietaryPreference !== 'any' ? ` | Pref: ${intent.dietaryPreference}` : ''
      }`,
      { intent }
    );

    // --- STAGE 2: Restaurant & Menu Search ---
    this.emitEvent(
      sessionId,
      'SEARCHING_RESTAURANTS',
      'in_progress',
      intent.restaurantName
        ? `Locating restaurant: ${intent.restaurantName}...`
        : 'Searching top-rated restaurants on Swiggy...',
      { intent }
    );

    await this.sleep(500);

    const matchedRestaurants = this.searchService.searchRestaurants(
      intent.restaurantName,
      intent.cuisine
    );
    session.restaurantsFound = matchedRestaurants.length;

    this.emitEvent(
      sessionId,
      'SEARCHING_RESTAURANTS',
      'completed',
      `Found ${matchedRestaurants.length} active Swiggy outlets matching criteria.`,
      {
        restaurantsCount: matchedRestaurants.length,
        matchedRestaurants: matchedRestaurants.slice(0, 5).map((r) => ({
          id: r.id,
          name: r.name,
          rating: r.rating,
        })),
      }
    );

    // --- STAGE 3: Filter Menu & Budget Matching ---
    this.emitEvent(
      sessionId,
      'FILTERING_MENU',
      'in_progress',
      `Scanning menu catalogs and filtering items${
        intent.maxBudget ? ` with price <= ₹${intent.maxBudget}` : ''
      }...`,
      {}
    );

    await this.sleep(450);

    const bestResult = this.searchService.findBestRecommendation(intent);

    if (!bestResult) {
      session.stage = 'FAILED';
      session.error = `No items found matching "${intent.queryItem}" within ₹${intent.maxBudget ?? 'specified criteria'}.`;
      this.emitEvent(
        sessionId,
        'FAILED',
        'failed',
        `No qualifying items found within budget ₹${intent.maxBudget ?? 'any'}.`,
        { error: session.error }
      );
      return;
    }

    session.recommendedItem = bestResult.item;
    session.recommendedRestaurant = bestResult.restaurant;

    const { deepLink, webUrl } = this.searchService.generateDeepLinks(
      bestResult.restaurant,
      bestResult.item
    );
    session.deepLink = deepLink;
    session.webUrl = webUrl;

    this.emitEvent(
      sessionId,
      'FILTERING_MENU',
      'completed',
      `Selected best match: ${bestResult.item.name} (₹${bestResult.item.price}) at ${bestResult.restaurant.name}`,
      {
        recommendation: {
          item: bestResult.item,
          restaurant: {
            id: bestResult.restaurant.id,
            name: bestResult.restaurant.name,
            slug: bestResult.restaurant.slug,
            rating: bestResult.restaurant.rating,
            ratingCount: bestResult.restaurant.ratingCount,
            deliveryTimeMinutes: bestResult.restaurant.deliveryTimeMinutes,
            address: bestResult.restaurant.address,
            cuisines: bestResult.restaurant.cuisines,
            coverImage: bestResult.restaurant.coverImage,
          },
        },
      }
    );

    // --- STAGE 4: Human-In-The-Loop Approval Card Presentation ---
    this.emitEvent(
      sessionId,
      'AWAITING_APPROVAL',
      'completed',
      'Recommendation ready. Awaiting user approval to open Swiggy app.',
      {
        recommendation: {
          item: bestResult.item,
          restaurant: {
            id: bestResult.restaurant.id,
            name: bestResult.restaurant.name,
            slug: bestResult.restaurant.slug,
            rating: bestResult.restaurant.rating,
            ratingCount: bestResult.restaurant.ratingCount,
            deliveryTimeMinutes: bestResult.restaurant.deliveryTimeMinutes,
            address: bestResult.restaurant.address,
            cuisines: bestResult.restaurant.cuisines,
            coverImage: bestResult.restaurant.coverImage,
          },
        },
        deepLink,
        webUrl,
      }
    );
  }

  /**
   * Approves the proposed recommendation and produces the final Swiggy deep links
   */
  public async approveOrder(
    sessionId: string,
    approved: boolean,
    selectedItemId?: string
  ): Promise<DeepLinkResponse> {
    const session = this.sessions.get(sessionId);
    if (!session) {
      throw new Error(`Session ${sessionId} not found`);
    }

    if (!session.recommendedItem || !session.recommendedRestaurant) {
      throw new Error(`No recommendation available for session ${sessionId}`);
    }

    let targetItem = session.recommendedItem;
    if (selectedItemId && selectedItemId !== targetItem.id) {
      const found = session.recommendedRestaurant.menu.find((m) => m.id === selectedItemId);
      if (found) {
        targetItem = found;
        session.recommendedItem = found;
      }
    }

    const { deepLink, webUrl } = this.searchService.generateDeepLinks(
      session.recommendedRestaurant,
      targetItem
    );

    session.deepLink = deepLink;
    session.webUrl = webUrl;
    session.approved = approved;

    if (approved) {
      session.stage = 'COMPLETED';
      this.emitEvent(
        sessionId,
        'COMPLETED',
        'completed',
        `Order approved! Dispatching deep link to Swiggy app: ${targetItem.name} at ${session.recommendedRestaurant.name}`,
        {
          deepLink,
          webUrl,
          recommendation: {
            item: targetItem,
            restaurant: {
              id: session.recommendedRestaurant.id,
              name: session.recommendedRestaurant.name,
              slug: session.recommendedRestaurant.slug,
              rating: session.recommendedRestaurant.rating,
              ratingCount: session.recommendedRestaurant.ratingCount,
              deliveryTimeMinutes: session.recommendedRestaurant.deliveryTimeMinutes,
              address: session.recommendedRestaurant.address,
              cuisines: session.recommendedRestaurant.cuisines,
              coverImage: session.recommendedRestaurant.coverImage,
            },
          },
        }
      );
    } else {
      session.stage = 'FAILED';
      this.emitEvent(sessionId, 'FAILED', 'failed', 'User declined recommendation.', {});
    }

    return {
      success: approved,
      sessionId,
      deepLink,
      webUrl,
      item: targetItem,
      restaurant: {
        id: session.recommendedRestaurant.id,
        name: session.recommendedRestaurant.name,
        slug: session.recommendedRestaurant.slug,
        rating: session.recommendedRestaurant.rating,
        ratingCount: session.recommendedRestaurant.ratingCount,
        deliveryTimeMinutes: session.recommendedRestaurant.deliveryTimeMinutes,
        address: session.recommendedRestaurant.address,
        cuisines: session.recommendedRestaurant.cuisines,
        coverImage: session.recommendedRestaurant.coverImage,
      },
      message: approved ? 'Swiggy deep link generated successfully.' : 'Order proposal was rejected.',
    };
  }
}
