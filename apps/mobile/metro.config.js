// Monorepo-aware Metro config for pnpm workspace.
// Keeps Expo's resolver defaults intact (do NOT disable hierarchical lookup —
// expo-doctor flags it, and disabling causes duplicate-react resolution bugs
// that surface as `getDevServer is not a function` on device).
const { getDefaultConfig } = require('expo/metro-config');
const path = require('path');

const projectRoot = __dirname;
const workspaceRoot = path.resolve(projectRoot, '../..');

const config = getDefaultConfig(projectRoot);

config.watchFolders = [...(config.watchFolders ?? []), workspaceRoot];

module.exports = config;
