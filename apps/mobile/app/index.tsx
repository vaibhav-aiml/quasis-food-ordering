import React, { useEffect, useRef, useState } from 'react';
import {
  Alert,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';
import { ApprovalCard } from '../components/ApprovalCard';
import { CityPickerModal } from '../components/CityPickerModal';
import { OrderHistoryModal } from '../components/OrderHistoryModal';
import { PipelineTrace } from '../components/PipelineTrace';
import { VoiceRecorder } from '../components/VoiceRecorder';
import AsyncStorage from '@react-native-async-storage/async-storage';
import {
  approveOrder,
  getApiBaseUrl,
  MenuItem,
  PipelineEvent,
  PipelineStage,
  Restaurant,
  setApiBaseUrl,
  submitFoodIntent,
  subscribeToPipeline,
} from '../services/api';
import { OrderStorage, StoredOrder } from '../services/orderStorage';

export default function MainScreen() {
  const [prompt, setPrompt] = useState('Find the best-rated iced latte under 200');
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [currentStage, setCurrentStage] = useState<PipelineStage | null>(null);
  const [events, setEvents] = useState<PipelineEvent[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [recommendation, setRecommendation] = useState<{
    item: MenuItem;
    restaurant: Restaurant;
    deepLink: string;
    webUrl: string;
  } | null>(null);
  const [completedState, setCompletedState] = useState<{
    deepLink: string;
    webUrl: string;
  } | null>(null);

  // Server URL settings for physical Android devices over Wi-Fi
  const [apiHost, setApiHost] = useState(getApiBaseUrl());
  const [showSettings, setShowSettings] = useState(false);

  // City Selection State
  const [selectedCity, setSelectedCity] = useState<string | null>(null);
  const [showCityPicker, setShowCityPicker] = useState(false);

  // Order History & Favorites Modal State
  const [showHistory, setShowHistory] = useState(false);
  const [orderCount, setOrderCount] = useState(0);

  const unsubscribeRef = useRef<(() => void) | null>(null);
  const scrollViewRef = useRef<ScrollView>(null);

  const refreshOrderCount = async () => {
    const list = await OrderStorage.getOrders();
    setOrderCount(list.length);
  };

  useEffect(() => {
    refreshOrderCount();
    (async () => {
      try {
        const savedCity = await AsyncStorage.getItem('quasis_selected_city');
        if (savedCity) {
          setSelectedCity(savedCity);
        } else {
          setShowCityPicker(true);
        }
      } catch (err) {
        console.warn('Failed to load selected city:', err);
        setShowCityPicker(true);
      }
    })();
    return () => {
      if (unsubscribeRef.current) {
        unsubscribeRef.current();
      }
    };
  }, []);

  const handleSelectCity = async (city: string) => {
    setSelectedCity(city);
    try {
      await AsyncStorage.setItem('quasis_selected_city', city);
    } catch (err) {
      console.warn('Failed to persist city:', err);
    }
    setShowCityPicker(false);
  };

  const handleStartPipeline = async (customPrompt?: string) => {
    const textToRun = customPrompt || prompt;
    if (!textToRun.trim()) {
      Alert.alert('Empty Request', 'Please type or speak your food order intent.');
      return;
    }

    if (!selectedCity) {
      setShowCityPicker(true);
      Alert.alert('Select City', 'Please select your city before submitting an order.');
      return;
    }

    // Reset state
    if (unsubscribeRef.current) {
      unsubscribeRef.current();
      unsubscribeRef.current = null;
    }
    setEvents([]);
    setRecommendation(null);
    setCompletedState(null);
    setIsLoading(true);
    setCurrentStage('PARSING_INTENT');

    try {
      const response = await submitFoodIntent(textToRun, selectedCity);
      setSessionId(response.sessionId);

      // Subscribe to real-time execution trace
      unsubscribeRef.current = subscribeToPipeline(
        response.sessionId,
        (event: PipelineEvent) => {
          setCurrentStage(event.stage);
          setEvents((prev) => {
            // Avoid duplicate events with same timestamp and stage
            const exists = prev.some(
              (e) => e.timestamp === event.timestamp && e.stage === event.stage
            );
            if (exists) return prev;
            return [...prev, event];
          });

          // Check if recommendation data is available
          if (event.data?.recommendation && event.data?.deepLink && event.data?.webUrl) {
            setRecommendation({
              item: event.data.recommendation.item,
              restaurant: event.data.recommendation.restaurant,
              deepLink: event.data.deepLink,
              webUrl: event.data.webUrl,
            });
          }

          if (event.stage === 'AWAITING_APPROVAL') {
            setIsLoading(false);
            setTimeout(() => {
              scrollViewRef.current?.scrollToEnd({ animated: true });
            }, 300);
          }

          if (event.stage === 'COMPLETED') {
            setIsLoading(false);
            if (event.data?.deepLink && event.data?.webUrl) {
              setCompletedState({
                deepLink: event.data.deepLink,
                webUrl: event.data.webUrl,
              });

              // Persist completed order to OrderStorage
              if (event.data.recommendation) {
                OrderStorage.saveOrder({
                  sessionId: response.sessionId,
                  prompt: textToRun,
                  item: event.data.recommendation.item,
                  restaurant: event.data.recommendation.restaurant,
                  deepLink: event.data.deepLink,
                  webUrl: event.data.webUrl,
                  status: 'DISPATCHED',
                }).then(() => refreshOrderCount());
              }
            }
          }

          if (event.stage === 'FAILED') {
            setIsLoading(false);
          }
        },
        (err) => {
          console.warn('Pipeline stream warning:', err);
        }
      );
    } catch (err: any) {
      setIsLoading(false);
      Alert.alert(
        'Connection Error',
        `Could not reach backend at ${apiHost}.\n\nEnsure backend is running: npm run dev in services/backend/.\n\nError: ${err.message}`
      );
    }
  };

  const handleApprove = async () => {
    if (!sessionId || !recommendation) return;
    try {
      const result = await approveOrder(sessionId, true);
      setCompletedState({
        deepLink: result.deepLink,
        webUrl: result.webUrl,
      });

      // Persist approved order
      await OrderStorage.saveOrder({
        sessionId,
        prompt,
        item: recommendation.item,
        restaurant: recommendation.restaurant,
        deepLink: result.deepLink,
        webUrl: result.webUrl,
        status: 'DISPATCHED',
      });
      await refreshOrderCount();
    } catch (err: any) {
      Alert.alert('Approval Error', err.message);
    }
  };

  const handleReject = () => {
    if (!sessionId) return;
    approveOrder(sessionId, false).catch(() => {});
    setRecommendation(null);
    Alert.alert('Proposal Dismissed', 'You can try another search or voice prompt.');
  };

  const handleSaveHost = () => {
    setApiBaseUrl(apiHost);
    setShowSettings(false);
    Alert.alert('Backend URL Updated', `API Endpoint set to: ${apiHost}`);
  };

  // Instant dispatch from order history (skips artificial pipeline search delays)
  const handleInstantDispatchFromHistory = async (order: StoredOrder) => {
    setRecommendation({
      item: {
        ...order.item,
        rating: 4.6,
        ratingCount: 1500,
        popular: true,
        category: order.item.category || 'Dishes',
        image: order.item.image || '',
        description: order.item.description || '',
      },
      restaurant: {
        ...order.restaurant,
        slug: order.restaurant.name.toLowerCase().replace(/\s+/g, '-'),
        ratingCount: 2000,
        cuisines: ['Popular'],
        coverImage: order.restaurant.coverImage || '',
      },
      deepLink: order.deepLink,
      webUrl: order.webUrl,
    });

    setCompletedState({
      deepLink: order.deepLink,
      webUrl: order.webUrl,
    });

    setPrompt(order.prompt || order.item.name);
    setTimeout(() => {
      scrollViewRef.current?.scrollToEnd({ animated: true });
    }, 200);
  };

  // Pipeline re-run from history
  const handleRerunFromHistory = (query: string) => {
    setPrompt(query);
    handleStartPipeline(query);
  };

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      style={styles.container}
    >
      <ScrollView
        ref={scrollViewRef}
        contentContainerStyle={styles.scrollContent}
        keyboardShouldPersistTaps="handled"
      >
        {/* Top Header */}
        <View style={styles.topHeader}>
          <View>
            <View style={styles.logoRow}>
              <Text style={styles.logoText}>QUASIS</Text>
              <View style={styles.swiggyTag}>
                <Text style={styles.swiggyTagText}>SWIGGY AGENT</Text>
              </View>
            </View>
            <Text style={styles.tagline}>Autonomous Food Ordering Pipeline</Text>
          </View>

          <View style={styles.headerButtons}>
            {/* City Selector Pill */}
            <TouchableOpacity
              style={styles.cityPill}
              onPress={() => setShowCityPicker(true)}
              activeOpacity={0.8}
            >
              <Text style={styles.cityPillPin}>📍</Text>
              <Text style={styles.cityPillText}>{selectedCity || 'Select City'}</Text>
              <Text style={styles.cityPillChevron}>▾</Text>
            </TouchableOpacity>

            {/* History & Favorites Button with Badge */}
            <TouchableOpacity
              style={styles.historyButton}
              onPress={() => setShowHistory(true)}
              activeOpacity={0.8}
            >
              <Text style={styles.historyIcon}>📜</Text>
              {orderCount > 0 && (
                <View style={styles.badge}>
                  <Text style={styles.badgeText}>{orderCount}</Text>
                </View>
              )}
            </TouchableOpacity>

            {/* Server Settings Button */}
            <TouchableOpacity
              style={styles.settingsButton}
              onPress={() => setShowSettings(!showSettings)}
              activeOpacity={0.8}
            >
              <Text style={styles.settingsIcon}>⚙️</Text>
            </TouchableOpacity>
          </View>
        </View>

        {/* Backend Host Config Drawer (for physical Android device over Wi-Fi) */}
        {showSettings && (
          <View style={styles.settingsBox}>
            <Text style={styles.settingsTitle}>Backend Server Address (0.0.0.0)</Text>
            <Text style={styles.settingsSub}>
              For physical devices, enter your PC local IP (e.g. http://192.168.1.5:3001)
            </Text>
            <View style={styles.settingsInputRow}>
              <TextInput
                style={styles.settingsInput}
                value={apiHost}
                onChangeText={setApiHost}
                autoCapitalize="none"
                placeholder="http://192.168.x.x:3001"
                placeholderTextColor="#64748b"
              />
              <TouchableOpacity style={styles.saveHostBtn} onPress={handleSaveHost}>
                <Text style={styles.saveHostText}>Save</Text>
              </TouchableOpacity>
            </View>
          </View>
        )}

        {/* Input Bar */}
        <View style={styles.searchCard}>
          <Text style={styles.inputLabel}>FOOD ORDERING INTENT</Text>
          <View style={styles.inputRow}>
            <TextInput
              style={styles.input}
              placeholder="e.g. Find iced latte under 200 from Blue Tokai"
              placeholderTextColor="#64748b"
              value={prompt}
              onChangeText={setPrompt}
              multiline
            />
            <TouchableOpacity
              style={[styles.runButton, isLoading && styles.runButtonDisabled]}
              onPress={() => handleStartPipeline()}
              disabled={isLoading}
              activeOpacity={0.8}
            >
              <Text style={styles.runButtonText}>{isLoading ? '...' : 'Launch'}</Text>
            </TouchableOpacity>
          </View>
        </View>

        {/* Voice Recorder with Groq Whisper & Preset Chips */}
        <VoiceRecorder
          onTranscriptReady={(transcript) => {
            setPrompt(transcript);
            handleStartPipeline(transcript);
          }}
          isProcessing={isLoading}
        />

        {/* Stage 1-3 Live Pipeline Trace */}
        {(events.length > 0 || isLoading) && (
          <PipelineTrace
            events={events}
            currentStage={currentStage}
            isLoading={isLoading}
          />
        )}

        {/* Stage 4: Human-In-The-Loop Approval Card */}
        {recommendation && (
          <ApprovalCard
            item={recommendation.item}
            restaurant={recommendation.restaurant}
            deepLink={recommendation.deepLink}
            webUrl={recommendation.webUrl}
            onApprove={handleApprove}
            onReject={handleReject}
          />
        )}

        {/* Completion Staging Alert */}
        {completedState && (
          <View style={styles.completedBox}>
            <Text style={styles.completedTitle}>✅ Swiggy Deep Link Dispatched!</Text>
            <Text style={styles.completedSub}>
              Native Link: {completedState.deepLink}
            </Text>
          </View>
        )}
      </ScrollView>

      {/* City Picker Modal */}
      <CityPickerModal
        visible={showCityPicker}
        selectedCity={selectedCity}
        onSelectCity={handleSelectCity}
        onClose={() => setShowCityPicker(false)}
        canClose={!!selectedCity}
      />

      {/* Order History & Favorites Modal */}
      <OrderHistoryModal
        visible={showHistory}
        onClose={() => {
          setShowHistory(false);
          refreshOrderCount();
        }}
        onInstantDispatch={handleInstantDispatchFromHistory}
        onRerunPipeline={handleRerunFromHistory}
      />
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0b0d13',
  },
  scrollContent: {
    padding: 16,
    paddingBottom: 40,
  },
  topHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
    paddingTop: 8,
  },
  logoRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  logoText: {
    fontSize: 22,
    fontWeight: '900',
    color: '#ffffff',
    letterSpacing: 1.5,
  },
  swiggyTag: {
    backgroundColor: '#fc8019',
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 6,
  },
  swiggyTagText: {
    color: '#ffffff',
    fontSize: 10,
    fontWeight: '800',
    letterSpacing: 0.5,
  },
  tagline: {
    color: '#64748b',
    fontSize: 12,
    fontWeight: '500',
    marginTop: 2,
  },
  headerButtons: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  cityPill: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#161922',
    paddingVertical: 8,
    paddingHorizontal: 12,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: '#262c3d',
    gap: 4,
  },
  cityPillPin: {
    fontSize: 12,
  },
  cityPillText: {
    color: '#f8fafc',
    fontSize: 13,
    fontWeight: '700',
  },
  cityPillChevron: {
    color: '#94a3b8',
    fontSize: 12,
    marginLeft: 2,
  },
  historyButton: {
    width: 38,
    height: 38,
    borderRadius: 19,
    backgroundColor: '#161922',
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#262c3d',
    position: 'relative',
  },
  historyIcon: {
    fontSize: 16,
  },
  badge: {
    position: 'absolute',
    top: -4,
    right: -4,
    backgroundColor: '#fc8019',
    borderRadius: 9,
    minWidth: 18,
    height: 18,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 4,
    borderWidth: 1.5,
    borderColor: '#0b0d13',
  },
  badgeText: {
    color: '#ffffff',
    fontSize: 10,
    fontWeight: '900',
  },
  settingsButton: {
    width: 38,
    height: 38,
    borderRadius: 19,
    backgroundColor: '#161922',
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#262c3d',
  },
  settingsIcon: {
    fontSize: 16,
  },
  settingsBox: {
    backgroundColor: '#161922',
    borderRadius: 12,
    padding: 12,
    marginBottom: 14,
    borderWidth: 1,
    borderColor: '#3b82f6',
  },
  settingsTitle: {
    color: '#93c5fd',
    fontSize: 12,
    fontWeight: '700',
  },
  settingsSub: {
    color: '#64748b',
    fontSize: 11,
    marginVertical: 4,
  },
  settingsInputRow: {
    flexDirection: 'row',
    gap: 8,
    marginTop: 6,
  },
  settingsInput: {
    flex: 1,
    backgroundColor: '#0f172a',
    borderRadius: 8,
    paddingHorizontal: 10,
    height: 38,
    color: '#ffffff',
    fontSize: 12,
    borderWidth: 1,
    borderColor: '#334155',
  },
  saveHostBtn: {
    backgroundColor: '#3b82f6',
    borderRadius: 8,
    paddingHorizontal: 14,
    justifyContent: 'center',
    alignItems: 'center',
  },
  saveHostText: {
    color: '#ffffff',
    fontSize: 12,
    fontWeight: '700',
  },
  searchCard: {
    backgroundColor: '#161922',
    borderRadius: 16,
    padding: 14,
    borderWidth: 1,
    borderColor: '#262c3d',
    marginBottom: 6,
  },
  inputLabel: {
    color: '#94a3b8',
    fontSize: 11,
    fontWeight: '800',
    letterSpacing: 0.8,
    marginBottom: 8,
  },
  inputRow: {
    flexDirection: 'row',
    gap: 8,
    alignItems: 'center',
  },
  input: {
    flex: 1,
    backgroundColor: '#0d0f17',
    borderRadius: 12,
    paddingHorizontal: 14,
    paddingVertical: 10,
    color: '#ffffff',
    fontSize: 14,
    borderWidth: 1,
    borderColor: '#23293a',
    minHeight: 48,
  },
  runButton: {
    backgroundColor: '#fc8019',
    borderRadius: 12,
    paddingHorizontal: 18,
    height: 48,
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: '#fc8019',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.3,
    shadowRadius: 4,
    elevation: 3,
  },
  runButtonDisabled: {
    opacity: 0.6,
  },
  runButtonText: {
    color: '#ffffff',
    fontSize: 14,
    fontWeight: '800',
  },
  completedBox: {
    backgroundColor: '#064e3b',
    borderRadius: 12,
    padding: 14,
    marginVertical: 12,
    borderWidth: 1,
    borderColor: '#10b981',
  },
  completedTitle: {
    color: '#34d399',
    fontSize: 14,
    fontWeight: '800',
  },
  completedSub: {
    color: '#a7f3d0',
    fontSize: 11,
    marginTop: 4,
  },
});
