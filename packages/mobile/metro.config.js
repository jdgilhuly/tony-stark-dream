const { getDefaultConfig, mergeConfig } = require('@react-native/metro-config');
const path = require('path');

// Get the root of the monorepo
const projectRoot = __dirname;
const monorepoRoot = path.resolve(projectRoot, '../..');

const defaultConfig = getDefaultConfig(projectRoot);

/**
 * Metro configuration for JARVIS Mobile
 * https://facebook.github.io/metro/docs/configuration
 */
const config = {
  watchFolders: [
    // Include the monorepo root for shared packages
    monorepoRoot,
    // Include the core package
    path.resolve(monorepoRoot, 'packages/core'),
  ],

  resolver: {
    // Allow importing from outside the mobile package
    nodeModulesPaths: [
      path.resolve(projectRoot, 'node_modules'),
      path.resolve(monorepoRoot, 'node_modules'),
    ],

    // Ensure we resolve to the correct versions
    extraNodeModules: {
      '@jarvis/core': path.resolve(monorepoRoot, 'packages/core'),
    },

    // Block duplicate react/react-native from monorepo
    blockList: [
      // Prevent loading react from the root
      new RegExp(`${monorepoRoot}/node_modules/react/.*`),
      new RegExp(`${monorepoRoot}/node_modules/react-native/.*`),
    ],

    // Source extensions
    sourceExts: [...defaultConfig.resolver.sourceExts, 'cjs'],
  },

  transformer: {
    getTransformOptions: async () => ({
      transform: {
        experimentalImportSupport: false,
        inlineRequires: true,
      },
    }),
  },
};

module.exports = mergeConfig(defaultConfig, config);
