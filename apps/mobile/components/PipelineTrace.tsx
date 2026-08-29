import React from 'react';
import { StyleSheet, Text, View, ActivityIndicator } from 'react-native';
import { PipelineEvent, PipelineStage } from '../services/api';

interface PipelineTraceProps {
  events: PipelineEvent[];
  currentStage: PipelineStage | null;
  isLoading: boolean;
}

interface StageDefinition {
  key: PipelineStage;
  title: string;
  subtitle: string;
  icon: string;
}

const STAGES: StageDefinition[] = [
  {
    key: 'PARSING_INTENT',
    title: 'Stage 1: Intent Extraction',
    subtitle: 'Extracting item, budget & preferences',
    icon: '🎯',
  },
  {
    key: 'SEARCHING_RESTAURANTS',
    title: 'Stage 2: Restaurant & Catalog Search',
    subtitle: 'Scanning top-rated Swiggy outlets',
    icon: '🏪',
  },
  {
    key: 'FILTERING_MENU',
    title: 'Stage 3: Menu & Budget Filter',
    subtitle: 'Filtering items within price limit',
    icon: '⚡',
  },
  {
    key: 'AWAITING_APPROVAL',
    title: 'Stage 4: Approval Card Staged',
    subtitle: 'Recommendation prepared for review',
    icon: '✨',
  },
];

export const PipelineTrace: React.FC<PipelineTraceProps> = ({
  events,
  currentStage,
  isLoading,
}) => {
  const getStageStatus = (stageKey: PipelineStage): 'completed' | 'active' | 'pending' | 'failed' => {
    const stageEvents = events.filter((e) => e.stage === stageKey);
    const hasFailed = events.some((e) => e.stage === 'FAILED' || e.status === 'failed');

    if (hasFailed && currentStage === stageKey) return 'failed';

    const isCompleted = stageEvents.some((e) => e.status === 'completed');
    if (isCompleted) return 'completed';

    if (currentStage === stageKey && isLoading) return 'active';

    const stageOrder: PipelineStage[] = [
      'PARSING_INTENT',
      'SEARCHING_RESTAURANTS',
      'FILTERING_MENU',
      'AWAITING_APPROVAL',
      'COMPLETED',
    ];
    const currentIndex = stageOrder.indexOf(currentStage || 'PARSING_INTENT');
    const stageIndex = stageOrder.indexOf(stageKey);

    if (stageIndex < currentIndex) return 'completed';
    return 'pending';
  };

  const getStageMessage = (stageKey: PipelineStage): string | null => {
    const stageEvents = events.filter((e) => e.stage === stageKey);
    if (stageEvents.length === 0) return null;
    return stageEvents[stageEvents.length - 1].message;
  };

  return (
    <View style={styles.container}>
      <View style={styles.headerRow}>
        <View style={styles.liveIndicator}>
          <View style={[styles.dot, isLoading && styles.dotPulsing]} />
          <Text style={styles.headerTitle}>
            {isLoading ? 'LIVE PIPELINE EXECUTION' : 'PIPELINE TRACE'}
          </Text>
        </View>
        <Text style={styles.eventCount}>{events.length} events</Text>
      </View>

      <View style={styles.timeline}>
        {STAGES.map((stage, index) => {
          const status = getStageStatus(stage.key);
          const message = getStageMessage(stage.key);
          const isLast = index === STAGES.length - 1;

          return (
            <View key={stage.key} style={styles.stageRow}>
              {/* Left Column: Icon & Line */}
              <View style={styles.leftColumn}>
                <View
                  style={[
                    styles.nodeCircle,
                    status === 'completed' && styles.nodeCompleted,
                    status === 'active' && styles.nodeActive,
                    status === 'failed' && styles.nodeFailed,
                    status === 'pending' && styles.nodePending,
                  ]}
                >
                  {status === 'active' ? (
                    <ActivityIndicator size="small" color="#60a5fa" />
                  ) : status === 'completed' ? (
                    <Text style={styles.checkIcon}>✓</Text>
                  ) : status === 'failed' ? (
                    <Text style={styles.errorIcon}>✕</Text>
                  ) : (
                    <Text style={styles.pendingIndex}>{index + 1}</Text>
                  )}
                </View>
                {!isLast && (
                  <View
                    style={[
                      styles.connectorLine,
                      (status === 'completed' || status === 'active') &&
                        styles.connectorLineActive,
                    ]}
                  />
                )}
              </View>

              {/* Right Column: Stage Details */}
              <View style={styles.detailsColumn}>
                <View style={styles.stageTitleRow}>
                  <Text style={styles.stageIcon}>{stage.icon}</Text>
                  <Text
                    style={[
                      styles.stageTitle,
                      status === 'active' && styles.stageTitleActive,
                      status === 'completed' && styles.stageTitleCompleted,
                    ]}
                  >
                    {stage.title}
                  </Text>
                </View>

                <Text style={styles.stageSubtitle}>{stage.subtitle}</Text>

                {message ? (
                  <View
                    style={[
                      styles.logBox,
                      status === 'active' && styles.logBoxActive,
                      status === 'completed' && styles.logBoxCompleted,
                      status === 'failed' && styles.logBoxFailed,
                    ]}
                  >
                    <Text style={styles.logText}>{message}</Text>
                  </View>
                ) : null}
              </View>
            </View>
          );
        })}
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    backgroundColor: '#161922',
    borderRadius: 16,
    padding: 18,
    marginVertical: 12,
    borderWidth: 1,
    borderColor: '#262c3d',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 4,
  },
  headerRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#222838',
    paddingBottom: 10,
  },
  liveIndicator: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  dot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: '#10b981',
    marginRight: 8,
  },
  dotPulsing: {
    backgroundColor: '#3b82f6',
  },
  headerTitle: {
    color: '#94a3b8',
    fontSize: 12,
    fontWeight: '700',
    letterSpacing: 1.1,
  },
  eventCount: {
    color: '#64748b',
    fontSize: 11,
    fontWeight: '600',
  },
  timeline: {
    paddingLeft: 4,
  },
  stageRow: {
    flexDirection: 'row',
    minHeight: 64,
  },
  leftColumn: {
    alignItems: 'center',
    width: 32,
  },
  nodeCircle: {
    width: 28,
    height: 28,
    borderRadius: 14,
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 2,
    borderColor: '#334155',
    backgroundColor: '#1e293b',
    zIndex: 2,
  },
  nodeActive: {
    borderColor: '#3b82f6',
    backgroundColor: '#1e3a8a',
  },
  nodeCompleted: {
    borderColor: '#10b981',
    backgroundColor: '#064e3b',
  },
  nodeFailed: {
    borderColor: '#ef4444',
    backgroundColor: '#7f1d1d',
  },
  nodePending: {
    borderColor: '#334155',
    backgroundColor: '#0f172a',
  },
  checkIcon: {
    color: '#34d399',
    fontSize: 14,
    fontWeight: '900',
  },
  errorIcon: {
    color: '#f87171',
    fontSize: 13,
    fontWeight: '900',
  },
  pendingIndex: {
    color: '#64748b',
    fontSize: 12,
    fontWeight: '600',
  },
  connectorLine: {
    width: 2,
    flex: 1,
    backgroundColor: '#262c3d',
    marginVertical: 4,
  },
  connectorLineActive: {
    backgroundColor: '#10b981',
  },
  detailsColumn: {
    flex: 1,
    paddingLeft: 14,
    paddingBottom: 16,
  },
  stageTitleRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  stageIcon: {
    fontSize: 14,
    marginRight: 6,
  },
  stageTitle: {
    fontSize: 14,
    fontWeight: '700',
    color: '#cbd5e1',
  },
  stageTitleActive: {
    color: '#60a5fa',
  },
  stageTitleCompleted: {
    color: '#f8fafc',
  },
  stageSubtitle: {
    fontSize: 12,
    color: '#64748b',
    marginTop: 2,
  },
  logBox: {
    marginTop: 6,
    backgroundColor: '#0f172a',
    borderRadius: 8,
    padding: 8,
    borderLeftWidth: 3,
    borderLeftColor: '#3b82f6',
  },
  logBoxActive: {
    borderLeftColor: '#60a5fa',
    backgroundColor: '#172554',
  },
  logBoxCompleted: {
    borderLeftColor: '#10b981',
    backgroundColor: '#064e3b33',
  },
  logBoxFailed: {
    borderLeftColor: '#ef4444',
    backgroundColor: '#7f1d1d33',
  },
  logText: {
    color: '#93c5fd',
    fontSize: 12,
    lineHeight: 16,
  },
});
