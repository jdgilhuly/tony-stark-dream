import React from 'react';
import { TouchableOpacity, StyleSheet, ActivityIndicator, Animated } from 'react-native';
import Icon from 'react-native-vector-icons/Ionicons';

interface VoiceButtonProps {
  isListening: boolean;
  isProcessing: boolean;
  onPress: () => void;
  size?: number;
}

export function VoiceButton({
  isListening,
  isProcessing,
  onPress,
  size = 44,
}: VoiceButtonProps) {
  const pulseAnim = React.useRef(new Animated.Value(1)).current;

  React.useEffect(() => {
    if (isListening) {
      Animated.loop(
        Animated.sequence([
          Animated.timing(pulseAnim, {
            toValue: 1.2,
            duration: 500,
            useNativeDriver: true,
          }),
          Animated.timing(pulseAnim, {
            toValue: 1,
            duration: 500,
            useNativeDriver: true,
          }),
        ])
      ).start();
    } else {
      pulseAnim.setValue(1);
    }
  }, [isListening, pulseAnim]);

  const getBackgroundColor = () => {
    if (isListening) return '#FF6B6B';
    if (isProcessing) return '#FFB74D';
    return '#2A2A3E';
  };

  const renderContent = () => {
    if (isProcessing) {
      return <ActivityIndicator size="small" color="#FFF" />;
    }
    return (
      <Icon
        name={isListening ? 'stop' : 'mic'}
        size={size * 0.5}
        color={isListening ? '#FFF' : '#00D9FF'}
      />
    );
  };

  return (
    <Animated.View style={{ transform: [{ scale: pulseAnim }] }}>
      <TouchableOpacity
        style={[
          styles.button,
          {
            width: size,
            height: size,
            borderRadius: size / 2,
            backgroundColor: getBackgroundColor(),
          },
        ]}
        onPress={onPress}
        disabled={isProcessing}
        activeOpacity={0.7}
      >
        {renderContent()}
      </TouchableOpacity>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  button: {
    justifyContent: 'center',
    alignItems: 'center',
  },
});
