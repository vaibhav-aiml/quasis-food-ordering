import React, { useEffect, useRef, useState } from 'react';
import {
  Animated,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';

interface VoiceRecorderProps {
  onTranscriptReady: (transcript: string) => void;
  isProcessing: boolean;
}

const PRESET_QUERIES = [
  'Find the best-rated iced latte under 200',
  'Get me cold coffee under 200 from Third Wave Coffee',
  'Truffles burger under 250',
  'Meghana special chicken biryani',
];

export const VoiceRecorder: React.FC<VoiceRecorderProps> = ({
  onTranscriptReady,
  isProcessing,
}) => {
  const [isRecording, setIsRecording] = useState(false);
  const [activePresetIndex, setActivePresetIndex] = useState(0);

  // Waveform bar animations
  const bar1 = useRef(new Animated.Value(12)).current;
  const bar2 = useRef(new Animated.Value(20)).current;
  const bar3 = useRef(new Animated.Value(14)).current;
  const bar4 = useRef(new Animated.Value(28)).current;
  const bar5 = useRef(new Animated.Value(16)).current;

  useEffect(() => {
    let animation: Animated.CompositeAnimation | null = null;
    if (isRecording) {
      const createWaveAnimation = (anim: Animated.Value, min: number, max: number, duration: number) => {
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

  const toggleRecording = () => {
    if (isRecording) {
      setIsRecording(false);
      // Simulate completed transcription from speech
      const chosenQuery = PRESET_QUERIES[activePresetIndex % PRESET_QUERIES.length];
      onTranscriptReady(chosenQuery);
      setActivePresetIndex((prev) => prev + 1);
    } else {
      setIsRecording(true);
      // Auto-finish after 2.5 seconds if user leaves it running
      setTimeout(() => {
        setIsRecording((current) => {
          if (current) {
            const chosenQuery = PRESET_QUERIES[activePresetIndex % PRESET_QUERIES.length];
            onTranscriptReady(chosenQuery);
            setActivePresetIndex((prev) => prev + 1);
            return false;
          }
          return false;
        });
      }, 2500);
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
              disabled={isProcessing || isRecording}
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
            isProcessing && styles.micButtonDisabled,
          ]}
          onPress={toggleRecording}
          disabled={isProcessing}
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
            <Text style={styles.micIcon}>🎙️</Text>
          )}
        </TouchableOpacity>

        <Text style={styles.statusText}>
          {isRecording
            ? 'Listening... Tap to finalize voice prompt'
            : isProcessing
            ? 'Pipeline executing...'
            : 'Tap mic or type above to order via Swiggy'}
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
  },
});
