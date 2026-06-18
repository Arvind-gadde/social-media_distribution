/**
 * Goal Rings Component
 * 
 * iOS-style activity rings for goal progress visualization
 */

'use client';

import { useMemo } from 'react';

interface GoalRingsProps {
  progress: number; // 0-100
  size?: number;
  strokeWidth?: number;
  color?: string;
}

export function GoalRings({
  progress,
  size = 120,
  strokeWidth = 12,
  color = '#06b6d4',
}: GoalRingsProps) {
  const radius = (size - strokeWidth) / 2;
  const circumference = radius * 2 * Math.PI;
  const offset = circumference - (progress / 100) * circumference;

  return (
    <div className="relative" style={{ width: size, height: size }}>
      {/* Background ring */}
      <svg
        className="transform -rotate-90"
        width={size}
        height={size}
      >
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke="rgba(255, 255, 255, 0.1)"
          strokeWidth={strokeWidth}
          fill="none"
        />
        {/* Progress ring */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke={color}
          strokeWidth={strokeWidth}
          fill="none"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          className="transition-all duration-500 ease-out"
          style={{
            filter: 'drop-shadow(0 0 8px rgba(6, 182, 212, 0.5))',
          }}
        />
      </svg>
      
      {/* Center text */}
      <div className="absolute inset-0 flex items-center justify-center">
        <div className="text-center">
          <div className="text-2xl font-bold">{Math.round(progress)}%</div>
        </div>
      </div>
    </div>
  );
}

interface MultiGoalRingsProps {
  goals: Array<{
    progress: number;
    color: string;
    label: string;
  }>;
  size?: number;
}

export function MultiGoalRings({ goals, size = 160 }: MultiGoalRingsProps) {
  const strokeWidth = 10;
  const gap = 6;

  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="transform -rotate-90">
        {goals.map((goal, index) => {
          const radius = (size - strokeWidth) / 2 - (index * (strokeWidth + gap));
          const circumference = radius * 2 * Math.PI;
          const offset = circumference - (goal.progress / 100) * circumference;

          return (
            <g key={index}>
              {/* Background */}
              <circle
                cx={size / 2}
                cy={size / 2}
                r={radius}
                stroke="rgba(255, 255, 255, 0.1)"
                strokeWidth={strokeWidth}
                fill="none"
              />
              {/* Progress */}
              <circle
                cx={size / 2}
                cy={size / 2}
                r={radius}
                stroke={goal.color}
                strokeWidth={strokeWidth}
                fill="none"
                strokeDasharray={circumference}
                strokeDashoffset={offset}
                strokeLinecap="round"
                className="transition-all duration-500 ease-out"
              />
            </g>
          );
        })}
      </svg>
      
      {/* Legend */}
      <div className="absolute -bottom-16 left-0 right-0">
        <div className="flex justify-center gap-4 text-xs">
          {goals.map((goal, index) => (
            <div key={index} className="flex items-center gap-1">
              <div
                className="w-2 h-2 rounded-full"
                style={{ backgroundColor: goal.color }}
              />
              <span className="text-muted-foreground">{goal.label}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
