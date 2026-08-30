import React, { useEffect, useRef, useState } from 'react';
import {
  Alert,
  Animated,
  Platform,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import { transcribeAudio } from '../services/api';

// Conditionally import audio modules on native platforms
let ExpoAVAudio: any = null;
let ExpoAudioModule: any = null;
let AudioModule: any = null;
let AudioRecorder: any = null;
let RecordingPresets: any = null;
let FileSystem: any = null;

if (Platform.OS !== 'web') {
  try {
    const expoAv = require('expo-av');
    ExpoAVAudio = expoAv.Audio;
  } catch (e) {
    // optional fallback
  }

  // Only attempt expo-audio if expo-av is not available
  if (!ExpoAVAudio) {
    try {
      const ExpoAudio = require('expo-audio');
      ExpoAudioModule = ExpoAudio;
      AudioModule = ExpoAudio.AudioModule;
      AudioRecorder = ExpoAudio.AudioRecorder || ExpoAudio.AudioModule?.AudioRecorder;
      RecordingPresets = ExpoAudio.RecordingPresets;
    } catch (e) {
      // optional fallback
    }
  }

  try {
    FileSystem = require('expo-file-system');
  } catch (e) {
    console.warn('expo-file-system load warning:', e);
  }
}

interface VoiceRecorderProps {
  onTranscriptReady: (transcript: string) => void;
  isProcessing: boolean;
}

const PRESET_QUERIES = [
  'Find the best-rated iced latte under 200',
  'Get me cold coffee under 200 from Third Wave Coffee',
  'Truffles burger under 250',
  'Meghana special chicken biryani',
  'Subway paneer tikka sub under 250',
  'Domino\'s farmhouse pizza under 350',
];

export const VoiceRecorder: React.FC<VoiceRecorderProps> = ({
  onTranscriptReady,
  isProcessing,
}) => {
  const [isRecording, setIsRecording] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string>(
    'Tap mic to speak, or tap a preset below'
  );

  // Web MediaRecorder references
  const mediaRecorderRef = useRef<any>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const mediaStreamRef = useRef<any>(null);

  // Native AudioRecorder reference (either expo-av Audio.Recording or expo-audio AudioRecorder)
  const nativeRecordingRef = useRef<any>(null);
  const recordingEngineRef = useRef<'expo-av' | 'expo-audio' | null>(null);

  // Waveform bar animations
  const bar1 = useRef(new Animated.Value(12)).current;
  const bar2 = useRef(new Animated.Value(20)).current;
  const bar3 = useRef(new Animated.Value(14)).current;
  const bar4 = useRef(new Animated.Value(28)).current;
  const bar5 = useRef(new Animated.Value(16)).current;

  useEffect(() => {
    let animation: Animated.CompositeAnimation | null = null;
    if (isRecording) {
      const createWaveAnimation = (
        anim: Animated.Value,
        min: number,
        max: number,
        duration: number
      ) => {
        return Animated.loop(
          Animated.sequence([
            Animated.timing(anim, {
              toValue: max,
              duration,
              useNativeDriver: false,
            }),
            Animated.timing(anim, {
              toValue: min,
              duration,
              useNativeDriver: false,
            }),
          ])
        );
      };

      const a1 = createWaveAnimation(bar1, 8, 36, 300);
      const a2 = createWaveAnimation(bar2, 12, 44, 250);
      const a3 = createWaveAnimation(bar3, 6, 38, 350);
      const a4 = createWaveAnimation(bar4, 14, 48, 280);
      const a5 = createWaveAnimation(bar5, 8, 32, 320);

      animation = Animated.parallel([a1, a2, a3, a4, a5]);
      animation.start();
    } else {
      bar1.setValue(12);
      bar2.setValue(20);
      bar3.setValue(14);
      bar4.setValue(28);
      bar5.setValue(16);
    }

    return () => {
      animation?.stop();
    };
  }, [isRecording]);

  /**
   * Starts recording on Web using MediaRecorder API
   */
  const startWebRecording = async () => {
    try {
      if (!navigator?.mediaDevices?.getUserMedia) {
        throw new Error('Microphone recording is not supported in this browser.');
      }

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaStreamRef.current = stream;
      audioChunksRef.current = [];

      let mimeType = 'audio/webm';
      if (typeof MediaRecorder.isTypeSupported === 'function') {
        if (MediaRecorder.isTypeSupported('audio/webm;codecs=opus')) {
          mimeType = 'audio/webm;codecs=opus';
        } else if (MediaRecorder.isTypeSupported('audio/mp4')) {
          mimeType = 'audio/mp4';
        }
      }

      const mediaRecorder = new MediaRecorder(stream, { mimeType });
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.start(100); // chunk every 100ms
      setIsRecording(true);
      setStatusMessage('🎙️ Listening... Tap mic when done speaking');
    } catch (err: any) {
      console.warn('Web mic recording error:', err);
      Alert.alert(
        'Microphone Access Required',
        `Could not access microphone: ${err.message || 'Permission denied'}.\nYou can also use the preset buttons below.`
      );
      setStatusMessage('⚠️ Microphone error. Use presets or type above.');
    }
  };

  /**
   * Stops recording on Web and sends audio to Groq Whisper
   */
  const stopWebRecording = async () => {
    return new Promise<void>((resolve) => {
      const mediaRecorder = mediaRecorderRef.current;
      if (!mediaRecorder) {
        setIsRecording(false);
        resolve();
        return;
      }

      mediaRecorder.onstop = async () => {
        setIsRecording(false);
        setIsTranscribing(true);
        setStatusMessage('⚡ Transcribing with Groq Whisper (large-v3)...');

        try {
          // Stop media tracks
          if (mediaStreamRef.current) {
            mediaStreamRef.current.getTracks().forEach((track: any) => track.stop());
            mediaStreamRef.current = null;
          }

          const blob = new Blob(audioChunksRef.current, {
            type: mediaRecorder.mimeType || 'audio/webm',
          });

          // Convert Blob to base64
          const reader = new FileReader();
          reader.readAsDataURL(blob);
          reader.onloadend = async () => {
            const base64Data = (reader.result as string) || '';
            try {
              const res = await transcribeAudio(base64Data, blob.type);
              setIsTranscribing(false);
              if (res.success && res.text) {
                setStatusMessage(`✅ Heard: "${res.text}"`);
                onTranscriptReady(res.text);
              } else {
                setStatusMessage('⚠️ Could not recognize speech. Try again or use presets.');
              }
            } catch (apiErr: any) {
              setIsTranscribing(false);
              console.warn('Whisper API call failed:', apiErr);
              setStatusMessage('⚠️ Whisper transcription failed. Check backend connection.');
            }
            resolve();
          };
          reader.onerror = () => {
            setIsTranscribing(false);
            setStatusMessage('⚠️ Error reading audio.');
            resolve();
          };
        } catch (err) {
          setIsTranscribing(false);
          setStatusMessage('⚠️ Error processing audio.');
          resolve();
        }
      };

      mediaRecorder.stop();
    });
  };

  /**
   * Starts recording on Native device (expo-av for Expo Go, or expo-audio)
   */
  const startNativeRecording = async () => {
    try {
      // 1. Primary path: expo-av (native in Expo Go on Android & iOS)
      if (ExpoAVAudio) {
        const permission = await ExpoAVAudio.requestPermissionsAsync();
        if (!permission.granted) {
          Alert.alert('Permission Denied', 'Microphone permission is required for voice ordering.');
          return;
        }

        await ExpoAVAudio.setAudioModeAsync({
          allowsRecordingIOS: true,
          playsInSilentModeIOS: true,
        });

        const recording = new ExpoAVAudio.Recording();
        await recording.prepareToRecordAsync(ExpoAVAudio.RecordingOptionsPresets.HIGH_QUALITY);
        await recording.startAsync();

        nativeRecordingRef.current = recording;
        recordingEngineRef.current = 'expo-av';
        setIsRecording(true);
        setStatusMessage('🎙️ Listening... Tap mic when done speaking');
        return;
      }

      // 2. Fallback path: expo-audio (if prebuilt with custom native modules)
      if (ExpoAudioModule || AudioRecorder) {
        if (ExpoAudioModule && typeof ExpoAudioModule.requestRecordingPermissionsAsync === 'function') {
          const permission = await ExpoAudioModule.requestRecordingPermissionsAsync();
          if (!permission.granted) {
            Alert.alert('Permission Denied', 'Microphone permission is required for voice ordering.');
            return;
          }
        } else if (AudioModule && typeof AudioModule.requestRecordingPermissionsAsync === 'function') {
          const permission = await AudioModule.requestRecordingPermissionsAsync();
          if (!permission.granted) {
            Alert.alert('Permission Denied', 'Microphone permission is required for voice ordering.');
            return;
          }
        }

        const preset = RecordingPresets?.HIGH_QUALITY || {};
        const RecorderClass = AudioRecorder || AudioModule?.AudioRecorder;
        if (!RecorderClass) {
          throw new Error('AudioRecorder native class is not available.');
        }
        const recorder = new RecorderClass(preset);
        nativeRecordingRef.current = recorder;
        recordingEngineRef.current = 'expo-audio';

        if (typeof recorder.prepareToRecordAsync === 'function') {
          await recorder.prepareToRecordAsync();
        }

        if (typeof recorder.record === 'function') {
          recorder.record();
        } else if (typeof recorder.recordAsync === 'function') {
          await recorder.recordAsync();
        }

        setIsRecording(true);
        setStatusMessage('🎙️ Listening... Tap mic when done speaking');
        return;
      }

      throw new Error('No audio recording module available on this device.');
    } catch (err: any) {
      console.warn('Native recording start error:', err);
      Alert.alert(
        'Recording Not Available',
        `Device audio recorder encountered an issue: ${err.message}.\nPlease use preset buttons or search input.`
      );
      setStatusMessage('⚠️ Audio not available on this device. Use presets below.');
    }
  };

  /**
   * Stops recording on Native device and sends audio to Groq Whisper
   */
  const stopNativeRecording = async () => {
    const recording = nativeRecordingRef.current;
    const engine = recordingEngineRef.current;
    if (!recording) {
      setIsRecording(false);
      return;
    }

    try {
      setIsRecording(false);
      setIsTranscribing(true);
      setStatusMessage('⚡ Transcribing with Groq Whisper (large-v3)...');

      let uri: string | null = null;

      if (engine === 'expo-av') {
        await recording.stopAndUnloadAsync();
        uri = recording.getURI();
        if (ExpoAVAudio) {
          await ExpoAVAudio.setAudioModeAsync({
            allowsRecordingIOS: false,
          }).catch(() => {});
        }
      } else {
        if (typeof recording.stop === 'function') {
          await recording.stop();
        } else if (typeof recording.stopAsync === 'function') {
          await recording.stopAsync();
        }
        uri = recording.uri;
      }

      if (!uri) {
        throw new Error('No recorded audio file URI found.');
      }

      // Read file as base64 using FileSystem
      let base64Audio = '';
      if (FileSystem && FileSystem.readAsStringAsync) {
        base64Audio = await FileSystem.readAsStringAsync(uri, {
          encoding: FileSystem.EncodingType?.Base64 || 'base64',
        });
      }

      if (!base64Audio) {
        throw new Error('Failed to encode audio file.');
      }

      const mimeType = uri.endsWith('.m4a') ? 'audio/m4a' : uri.endsWith('.mp4') ? 'audio/mp4' : 'audio/m4a';
      const res = await transcribeAudio(base64Audio, mimeType);
      setIsTranscribing(false);

      if (res.success && res.text) {
        setStatusMessage(`✅ Heard: "${res.text}"`);
        onTranscriptReady(res.text);
      } else {
        setStatusMessage('⚠️ Could not recognize speech. Try again or tap preset.');
      }
    } catch (err: any) {
      setIsTranscribing(false);
      console.warn('Native recording stop error:', err);
      setStatusMessage('⚠️ Whisper transcription failed. Try again or tap preset.');
    } finally {
      nativeRecordingRef.current = null;
      recordingEngineRef.current = null;
    }
  };

  const toggleRecording = async () => {
    if (isProcessing || isTranscribing) return;

    if (isRecording) {
      if (Platform.OS === 'web') {
        await stopWebRecording();
      } else {
        await stopNativeRecording();
      }
    } else {
      if (Platform.OS === 'web') {
        await startWebRecording();
      } else {
        await startNativeRecording();
      }
    }
  };

  return (
    <View style={styles.container}>
      {/* Quick Prompt Chips */}
      <View style={styles.presetSection}>
        <Text style={styles.presetLabel}>Quick Voice / Intent Presets:</Text>
        <View style={styles.chipContainer}>
          {PRESET_QUERIES.map((query, index) => (
            <TouchableOpacity
              key={index}
              style={styles.chip}
              onPress={() => onTranscriptReady(query)}
              disabled={isProcessing || isRecording || isTranscribing}
              activeOpacity={0.7}
            >
              <Text style={styles.chipText} numberOfLines={1}>
                💬 {query}
              </Text>
            </TouchableOpacity>
          ))}
        </View>
      </View>

      {/* Voice Mic Interaction Area */}
      <View style={styles.recorderArea}>
        <TouchableOpacity
          style={[
            styles.micButton,
            isRecording && styles.micButtonActive,
            (isProcessing || isTranscribing) && styles.micButtonDisabled,
          ]}
          onPress={toggleRecording}
          disabled={isProcessing || isTranscribing}
          activeOpacity={0.8}
        >
          {isRecording ? (
            <View style={styles.waveformContainer}>
              <Animated.View style={[styles.waveBar, { height: bar1 }]} />
              <Animated.View style={[styles.waveBar, { height: bar2 }]} />
              <Animated.View style={[styles.waveBar, { height: bar4 }]} />
              <Animated.View style={[styles.waveBar, { height: bar3 }]} />
              <Animated.View style={[styles.waveBar, { height: bar5 }]} />
            </View>
          ) : (
            <Text style={styles.micIcon}>{isTranscribing ? '⏳' : '🎙️'}</Text>
          )}
        </TouchableOpacity>

        <Text
          style={[
            styles.statusText,
            isRecording && styles.statusTextActive,
            isTranscribing && styles.statusTextTranscribing,
          ]}
        >
          {statusMessage}
        </Text>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    marginVertical: 10,
  },
  presetSection: {
    marginBottom: 12,
  },
  presetLabel: {
    color: '#64748b',
    fontSize: 11,
    fontWeight: '700',
    letterSpacing: 0.8,
    marginBottom: 6,
    textTransform: 'uppercase',
  },
  chipContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 6,
  },
  chip: {
    backgroundColor: '#1b202e',
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#2d3748',
    maxWidth: '100%',
  },
  chipText: {
    color: '#cbd5e1',
    fontSize: 11,
    fontWeight: '500',
  },
  recorderArea: {
    alignItems: 'center',
    paddingVertical: 12,
  },
  micButton: {
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: '#1e2538',
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 2,
    borderColor: '#3b82f6',
    shadowColor: '#3b82f6',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 4,
  },
  micButtonActive: {
    borderColor: '#ef4444',
    backgroundColor: '#3b1219',
    shadowColor: '#ef4444',
  },
  micButtonDisabled: {
    opacity: 0.5,
    borderColor: '#475569',
  },
  micIcon: {
    fontSize: 26,
  },
  waveformContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 3,
    height: 48,
  },
  waveBar: {
    width: 4,
    borderRadius: 2,
    backgroundColor: '#ef4444',
  },
  statusText: {
    color: '#94a3b8',
    fontSize: 12,
    marginTop: 8,
    fontWeight: '500',
    textAlign: 'center',
  },
  statusTextActive: {
    color: '#f87171',
    fontWeight: '700',
  },
  statusTextTranscribing: {
    color: '#60a5fa',
    fontWeight: '700',
  },
});
