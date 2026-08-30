import React from 'react';
import {
  Modal,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import { SUPPORTED_CITIES, SupportedCity } from '../constants/cities';

interface CityPickerModalProps {
  visible: boolean;
  selectedCity: string | null;
  onSelectCity: (city: string) => void;
  onClose?: () => void;
  canClose?: boolean;
}

export const CityPickerModal: React.FC<CityPickerModalProps> = ({
  visible,
  selectedCity,
  onSelectCity,
  onClose,
  canClose = true,
}) => {
  return (
    <Modal
      visible={visible}
      animationType="slide"
      transparent={false}
      onRequestClose={() => {
        if (canClose && onClose) {
          onClose();
        }
      }}
    >
      <SafeAreaView style={styles.container}>
        <View style={styles.header}>
          <View>
            <Text style={styles.title}>📍 Select Your City</Text>
            <Text style={styles.subtitle}>
              Swiggy recommendations will be tailored to outlets in your city
            </Text>
          </View>
          {canClose && onClose && selectedCity && (
            <TouchableOpacity onPress={onClose} style={styles.closeBtn}>
              <Text style={styles.closeBtnText}>✕</Text>
            </TouchableOpacity>
          )}
        </View>

        <ScrollView contentContainerStyle={styles.scrollList}>
          {SUPPORTED_CITIES.map((city: SupportedCity) => {
            const isSelected = selectedCity === city;
            return (
              <TouchableOpacity
                key={city}
                style={[styles.cityCard, isSelected && styles.cityCardSelected]}
                onPress={() => onSelectCity(city)}
                activeOpacity={0.7}
              >
                <View style={styles.cityInfo}>
                  <Text style={[styles.cityName, isSelected && styles.cityNameSelected]}>
                    {city}
                  </Text>
                </View>
                <View style={[styles.radioCircle, isSelected && styles.radioCircleSelected]}>
                  {isSelected && <View style={styles.radioDot} />}
                </View>
              </TouchableOpacity>
            );
          })}
        </ScrollView>
      </SafeAreaView>
    </Modal>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0f172a',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    paddingHorizontal: 20,
    paddingTop: 24,
    paddingBottom: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#334155',
  },
  title: {
    fontSize: 22,
    fontWeight: '800',
    color: '#f8fafc',
    marginBottom: 4,
  },
  subtitle: {
    fontSize: 13,
    color: '#94a3b8',
    maxWidth: 280,
  },
  closeBtn: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: '#1e293b',
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: '#334155',
  },
  closeBtnText: {
    color: '#cbd5e1',
    fontSize: 16,
    fontWeight: '600',
  },
  scrollList: {
    padding: 16,
    gap: 10,
  },
  cityCard: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: '#1e293b',
    paddingVertical: 16,
    paddingHorizontal: 18,
    borderRadius: 12,
    borderWidth: 1.5,
    borderColor: '#334155',
  },
  cityCardSelected: {
    borderColor: '#10b981',
    backgroundColor: '#064e3b22',
  },
  cityInfo: {
    flex: 1,
  },
  cityName: {
    fontSize: 16,
    fontWeight: '600',
    color: '#e2e8f0',
  },
  cityNameSelected: {
    color: '#10b981',
    fontWeight: '700',
  },
  radioCircle: {
    width: 22,
    height: 22,
    borderRadius: 11,
    borderWidth: 2,
    borderColor: '#64748b',
    alignItems: 'center',
    justifyContent: 'center',
  },
  radioCircleSelected: {
    borderColor: '#10b981',
  },
  radioDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: '#10b981',
  },
});
