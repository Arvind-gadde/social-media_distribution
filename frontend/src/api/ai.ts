import api from "./client";

export interface CaptionRequest {
  topic: string; tone: string; language: string;
  media_type: string; platforms: string[];
}

export const generateCaption = (data: CaptionRequest) =>
  api.post<{ caption: string }>("/ai/generate-caption", data);

export const suggestHashtags = (platform: string, caption: string, language = "en") =>
  api.post<{ hashtags: string[] }>("/ai/suggest-hashtags", null, {
    params: { platform, caption, language },
  });