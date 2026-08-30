import { StatusBar } from 'expo-status-bar';
import React, { useState } from 'react';
import { SafeAreaView, StyleSheet, Text, View } from 'react-native';
import MainScreen from './index';

const bootLog: string[] = [];
export function logBoot(msg: string) {
  const line = `${new Date().toISOString().slice(11, 19)} ${msg}`;
  bootLog.push(line);
  console.log('[BOOT]', line);
}
logBoot('module:_layout evaluated');

export default function RootLayout() {
  const [, forceRender] = useState(0);
  logBoot('RootLayout:render start');
  React.useEffect(() => {
    logBoot('RootLayout:mounted');
  }, []);
  return (
    <SafeAreaView style={styles.container}>
      <StatusBar style="light" backgroundColor="#0b0d13" />
      {/* Always-visible boot trail, positioned to never be hidden by a modal */}
      <View style={{ position: 'absolute', top: 40, left: 8, right: 8, zIndex: 9999, pointerEvents: 'none' }}>
        {bootLog.slice(-6).map((l, i) => (
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
