import React, { useEffect, useState } from 'react';
import {
  Alert,
  Image,
  Modal,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';
import { OrderStorage, StoredOrder } from '../services/orderStorage';

interface OrderHistoryModalProps {
  visible: boolean;
  onClose: () => void;
  onInstantDispatch: (order: StoredOrder) => void;
  onRerunPipeline: (prompt: string) => void;
}

export const OrderHistoryModal: React.FC<OrderHistoryModalProps> = ({
  visible,
  onClose,
  onInstantDispatch,
  onRerunPipeline,
}) => {
  const [orders, setOrders] = useState<StoredOrder[]>([]);
  const [activeTab, setActiveTab] = useState<'all' | 'favorites'>('all');
  const [searchQuery, setSearchQuery] = useState('');

  const loadOrders = async () => {
    const list = await OrderStorage.getOrders();
    setOrders(list);
  };

  useEffect(() => {
    if (visible) {
      loadOrders();
    }
  }, [visible]);

  const handleToggleFavorite = async (orderId: string) => {
    await OrderStorage.toggleFavorite(orderId);
    await loadOrders();
  };

  const handleDeleteOrder = async (orderId: string) => {
    await OrderStorage.deleteOrder(orderId);
    await loadOrders();
  };

  const handleClearAll = () => {
    Alert.alert(
      'Clear All Orders',
      'Are you sure you want to clear your entire order history?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Clear All',
          style: 'destructive',
          onPress: async () => {
            await OrderStorage.clearAllOrders();
            await loadOrders();
          },
        },
      ]
    );
  };

  const filteredOrders = orders
    .filter((order) => {
      if (activeTab === 'favorites' && !order.isFavorite) return false;
      if (!searchQuery.trim()) return true;
      const q = searchQuery.toLowerCase();
      return (
        order.item.name.toLowerCase().includes(q) ||
        order.restaurant.name.toLowerCase().includes(q) ||
        order.prompt.toLowerCase().includes(q)
      );
    });

  const favoritesCount = orders.filter((o) => o.isFavorite).length;

  return (
    <Modal
      visible={visible}
      animationType="slide"
      transparent={false}
      onRequestClose={onClose}
    >
      <View style={styles.container}>
        {/* Modal Header */}
        <View style={styles.header}>
          <View>
            <Text style={styles.headerTitle}>Order History & Favorites</Text>
            <Text style={styles.headerSub}>
              {orders.length} past {orders.length === 1 ? 'order' : 'orders'} saved
            </Text>
          </View>
          <View style={styles.headerActions}>
            {orders.length > 0 && (
              <TouchableOpacity style={styles.clearBtn} onPress={handleClearAll}>
                <Text style={styles.clearBtnText}>Clear</Text>
              </TouchableOpacity>
            )}
            <TouchableOpacity style={styles.closeBtn} onPress={onClose}>
              <Text style={styles.closeBtnText}>✕</Text>
            </TouchableOpacity>
          </View>
        </View>

        {/* Tab Selector */}
        <View style={styles.tabBar}>
          <TouchableOpacity
            style={[styles.tabButton, activeTab === 'all' && styles.tabButtonActive]}
            onPress={() => setActiveTab('all')}
          >
            <Text
              style={[
                styles.tabButtonText,
                activeTab === 'all' && styles.tabButtonTextActive,
              ]}
            >
              All Orders ({orders.length})
            </Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[
              styles.tabButton,
              activeTab === 'favorites' && styles.tabButtonActive,
            ]}
            onPress={() => setActiveTab('favorites')}
          >
            <Text
              style={[
                styles.tabButtonText,
                activeTab === 'favorites' && styles.tabButtonTextActive,
              ]}
            >
              ⭐ Favorites ({favoritesCount})
            </Text>
          </TouchableOpacity>
        </View>

        {/* Search Input */}
        {orders.length > 0 && (
          <View style={styles.searchBox}>
            <TextInput
              style={styles.searchInput}
              placeholder="Search past items, restaurants, or queries..."
              placeholderTextColor="#64748b"
              value={searchQuery}
              onChangeText={setSearchQuery}
            />
            {searchQuery.length > 0 && (
              <TouchableOpacity onPress={() => setSearchQuery('')}>
                <Text style={styles.searchClearIcon}>✕</Text>
              </TouchableOpacity>
            )}
          </View>
        )}

        {/* Orders List */}
        <ScrollView
          contentContainerStyle={styles.scrollContent}
          keyboardShouldPersistTaps="handled"
        >
          {filteredOrders.length === 0 ? (
            <View style={styles.emptyContainer}>
              <Text style={styles.emptyIcon}>
                {activeTab === 'favorites' ? '⭐' : '🍽️'}
              </Text>
              <Text style={styles.emptyTitle}>
                {activeTab === 'favorites'
                  ? 'No Favorite Orders Yet'
                  : searchQuery
                  ? 'No matching orders found'
                  : 'No Order History Yet'}
              </Text>
              <Text style={styles.emptySub}>
                {activeTab === 'favorites'
                  ? 'Tap the star ⭐ icon on any past order card to bookmark it for rapid access!'
                  : searchQuery
                  ? 'Try searching with a different item or restaurant name.'
                  : 'Your autonomous Swiggy orders and approvals will appear here with 1-tap re-ordering.'}
              </Text>
            </View>
          ) : (
            filteredOrders.map((order) => (
              <View key={order.id} style={styles.orderCard}>
                {/* Top card metadata */}
                <View style={styles.cardHeader}>
                  <View style={styles.cardHeaderLeft}>
                    <Text style={styles.dateText}>{order.formattedDate}</Text>
                    <View style={styles.statusBadge}>
                      <Text style={styles.statusBadgeText}>
                        {order.status === 'DISPATCHED' ? 'DISPATCHED' : 'SAVED'}
                      </Text>
                    </View>
                  </View>

                  <View style={styles.cardHeaderRight}>
                    <TouchableOpacity
                      style={[
                        styles.iconButton,
                        order.isFavorite && styles.favoriteActive,
                      ]}
                      onPress={() => handleToggleFavorite(order.id)}
                    >
                      <Text style={styles.iconButtonText}>
                        {order.isFavorite ? '⭐' : '☆'}
                      </Text>
                    </TouchableOpacity>

                    <TouchableOpacity
                      style={styles.iconButton}
                      onPress={() => handleDeleteOrder(order.id)}
                    >
                      <Text style={styles.iconButtonText}>🗑️</Text>
                    </TouchableOpacity>
                  </View>
                </View>

                {/* Original Prompt Query */}
                {order.prompt && (
                  <View style={styles.promptRow}>
                    <Text style={styles.promptLabel}>INTENT:</Text>
                    <Text style={styles.promptText} numberOfLines={1}>
                      "{order.prompt}"
                    </Text>
                  </View>
                )}

                {/* Restaurant & Item Details */}
                <View style={styles.detailsRow}>
                  {order.item.image ? (
                    <Image
                      source={{ uri: order.item.image }}
                      style={styles.itemImage}
                      resizeMode="cover"
                    />
                  ) : (
                    <View style={styles.imagePlaceholder}>
                      <Text style={{ fontSize: 24 }}>🍽️</Text>
                    </View>
                  )}

                  <View style={styles.itemInfo}>
                    <View style={styles.itemTitleRow}>
                      <Text style={styles.vegIcon}>
                        {order.item.isVeg ? '🟢' : '🔴'}
                      </Text>
                      <Text style={styles.itemName} numberOfLines={1}>
                        {order.item.name}
                      </Text>
                    </View>

                    <Text style={styles.restaurantName} numberOfLines={1}>
                      {order.restaurant.name} • ⭐ {order.restaurant.rating}
                    </Text>

                    <Text style={styles.itemPrice}>₹{order.item.price}</Text>
                  </View>
                </View>

                {/* Re-order Action Buttons */}
                <View style={styles.actionsRow}>
                  <TouchableOpacity
                    style={styles.instantDispatchBtn}
                    onPress={() => {
                      onInstantDispatch(order);
                      onClose();
                    }}
                    activeOpacity={0.8}
                  >
                    <Text style={styles.instantDispatchText}>
                      ⚡ Instant Dispatch
                    </Text>
                  </TouchableOpacity>

                  <TouchableOpacity
                    style={styles.rerunPipelineBtn}
                    onPress={() => {
                      onRerunPipeline(order.prompt || order.item.name);
                      onClose();
                    }}
                    activeOpacity={0.8}
                  >
                    <Text style={styles.rerunPipelineText}>🔄 Re-run</Text>
                  </TouchableOpacity>
                </View>
              </View>
            ))
          )}
        </ScrollView>
      </View>
    </Modal>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0b0d13',
    paddingTop: 16,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingBottom: 14,
    borderBottomWidth: 1,
    borderBottomColor: '#1e2538',
  },
  headerTitle: {
    color: '#ffffff',
    fontSize: 18,
    fontWeight: '800',
  },
  headerSub: {
    color: '#64748b',
    fontSize: 12,
    marginTop: 2,
  },
  headerActions: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  clearBtn: {
    backgroundColor: '#2d1519',
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#7f1d1d',
  },
  clearBtnText: {
    color: '#f87171',
    fontSize: 11,
    fontWeight: '700',
  },
  closeBtn: {
    width: 34,
    height: 34,
    borderRadius: 17,
    backgroundColor: '#1b202e',
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#2d3748',
  },
  closeBtnText: {
    color: '#cbd5e1',
    fontSize: 14,
    fontWeight: '700',
  },
  tabBar: {
    flexDirection: 'row',
    paddingHorizontal: 16,
    paddingVertical: 10,
    gap: 8,
  },
  tabButton: {
    flex: 1,
    paddingVertical: 8,
    borderRadius: 8,
    backgroundColor: '#161922',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#262c3d',
  },
  tabButtonActive: {
    backgroundColor: '#1e2538',
    borderColor: '#fc8019',
  },
  tabButtonText: {
    color: '#94a3b8',
    fontSize: 12,
    fontWeight: '600',
  },
  tabButtonTextActive: {
    color: '#fc8019',
    fontWeight: '800',
  },
  searchBox: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#161922',
    marginHorizontal: 16,
    marginBottom: 8,
    paddingHorizontal: 12,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: '#262c3d',
  },
  searchInput: {
    flex: 1,
    color: '#ffffff',
    fontSize: 13,
    paddingVertical: 8,
  },
  searchClearIcon: {
    color: '#94a3b8',
    fontSize: 12,
    padding: 4,
  },
  scrollContent: {
    padding: 16,
    paddingBottom: 40,
  },
  emptyContainer: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 60,
    paddingHorizontal: 24,
  },
  emptyIcon: {
    fontSize: 48,
    marginBottom: 12,
  },
  emptyTitle: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: '700',
    marginBottom: 6,
    textAlign: 'center',
  },
  emptySub: {
    color: '#64748b',
    fontSize: 13,
    textAlign: 'center',
    lineHeight: 18,
  },
  orderCard: {
    backgroundColor: '#161922',
    borderRadius: 14,
    padding: 14,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#262c3d',
  },
  cardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  cardHeaderLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  dateText: {
    color: '#94a3b8',
    fontSize: 11,
    fontWeight: '600',
  },
  statusBadge: {
    backgroundColor: '#064e3b',
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4,
  },
  statusBadgeText: {
    color: '#34d399',
    fontSize: 9,
    fontWeight: '800',
  },
  cardHeaderRight: {
    flexDirection: 'row',
    gap: 6,
  },
  iconButton: {
    width: 30,
    height: 30,
    borderRadius: 15,
    backgroundColor: '#1e2538',
    justifyContent: 'center',
    alignItems: 'center',
  },
  favoriteActive: {
    backgroundColor: '#3b2f15',
  },
  iconButtonText: {
    fontSize: 13,
  },
  promptRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    marginBottom: 10,
    backgroundColor: '#0d0f17',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6,
  },
  promptLabel: {
    color: '#64748b',
    fontSize: 9,
    fontWeight: '800',
  },
  promptText: {
    color: '#cbd5e1',
    fontSize: 11,
    fontStyle: 'italic',
    flex: 1,
  },
  detailsRow: {
    flexDirection: 'row',
    gap: 12,
    alignItems: 'center',
    marginBottom: 12,
  },
  itemImage: {
    width: 60,
    height: 60,
    borderRadius: 8,
  },
  imagePlaceholder: {
    width: 60,
    height: 60,
    borderRadius: 8,
    backgroundColor: '#1e2538',
    justifyContent: 'center',
    alignItems: 'center',
  },
  itemInfo: {
    flex: 1,
  },
  itemTitleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  vegIcon: {
    fontSize: 10,
  },
  itemName: {
    color: '#ffffff',
    fontSize: 14,
    fontWeight: '700',
    flex: 1,
  },
  restaurantName: {
    color: '#94a3b8',
    fontSize: 12,
    marginTop: 2,
  },
  itemPrice: {
    color: '#fc8019',
    fontSize: 13,
    fontWeight: '800',
    marginTop: 4,
  },
  actionsRow: {
    flexDirection: 'row',
    gap: 8,
    marginTop: 4,
  },
  instantDispatchBtn: {
    flex: 2,
    backgroundColor: '#fc8019',
    paddingVertical: 9,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
  },
  instantDispatchText: {
    color: '#ffffff',
    fontSize: 12,
    fontWeight: '800',
  },
  rerunPipelineBtn: {
    flex: 1,
    backgroundColor: '#1e2538',
    paddingVertical: 9,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: '#3b82f6',
  },
  rerunPipelineText: {
    color: '#93c5fd',
    fontSize: 12,
    fontWeight: '700',
  },
});
