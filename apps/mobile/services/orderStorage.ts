import AsyncStorage from '@react-native-async-storage/async-storage';
import { Platform } from 'react-native';

export interface StoredOrder {
  id: string;
  sessionId: string;
  timestamp: number;
  formattedDate: string;
  prompt: string;
  restaurant: {
    id: string;
    name: string;
    rating: number;
    deliveryTimeMinutes: number;
    address: string;
    coverImage?: string;
  };
  item: {
    id: string;
    name: string;
    price: number;
    isVeg: boolean;
    category?: string;
    image?: string;
    description?: string;
  };
  deepLink: string;
  webUrl: string;
  isFavorite: boolean;
  status: 'DISPATCHED' | 'SAVED';
}

export type NewOrderInput = Omit<
  StoredOrder,
  'id' | 'timestamp' | 'formattedDate' | 'isFavorite'
> & {
  isFavorite?: boolean;
};

const STORAGE_KEY = '@quasis_order_history_v1';
const MAX_ORDERS = 50; // Cap storage size to prevent unbounded memory/disk growth

// Resilient key-value in-memory fallback store if native AsyncStorage or localStorage is unavailable
const memoryStore = new Map<string, string>();

const withTimeout = <T>(promise: Promise<T>, ms: number, fallback: T): Promise<T> => {
  return Promise.race([
    promise,
    new Promise<T>((resolve) => setTimeout(() => resolve(fallback), ms)),
  ]);
};

export const StorageAdapter = {
  async getItem(key: string): Promise<string | null> {
    try {
      if (Platform.OS === 'web' && typeof window !== 'undefined' && window.localStorage) {
        return window.localStorage.getItem(key);
      }
      const val = await withTimeout(AsyncStorage.getItem(key), 500, null);
      return val ?? memoryStore.get(key) ?? null;
    } catch {
      return memoryStore.get(key) ?? null;
    }
  },

  async setItem(key: string, value: string): Promise<void> {
    memoryStore.set(key, value);
    try {
      if (Platform.OS === 'web' && typeof window !== 'undefined' && window.localStorage) {
        window.localStorage.setItem(key, value);
        return;
      }
      await withTimeout(AsyncStorage.setItem(key, value), 500, undefined);
    } catch {
      // In-memory fallback already populated
    }
  },

  async removeItem(key: string): Promise<void> {
    memoryStore.delete(key);
    try {
      if (Platform.OS === 'web' && typeof window !== 'undefined' && window.localStorage) {
        window.localStorage.removeItem(key);
        return;
      }
      await withTimeout(AsyncStorage.removeItem(key), 500, undefined);
    } catch {
      // In-memory fallback already cleared
    }
  },
};

function formatDate(ts: number): string {
  const date = new Date(ts);
  return date.toLocaleDateString('en-IN', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export const OrderStorage = {
  /**
   * Retrieves all saved orders ordered by most recent first.
   */
  async getOrders(): Promise<StoredOrder[]> {
    try {
      const raw = await StorageAdapter.getItem(STORAGE_KEY);
      if (!raw) return [];
      const parsed: StoredOrder[] = JSON.parse(raw);
      return Array.isArray(parsed) ? parsed : [];
    } catch (err) {
      console.warn('Failed to load order history:', err);
      return [];
    }
  },

  /**
   * Saves a new completed or dispatched order, pruning older non-favorite entries if over capacity.
   */
  async saveOrder(input: NewOrderInput): Promise<StoredOrder> {
    const existing = await this.getOrders();
    const timestamp = Date.now();
    const id = `order_${timestamp}_${Math.random().toString(36).slice(2, 7)}`;

    const newOrder: StoredOrder = {
      ...input,
      id,
      timestamp,
      formattedDate: formatDate(timestamp),
      isFavorite: !!input.isFavorite,
    };

    // Avoid duplicate entry for same sessionId
    const filtered = existing.filter((o) => o.sessionId !== input.sessionId);
    let updated = [newOrder, ...filtered];

    // Prune if over MAX_ORDERS (prefer keeping favorites)
    if (updated.length > MAX_ORDERS) {
      const favorites = updated.filter((o) => o.isFavorite);
      const nonFavorites = updated.filter((o) => !o.isFavorite);
      const allowedNonFavorites = MAX_ORDERS - favorites.length;

      if (allowedNonFavorites > 0) {
        updated = [...favorites, ...nonFavorites.slice(0, allowedNonFavorites)].sort(
          (a, b) => b.timestamp - a.timestamp
        );
      } else {
        updated = favorites.slice(0, MAX_ORDERS);
      }
    }

    await StorageAdapter.setItem(STORAGE_KEY, JSON.stringify(updated));
    return newOrder;
  },

  /**
   * Toggles the favorite status of an order.
   */
  async toggleFavorite(orderId: string): Promise<boolean> {
    const orders = await this.getOrders();
    let newStatus = false;
    const updated = orders.map((order) => {
      if (order.id === orderId) {
        newStatus = !order.isFavorite;
        return { ...order, isFavorite: newStatus };
      }
      return order;
    });

    await StorageAdapter.setItem(STORAGE_KEY, JSON.stringify(updated));
    return newStatus;
  },

  /**
   * Deletes an order by ID.
   */
  async deleteOrder(orderId: string): Promise<void> {
    const orders = await this.getOrders();
    const updated = orders.filter((order) => order.id !== orderId);
    await StorageAdapter.setItem(STORAGE_KEY, JSON.stringify(updated));
  },

  /**
   * Clears all order history.
   */
  async clearAllOrders(): Promise<void> {
    await StorageAdapter.removeItem(STORAGE_KEY);
  },

  /**
   * Returns only favorite orders.
   */
  async getFavorites(): Promise<StoredOrder[]> {
    const orders = await this.getOrders();
    return orders.filter((o) => o.isFavorite);
  },
};
