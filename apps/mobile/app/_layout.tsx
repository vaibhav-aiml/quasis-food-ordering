import { StatusBar } from 'expo-status-bar';
import React, { useEffect, useState } from 'react';
import { SafeAreaView, StyleSheet, Text, View } from 'react-native';
import { getBootLog, logBoot } from '../services/bootLogger';
import MainScreen from './index';

logBoot('module:_layout evaluated');

export default function RootLayout() {
  const [logs, setLogs] = useState<string[]>([]);
  logBoot('RootLayout:render start');

  useEffect(() => {
    logBoot('RootLayout:mounted');
    setLogs([...getBootLog()]);
    const interval = setInterval(() => {
      setLogs([...getBootLog()]);
    }, 500);
    return () => clearInterval(interval);
  }, []);

  const displayLogs = logs.length > 0 ? logs : getBootLog();

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar style="light" backgroundColor="#0b0d13" />
      {/* Always-visible boot trail, positioned to never be hidden by a modal */}
      <View style={{ position: 'absolute', top: 40, left: 8, right: 8, zIndex: 9999, pointerEvents: 'none' }}>
        {displayLogs.slice(-6).map((l, i) => (
          <Text key={i} style={{ color: '#00ff00', fontSize: 9, backgroundColor: '#000000cc' }}>
            {l}
          </Text>
        ))}
      </View>
      <MainScreen />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0b0d13',
  },
});
