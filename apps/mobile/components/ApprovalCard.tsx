import React, { useState } from 'react';
import {
  ActivityIndicator,
  Image,
  Linking,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import { MenuItem, Restaurant } from '../services/api';

interface ApprovalCardProps {
  item: MenuItem;
  restaurant: Restaurant;
  deepLink: string;
  webUrl: string;
  onApprove: () => Promise<void>;
  onReject?: () => void;
}

export const ApprovalCard: React.FC<ApprovalCardProps> = ({
  item,
  restaurant,
  deepLink,
  webUrl,
  onApprove,
  onReject,
}) => {
  const [isOpening, setIsOpening] = useState(false);

  const handleOpenSwiggy = async () => {
    try {
      setIsOpening(true);
      await onApprove();

      // Tactical Refinement: Check if native Swiggy deep link is supported, else fallback to web URL
      const supported = await Linking.canOpenURL(deepLink);
      if (supported) {
        await Linking.openURL(deepLink);
      } else {
        await Linking.openURL(webUrl);
      }
    } catch (err) {
      console.warn('Error opening Swiggy URL, opening web fallback:', err);
      try {
        await Linking.openURL(webUrl);
      } catch (fallbackErr) {
        console.error('Failed to open web URL:', fallbackErr);
      }
    } finally {
      setIsOpening(false);
    }
  };

  return (
    <View style={styles.card}>
      {/* Header Banner */}
      <View style={styles.header}>
        <View style={styles.badgeRow}>
          <View style={styles.approvalBadge}>
            <Text style={styles.approvalBadgeText}>⚡ PROPOSED ORDER MATCH</Text>
          </View>
          <View style={[styles.dietBadge, item.isVeg ? styles.vegBadge : styles.nonVegBadge]}>
            <View style={[styles.dietDot, item.isVeg ? styles.vegDot : styles.nonVegDot]} />
            <Text style={[styles.dietText, item.isVeg ? styles.vegText : styles.nonVegText]}>
              {item.isVeg ? 'VEG' : 'NON-VEG'}
            </Text>
          </View>
        </View>
      </View>

      {/* Item Image and Core Info */}
      <View style={styles.body}>
        {item.image ? (
          <Image source={{ uri: item.image }} style={styles.itemImage} resizeMode="cover" />
        ) : null}

        <View style={styles.content}>
          <Text style={styles.itemName}>{item.name}</Text>
          <Text style={styles.restaurantName}>at {restaurant.name}</Text>

          <View style={styles.metaRow}>
            <View style={styles.ratingBox}>
              <Text style={styles.starText}>★</Text>
              <Text style={styles.ratingValue}>{item.rating.toFixed(1)}</Text>
              <Text style={styles.reviewCount}>({item.ratingCount.toLocaleString()})</Text>
            </View>

            <View style={styles.priceTag}>
              <Text style={styles.currency}>₹</Text>
              <Text style={styles.priceValue}>{item.price}</Text>
            </View>
          </View>

          {item.description ? (
            <Text style={styles.description} numberOfLines={2}>
              {item.description}
            </Text>
          ) : null}

          <View style={styles.deliveryRow}>
            <Text style={styles.deliveryText}>
              ⏱️ ~{restaurant.deliveryTimeMinutes} mins delivery | 📍 {restaurant.address.split(',')[0]}
            </Text>
          </View>
        </View>
      </View>

      {/* Action Buttons */}
      <View style={styles.actionContainer}>
        {onReject && (
          <TouchableOpacity
            style={styles.rejectButton}
            onPress={onReject}
            disabled={isOpening}
            activeOpacity={0.7}
          >
            <Text style={styles.rejectButtonText}>Decline</Text>
          </TouchableOpacity>
        )}

        <TouchableOpacity
          style={[styles.approveButton, !onReject && styles.approveButtonFull]}
          onPress={handleOpenSwiggy}
          disabled={isOpening}
          activeOpacity={0.85}
        >
          {isOpening ? (
            <ActivityIndicator size="small" color="#ffffff" />
          ) : (
            <View style={styles.buttonContent}>
              <Text style={styles.swiggyIcon}>🟠</Text>
              <Text style={styles.approveButtonText}>Approve & Open Swiggy</Text>
            </View>
          )}
        </TouchableOpacity>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  card: {
    backgroundColor: '#1a1e2b',
    borderRadius: 20,
    borderWidth: 1.5,
    borderColor: '#fc8019',
    overflow: 'hidden',
    marginVertical: 14,
    shadowColor: '#fc8019',
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 0.25,
    shadowRadius: 12,
    elevation: 6,
  },
  header: {
    paddingHorizontal: 16,
    paddingTop: 14,
    paddingBottom: 8,
    backgroundColor: '#141724',
    borderBottomWidth: 1,
    borderBottomColor: '#242a3e',
  },
  badgeRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  approvalBadge: {
    backgroundColor: '#fc801926',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: '#fc8019',
  },
  approvalBadgeText: {
    color: '#fc8019',
    fontSize: 11,
    fontWeight: '800',
    letterSpacing: 0.5,
  },
  dietBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6,
    borderWidth: 1,
  },
  vegBadge: {
    backgroundColor: '#052e16',
    borderColor: '#22c55e',
  },
  nonVegBadge: {
    backgroundColor: '#450a0a',
    borderColor: '#ef4444',
  },
  dietDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    marginRight: 5,
  },
  vegDot: {
    backgroundColor: '#22c55e',
  },
  nonVegDot: {
    backgroundColor: '#ef4444',
  },
  dietText: {
    fontSize: 10,
    fontWeight: '700',
  },
  vegText: {
    color: '#4ade80',
  },
  nonVegText: {
    color: '#f87171',
  },
  body: {
    padding: 16,
  },
  itemImage: {
    width: '100%',
    height: 160,
    borderRadius: 12,
    marginBottom: 14,
  },
  content: {
    gap: 4,
  },
  itemName: {
    fontSize: 20,
    fontWeight: '800',
    color: '#ffffff',
    letterSpacing: 0.2,
  },
  restaurantName: {
    fontSize: 14,
    fontWeight: '600',
    color: '#94a3b8',
  },
  metaRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginVertical: 8,
  },
  ratingBox: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#064e3b',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6,
  },
  starText: {
    color: '#fbbf24',
    fontSize: 13,
    marginRight: 4,
  },
  ratingValue: {
    color: '#ffffff',
    fontSize: 13,
    fontWeight: '700',
    marginRight: 4,
  },
  reviewCount: {
    color: '#94a3b8',
    fontSize: 11,
  },
  priceTag: {
    flexDirection: 'row',
    alignItems: 'baseline',
    backgroundColor: '#22c55e1a',
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#22c55e44',
  },
  currency: {
    color: '#4ade80',
    fontSize: 14,
    fontWeight: '700',
  },
  priceValue: {
    color: '#4ade80',
    fontSize: 20,
    fontWeight: '900',
  },
  description: {
    fontSize: 12,
    color: '#94a3b8',
    lineHeight: 18,
    marginTop: 4,
  },
  deliveryRow: {
    marginTop: 8,
    paddingTop: 8,
    borderTopWidth: 1,
    borderTopColor: '#252c3d',
  },
  deliveryText: {
    fontSize: 11,
    color: '#64748b',
  },
  actionContainer: {
    flexDirection: 'row',
    padding: 14,
    backgroundColor: '#141724',
    borderTopWidth: 1,
    borderTopColor: '#242a3e',
    gap: 10,
  },
  rejectButton: {
    flex: 1,
    height: 48,
    justifyContent: 'center',
    alignItems: 'center',
    borderRadius: 12,
    backgroundColor: '#23293a',
    borderWidth: 1,
    borderColor: '#374151',
  },
  rejectButtonText: {
    color: '#94a3b8',
    fontSize: 14,
    fontWeight: '600',
  },
  approveButton: {
    flex: 2,
    height: 48,
    justifyContent: 'center',
    alignItems: 'center',
    borderRadius: 12,
    backgroundColor: '#fc8019',
    shadowColor: '#fc8019',
    shadowOffset: { width: 0, height: 3 },
    shadowOpacity: 0.4,
    shadowRadius: 6,
    elevation: 4,
  },
  approveButtonFull: {
    flex: 1,
  },
  buttonContent: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  swiggyIcon: {
    fontSize: 16,
  },
  approveButtonText: {
    color: '#ffffff',
    fontSize: 15,
    fontWeight: '800',
    letterSpacing: 0.3,
  },
});
