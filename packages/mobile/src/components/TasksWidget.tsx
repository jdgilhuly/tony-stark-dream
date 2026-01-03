import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import Icon from 'react-native-vector-icons/Ionicons';

interface Task {
  id: string;
  title: string;
  completed: boolean;
  priority: string;
}

interface TasksWidgetProps {
  tasks?: Task[];
  onTaskPress?: (task: Task) => void;
}

const getPriorityColor = (priority: string): string => {
  switch (priority.toLowerCase()) {
    case 'urgent':
      return '#FF6B6B';
    case 'high':
      return '#FFB74D';
    case 'medium':
      return '#00D9FF';
    case 'low':
      return '#4CAF50';
    default:
      return '#888';
  }
};

export function TasksWidget({ tasks, onTaskPress }: TasksWidgetProps) {
  const pendingTasks = tasks?.filter((t) => !t.completed).slice(0, 4) || [];

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Icon name="checkbox" size={20} color="#00D9FF" />
        <Text style={styles.title}>Tasks</Text>
        {tasks && (
          <View style={styles.badge}>
            <Text style={styles.badgeText}>{pendingTasks.length}</Text>
          </View>
        )}
      </View>

      <View style={styles.content}>
        {pendingTasks.length > 0 ? (
          pendingTasks.map((task, index) => (
            <TouchableOpacity
              key={task.id || index}
              style={styles.taskItem}
              onPress={() => onTaskPress?.(task)}
              activeOpacity={0.7}
            >
              <View
                style={[
                  styles.priorityIndicator,
                  { backgroundColor: getPriorityColor(task.priority) },
                ]}
              />
              <Icon
                name={task.completed ? 'checkbox' : 'square-outline'}
                size={20}
                color={task.completed ? '#4CAF50' : '#888'}
              />
              <Text
                style={[styles.taskTitle, task.completed && styles.taskCompleted]}
                numberOfLines={1}
              >
                {task.title}
              </Text>
            </TouchableOpacity>
          ))
        ) : (
          <View style={styles.emptyState}>
            <Icon name="checkmark-circle" size={32} color="#4CAF50" />
            <Text style={styles.emptyText}>All caught up, sir!</Text>
          </View>
        )}
      </View>

      {tasks && tasks.filter((t) => !t.completed).length > 4 && (
        <TouchableOpacity style={styles.viewAll}>
          <Text style={styles.viewAllText}>View all tasks</Text>
          <Icon name="chevron-forward" size={16} color="#00D9FF" />
        </TouchableOpacity>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: '#1A1A2E',
    borderRadius: 12,
    padding: 16,
    borderWidth: 1,
    borderColor: '#2A2A3E',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
  },
  title: {
    color: '#FFF',
    fontSize: 14,
    fontWeight: 'bold',
    marginLeft: 8,
    flex: 1,
  },
  badge: {
    backgroundColor: '#00D9FF',
    borderRadius: 10,
    paddingHorizontal: 8,
    paddingVertical: 2,
  },
  badgeText: {
    color: '#000',
    fontSize: 12,
    fontWeight: 'bold',
  },
  content: {
    gap: 4,
  },
  taskItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: '#2A2A3E',
  },
  priorityIndicator: {
    width: 3,
    height: '100%',
    borderRadius: 2,
    marginRight: 10,
  },
  taskTitle: {
    color: '#FFF',
    fontSize: 14,
    marginLeft: 8,
    flex: 1,
  },
  taskCompleted: {
    textDecorationLine: 'line-through',
    color: '#666',
  },
  emptyState: {
    alignItems: 'center',
    paddingVertical: 20,
  },
  emptyText: {
    color: '#4CAF50',
    marginTop: 8,
  },
  viewAll: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 12,
  },
  viewAllText: {
    color: '#00D9FF',
    fontSize: 12,
  },
});
