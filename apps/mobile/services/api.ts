import { Platform } from 'react-native';
import Constants from 'expo-constants';

// Auto-detect computer's Wi-Fi IP address from Expo bundler hostUri
const getDevServerHost = () => {
  const debuggerHost =
    Constants.expoConfig?.hostUri ||
    (Constants as any).manifest2?.extra?.expoClient?.hostUri ||
    (Constants as any).manifest?.debuggerHost;

  if (debuggerHost) {
    const ip = debuggerHost.split(':')[0];
    if (ip && ip !== 'localhost' && ip !== '127.0.0.1') {
      return `http://${ip}:3001`;
    }
  }
  return Platform.OS === 'android' ? 'http://10.0.2.2:3001' : 'http://localhost:3001';
};

export const DEFAULT_API_HOST = getDevServerHost();

let currentApiBaseUrl = DEFAULT_API_HOST;

export const setApiBaseUrl = (url: string) => {
  currentApiBaseUrl = url.replace(/\/$/, '');
};

export const getApiBaseUrl = () => currentApiBaseUrl;

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
  city?: string;
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
    intent?: {
      queryItem: string;
      city?: string;
      maxBudget?: number;
      restaurantName?: string | null;
      dietaryPreference?: 'veg' | 'non-veg' | 'any';
    };
    restaurantsCount?: number;
    matchedRestaurants?: Array<{ id: string; name: string; rating: number }>;
    itemsEvaluated?: number;
    recommendation?: {
      item: MenuItem;
      restaurant: Restaurant;
    };
    deepLink?: string;
    webUrl?: string;
    error?: string;
    [key: string]: any;
  };
}

export interface StartPipelineResponse {
  success: boolean;
  sessionId: string;
  status: string;
  initialStage: PipelineStage;
  message: string;
}

export interface ApprovalResponse {
  success: boolean;
  sessionId: string;
  deepLink: string;
  webUrl: string;
  item: MenuItem;
  restaurant: Restaurant;
  message: string;
}

export const submitFoodIntent = async (
  prompt: string,
  city: string,
  sessionId?: string
): Promise<StartPipelineResponse> => {
  const res = await fetch(`${currentApiBaseUrl}/api/order/intent`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ prompt, city, sessionId }),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.error || `Failed to submit intent: ${res.statusText}`);
  }

  return res.json();
};

export const approveOrder = async (
  sessionId: string,
  approved: boolean = true,
  selectedItemId?: string
): Promise<ApprovalResponse> => {
  const res = await fetch(`${currentApiBaseUrl}/api/order/approve`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ sessionId, approved, selectedItemId }),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.error || `Failed to approve order: ${res.statusText}`);
  }

  return res.json();
};

export interface TranscribeResponse {
  success: boolean;
  text: string;
  model: string;
  durationMs: number;
  error?: string;
}

/**
 * Sends base64-encoded audio to backend Groq Whisper (whisper-large-v3) endpoint
 */
export const transcribeAudio = async (
  audioBase64: string,
  mimeType: string = 'audio/m4a',
  prompt?: string
): Promise<TranscribeResponse> => {
  const res = await fetch(`${currentApiBaseUrl}/api/voice/transcribe`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ audioBase64, mimeType, prompt }),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(
      errorData.error || `Voice transcription failed with HTTP ${res.status}`
    );
  }

  return res.json();
};

/**
 * Connects to live pipeline trace stream via WebSocket or polling fallback
 */
export const subscribeToPipeline = (
  sessionId: string,
  onEvent: (event: PipelineEvent) => void,
  onError?: (err: any) => void
): (() => void) => {
  let isClosed = false;
  let ws: WebSocket | null = null;
  let pollInterval: any = null;

  // Try WebSocket first
  try {
    const wsUrl = currentApiBaseUrl.replace(/^http/, 'ws') + `/ws?sessionId=${sessionId}`;
    ws = new WebSocket(wsUrl);

    ws.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data);
        if (parsed && parsed.stage) {
          onEvent(parsed as PipelineEvent);
        }
      } catch {
        // ignore parse error
      }
    };

    ws.onerror = () => {
      startPollingFallback();
    };

    ws.onclose = () => {
      // If closed prematurely and not deliberate, start polling fallback
      if (!isClosed) {
        startPollingFallback();
      }
    };
  } catch {
    startPollingFallback();
  }

  function startPollingFallback() {
    if (pollInterval || isClosed) return;
    let lastSeenCount = 0;

    pollInterval = setInterval(async () => {
      if (isClosed) return;
      try {
        const res = await fetch(`${currentApiBaseUrl}/api/order/state/${sessionId}`);
        if (res.ok) {
          const data = await res.json();
          if (data && Array.isArray(data.events)) {
            const newEvents = data.events.slice(lastSeenCount);
            lastSeenCount = data.events.length;
            for (const ev of newEvents) {
              onEvent(ev);
            }
          }
        }
      } catch (e) {
        onError?.(e);
      }
    }, 800);
  }

  return () => {
    isClosed = true;
    if (ws) {
      try {
        ws.close();
      } catch {}
    }
    if (pollInterval) {
      clearInterval(pollInterval);
    }
  };
};
