export interface User {
  id: string;
  email: string;
  name: string;
  avatar_url: string | null;
  connected_platforms: string[];
  is_active: boolean;
  created_at: string;
}

export interface PlatformContent {
  caption: string;
  hashtags: string[];
  full_text: string;
}

export interface Post {
  id: string;
  title: string | null;
  caption: string | null;
  media_url: string | null;
  media_type: string | null;
  target_platforms: string[];
  platform_status: Record<string, string>;
  platform_content: Record<string, PlatformContent>;
  recommended_platforms: string[];
  status: "draft" | "scheduled" | "processing" | "published" | "partial" | "failed";
  scheduled_at: string | null;
  published_at: string | null;
  created_at: string;
}

export interface PlatformMeta {
  id: string;
  name: string;
  icon: string;
  color: string;
  supportsVideo: boolean;
  supportsImage: boolean;
  supportsText: boolean;
}

export interface Recommendation {
  platform: string;
  reason: string;
  score: number;
}

export interface AnalyticsSummary {
  total_posts: number;
  published_posts: number;
  partial_posts: number;
  failed_posts: number;
  platform_distribution: Record<string, number>;
  platform_success_rate: Record<string, number>;
}

export const PLATFORMS: PlatformMeta[] = [
  { id: "instagram",      name: "Instagram",       icon: "📸", color: "#E1306C", supportsVideo: true,  supportsImage: true,  supportsText: false },
  { id: "youtube",        name: "YouTube",          icon: "▶️",  color: "#FF0000", supportsVideo: true,  supportsImage: false, supportsText: false },
  { id: "youtube_shorts", name: "YT Shorts",        icon: "🩳", color: "#FF0000", supportsVideo: true,  supportsImage: false, supportsText: false },
  { id: "facebook",       name: "Facebook",         icon: "👥", color: "#1877F2", supportsVideo: true,  supportsImage: true,  supportsText: true  },
  { id: "linkedin",       name: "LinkedIn",         icon: "💼", color: "#0A66C2", supportsVideo: true,  supportsImage: true,  supportsText: true  },
  { id: "x",              name: "X / Twitter",      icon: "✖️", color: "#000000", supportsVideo: false, supportsImage: true,  supportsText: true  },
  { id: "josh",           name: "Josh",             icon: "🎬", color: "#FF6B00", supportsVideo: true,  supportsImage: false, supportsText: false },
  { id: "moj",            name: "Moj",              icon: "🎵", color: "#7C3AED", supportsVideo: true,  supportsImage: false, supportsText: false },
  { id: "sharechat",      name: "ShareChat",        icon: "💬", color: "#F59E0B", supportsVideo: true,  supportsImage: true,  supportsText: true  },
  { id: "koo",            name: "Koo",              icon: "🐦", color: "#F6C90E", supportsVideo: false, supportsImage: true,  supportsText: true  },
  { id: "chingari",       name: "Chingari",         icon: "🔥", color: "#EF4444", supportsVideo: true,  supportsImage: false, supportsText: false },
  { id: "roposo",         name: "Roposo",           icon: "🎥", color: "#10B981", supportsVideo: true,  supportsImage: false, supportsText: false },
];