const globalBootLog: string[] = [];

export function logBoot(msg: string) {
  const line = `${new Date().toISOString().slice(11, 19)} ${msg}`;
  if (Array.isArray(globalBootLog)) {
    globalBootLog.push(line);
  }
  console.log('[BOOT]', line);
}

export function getBootLog(): string[] {
  return globalBootLog;
}

logBoot('bootLogger:module evaluated');
