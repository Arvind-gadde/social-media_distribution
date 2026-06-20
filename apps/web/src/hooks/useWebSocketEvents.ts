/**
 * WebSocket Events Hook
 * 
 * React hook for real-time agent events via WebSocket
 */

import { useEffect, useState, useCallback } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { getWebSocketClient, type AgentEvent, type AgentEventType } from '@/lib/websocket';
import { toast } from '@/lib/toast';

export type ConnectionStatus = 'connected' | 'disconnected' | 'connecting' | 'error';

interface UseWebSocketEventsOptions {
  /**
   * Auto-connect on mount
   */
  autoConnect?: boolean;
  
  /**
   * Event types to subscribe to
   */
  eventTypes?: AgentEventType[];
  
  /**
   * Show toast notifications for events
   */
  showToasts?: boolean;
  
  /**
   * Invalidate React Query cache on events
   */
  invalidateQueries?: boolean;
}

/**
 * Hook for WebSocket real-time events
 */
export function useWebSocketEvents(options: UseWebSocketEventsOptions = {}) {
  const {
    autoConnect = true,
    eventTypes = [],
    showToasts = true,
    invalidateQueries = true,
  } = options;

  const queryClient = useQueryClient();
  const wsClient = getWebSocketClient();
  
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('disconnected');
  const [lastEvent, setLastEvent] = useState<AgentEvent | null>(null);
  const [events, setEvents] = useState<AgentEvent[]>([]);

  // Stable dependency: an inline or default `eventTypes` array is a new
  // reference every render; keying on its joined value stops the subscribe
  // effect from tearing down and re-registering listeners on every render.
  const eventTypesKey = eventTypes.join(',');

  /**
   * Handle incoming agent event
   */
  const handleEvent = useCallback((event: AgentEvent) => {
    console.log('[useWebSocketEvents] Received event:', event.type, event);
    
    // Update state
    setLastEvent(event);
    setEvents(prev => [event, ...prev].slice(0, 50)); // Keep last 50 events

    // Show toast notification
    if (showToasts) {
      const eventMessages: Partial<Record<AgentEventType, (data: any) => string>> = {
        agent_started: (data) => `🤖 ${data.agent_type} agent started`,
        agent_completed: (data) => `✅ ${data.agent_type} agent completed`,
        agent_failed: (data) => `❌ ${data.agent_type} agent failed`,
        insight_created: (data) => `💡 New insight: ${data.title}`,
        trend_detected: (data) => `📈 Trending: ${data.title}`,
        goal_milestone: (data) => `🎯 Goal milestone: ${data.title}`,
        competitor_move: (data) => `🔍 Competitor update: ${data.title}`,
      };

      const getMessage = eventMessages[event.type];
      if (getMessage) {
        const message = getMessage(event.data);
        
        // Use appropriate toast type
        if (event.type === 'agent_failed') {
          toast.error(message);
        } else if (event.type === 'insight_created' || event.type === 'trend_detected') {
          toast.success(message);
        } else {
          toast.info(message);
        }
      }
    }

    // Invalidate React Query cache
    if (invalidateQueries) {
      const queryKeysToInvalidate: Partial<Record<AgentEventType, string[]>> = {
        agent_started: ['agents'],
        agent_completed: ['agents', 'insights'],
        agent_failed: ['agents'],
        insight_created: ['insights'],
        trend_detected: ['trends'],
        goal_milestone: ['goals'],
        competitor_move: ['competitors'],
      };

      const keys = queryKeysToInvalidate[event.type] || [];
      keys.forEach(key => {
        queryClient.invalidateQueries({ queryKey: [key] });
      });
    }
  }, [showToasts, invalidateQueries, queryClient]);

  /**
   * Connect to WebSocket
   */
  const connect = useCallback(() => {
    if (wsClient.isConnected()) {
      console.log('[useWebSocketEvents] Already connected');
      return;
    }

    console.log('[useWebSocketEvents] Connecting...');
    setConnectionStatus('connecting');

    // Get token from localStorage
    const token = typeof window !== 'undefined' 
      ? localStorage.getItem('access_token') 
      : null;

    wsClient.connect(token || undefined);
  }, [wsClient]);

  /**
   * Disconnect from WebSocket
   */
  const disconnect = useCallback(() => {
    console.log('[useWebSocketEvents] Disconnecting...');
    wsClient.disconnect();
    setConnectionStatus('disconnected');
  }, [wsClient]);

  /**
   * Subscribe to specific event type
   */
  const subscribe = useCallback((eventType: AgentEventType, handler: (event: AgentEvent) => void) => {
    // Caller owns the returned unsubscribe (see useLiveInsights etc.); do NOT
    // also track it in a shared ref that other effects would wholesale-clear.
    return wsClient.on(eventType, handler);
  }, [wsClient]);

  /**
   * Emit event to server
   */
  const emit = useCallback((event: string, data: any) => {
    wsClient.emit(event, data);
  }, [wsClient]);

  /**
   * Clear events history
   */
  const clearEvents = useCallback(() => {
    setEvents([]);
    setLastEvent(null);
  }, []);

  // Setup connection status listener
  useEffect(() => {
    const unsubscribe = wsClient.onConnectionStatus((status) => {
      console.log('[useWebSocketEvents] Connection status:', status);
      setConnectionStatus(status);
    });

    return () => {
      unsubscribe();
    };
  }, [wsClient]);

  // Auto-connect on mount
  useEffect(() => {
    if (autoConnect) {
      connect();
    }
  }, [autoConnect, connect]);

  // Subscribe to event types
  useEffect(() => {
    const localUnsubs: (() => void)[] = [];
    if (eventTypes.length === 0) {
      // Subscribe to all events
      localUnsubs.push(wsClient.on('*', handleEvent));
    } else {
      // Subscribe to specific event types
      eventTypes.forEach((eventType) => {
        localUnsubs.push(wsClient.on(eventType, handleEvent));
      });
    }

    return () => {
      // Tear down ONLY this effect's own listeners — not a shared array that
      // other effects and the public subscribe() also write to.
      localUnsubs.forEach((unsub) => unsub());
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [eventTypesKey, handleEvent, wsClient]);

  return {
    // Connection
    connectionStatus,
    isConnected: connectionStatus === 'connected',
    isConnecting: connectionStatus === 'connecting',
    connect,
    disconnect,
    
    // Events
    lastEvent,
    events,
    clearEvents,
    
    // Subscriptions
    subscribe,
    emit,
  };
}

/**
 * Hook for specific agent type events
 */
export function useAgentEvents(agentType: string) {
  const [agentEvents, setAgentEvents] = useState<AgentEvent[]>([]);
  
  const { subscribe, ...rest } = useWebSocketEvents({
    autoConnect: true,
    showToasts: false, // Don't show toasts for specific agent events
    invalidateQueries: true,
  });

  useEffect(() => {
    const unsubscribers: (() => void)[] = [];

    // Subscribe to all agent events and filter by agent type
    const unsubscribe = subscribe('*' as AgentEventType, (event) => {
      if (event.agent_type === agentType) {
        setAgentEvents(prev => [event, ...prev].slice(0, 20));
      }
    });
    
    unsubscribers.push(unsubscribe);

    return () => {
      unsubscribers.forEach(unsub => unsub());
    };
  }, [agentType, subscribe]);

  return {
    ...rest,
    agentEvents,
  };
}

/**
 * Hook for live insights
 */
export function useLiveInsights() {
  const [liveInsights, setLiveInsights] = useState<AgentEvent[]>([]);
  
  const { subscribe, ...rest } = useWebSocketEvents({
    autoConnect: true,
    eventTypes: ['insight_created'],
    showToasts: true,
    invalidateQueries: true,
  });

  useEffect(() => {
    const unsubscribe = subscribe('insight_created', (event) => {
      setLiveInsights(prev => [event, ...prev].slice(0, 10));
    });

    return () => {
      unsubscribe();
    };
  }, [subscribe]);

  return {
    ...rest,
    liveInsights,
  };
}

/**
 * Hook for live trends
 */
export function useLiveTrends() {
  const [liveTrends, setLiveTrends] = useState<AgentEvent[]>([]);
  
  const { subscribe, ...rest } = useWebSocketEvents({
    autoConnect: true,
    eventTypes: ['trend_detected'],
    showToasts: true,
    invalidateQueries: true,
  });

  useEffect(() => {
    const unsubscribe = subscribe('trend_detected', (event) => {
      setLiveTrends(prev => [event, ...prev].slice(0, 10));
    });

    return () => {
      unsubscribe();
    };
  }, [subscribe]);

  return {
    ...rest,
    liveTrends,
  };
}

/**
 * Hook for goal milestones
 */
export function useLiveGoalMilestones() {
  const [milestones, setMilestones] = useState<AgentEvent[]>([]);
  
  const { subscribe, ...rest } = useWebSocketEvents({
    autoConnect: true,
    eventTypes: ['goal_milestone'],
    showToasts: true,
    invalidateQueries: true,
  });

  useEffect(() => {
    const unsubscribe = subscribe('goal_milestone', (event) => {
      setMilestones(prev => [event, ...prev].slice(0, 10));
    });

    return () => {
      unsubscribe();
    };
  }, [subscribe]);

  return {
    ...rest,
    milestones,
  };
}
